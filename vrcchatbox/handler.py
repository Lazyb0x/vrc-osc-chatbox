import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Any, AsyncGenerator, Callable, List, Type

from vrcchatbox.agent import TranslateAgent
from vrcchatbox.config import Config

logger = logging.getLogger(__name__)


@dataclass
class MsgContext:
    text: str
    is_end: bool = False  # 当 yield 此 context 时表示 handler 结束输出
    param: dict = None  # 可选的额外参数


# Handler 返回类型：异步生成器，用于流式处理
HandlerResult = AsyncGenerator[MsgContext, None]


class MsgHandler:
    order: int = 100  # 处理顺序，数值越小越先执行

    async def handle(self, ctx: MsgContext) -> HandlerResult:
        yield ctx


# 全局 handler 注册表
HANDLER_REGISTRY: dict[str, Any] = {}


def msg_register(name: str) -> Callable[[Type[MsgHandler]], Type[MsgHandler]]:
    def decorator(cls: Type[MsgHandler]) -> Type[MsgHandler]:
        HANDLER_REGISTRY[name] = cls
        return cls

    return decorator


@msg_register("example")
class ExampleHandler(MsgHandler):
    order: int = 30

    async def handle(self, ctx: MsgContext) -> HandlerResult:
        ctx.text = ctx.text.upper()
        buffer = ""
        for ch in ctx.text:
            # 延迟输出
            await asyncio.sleep(0.1)  # 模拟延迟
            buffer += ch
            yield replace(ctx, text=buffer)
        yield replace(ctx, text=buffer, is_end=True)


@msg_register("translate")
class TranslateHandler(MsgHandler):
    """翻译处理器：调用大模型翻译接口"""

    order: int = 20

    def __init__(self, config: Config, debounce_seconds: float = 1.1):
        if config.translate.enable and not config.translate.languages:
            raise ValueError("No translation languages configured.")
        self.translate_config = config.translate
        self.agent = TranslateAgent(config)
        self._debounce_seconds = debounce_seconds
        self._debouncing_task: asyncio.Task | None = None

    async def handle(self, ctx: MsgContext) -> HandlerResult:
        yield replace(ctx, text=ctx.text)
        if not self.translate_config.enable:
            return
        if not ctx.text.strip():
            return
        debounced_seconds = None
        if ctx.param:
            debounced_seconds = ctx.param.get("debounced_seconds")

        # 流式输入防抖
        if self._debouncing_task and not self._debouncing_task.done():
            self._debouncing_task.cancel()
        self._debouncing_task = asyncio.create_task(
            self._debounced_timer(debounced_seconds)
        )

        try:
            await self._debouncing_task
            yield replace(ctx, text=f"{ctx.text}\n...")
            translated_text = await self.agent.translate(ctx.text)
            yield replace(ctx, text=f"{ctx.text}\n{translated_text}", is_end=True)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.exception(f"Error translating text: {ctx.text}")
            yield replace(
                ctx,
                text=f"{ctx.text}\n[翻译接口错误，请检查模型信息是否配置正确: {str(e)}]",
                is_end=True,
            )
            return
        pass

    async def _debounced_timer(self, debounce_seconds: float = None) -> None:
        if debounce_seconds is None:
            debounce_seconds = self._debounce_seconds
        await asyncio.sleep(debounce_seconds)


class Pipeline:
    """消息处理管道，按 order 顺序执行多个 handler。"""

    def __init__(self, handlers: List[MsgHandler]) -> None:
        self.handlers: List[MsgHandler] = sorted(handlers, key=lambda h: h.order)

    async def process(self, ctx: MsgContext) -> HandlerResult:
        async for result in self._run_handlers(ctx, 0):
            yield result

    async def _run_handlers(self, ctx: MsgContext, index: int) -> HandlerResult:
        if index >= len(self.handlers):
            yield ctx
            return

        handler = self.handlers[index]
        async for new_ctx in handler.handle(ctx):
            async for final_ctx in self._run_handlers(new_ctx, index + 1):
                yield final_ctx


def build_pipeline(config: Config) -> Pipeline:
    """根据配置构建 handler 管道。"""
    handlers: List[MsgHandler] = []

    handler_cls = HANDLER_REGISTRY.get("translate")
    if handler_cls:
        handlers.append(handler_cls(config))

    return Pipeline(handlers)

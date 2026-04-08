from dataclasses import dataclass
import logging

from vrcchatbox.config import Config
from vrcchatbox.handler import MsgContext, build_pipeline

logger = logging.getLogger(__name__)


@dataclass
class Message:
    data: str
    translation: bool | None = None
    realtime: bool | None = None
    clipboard: str | None = None

    @staticmethod
    def from_dict(data: dict) -> "Message":
        return Message(
            data=data.get("data", ""),
            translation=data.get("translation"),
            realtime=data.get("realtime"),
            clipboard=data.get("clipboard"),
        )


class MessageProcessor:
    """消息加工与处理"""

    def __init__(self, config: Config):
        self.config = config
        self.pipeline = build_pipeline(config)

    async def process(self, message: Message):
        param: dict = {}
        # 翻译开关切换
        if (
            message.translation is not None
            and self.config.translate.enable != message.translation
        ):
            logger.info(f"Translation changed to {message.translation}")
            self.config.translate.enable = message.translation
        # 非实时输入关闭防抖
        if message.realtime is not None and message.realtime is False:
            param["debounced_seconds"] = 0
        # 复制到系统剪贴板
        # TODO

        ctx = MsgContext(text=message.data, param=param)
        async for result in self.pipeline.process(ctx):
            yield result.text
        return

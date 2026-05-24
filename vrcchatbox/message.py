import logging
from dataclasses import dataclass

import pyperclip

from vrcchatbox.config import Config
from vrcchatbox.handler import MsgContext, build_pipeline
from vrcchatbox.osc_client import OSCClient

logger = logging.getLogger(__name__)


@dataclass
class Message:
    data: str | None = None
    translation: bool | None = None
    realtime: bool | None = None
    clipboard: str | None = None
    languages: list[str] | None = None
    typing: bool | None = None

    @staticmethod
    def from_dict(data: dict) -> "Message":
        return Message(
            data=data.get("data"),
            translation=data.get("translation"),
            realtime=data.get("realtime"),
            clipboard=data.get("clipboard"),
            languages=data.get("languages"),
            typing=data.get("typing"),
        )


class MessageProcessor:
    """消息加工与处理"""

    def __init__(self, config: Config, osc_client: OSCClient):
        self.config = config
        self.pipeline = build_pipeline(config)
        self.osc_client = osc_client

    async def process(self, message: Message):
        param: dict = {}
        # 翻译开关切换
        if message.translation is not None and self.config.translate.enable != message.translation:
            logger.info(f"Translation changed to {message.translation}")
            self.config.translate.enable = message.translation
        # 翻译语言切换
        if message.languages is not None:
            logger.info(f"Translation languages changed to {message.languages}")
            self.config.translate.languages = message.languages

        # 非实时输入关闭防抖
        if message.realtime is not None and message.realtime is False:
            param["debounced_seconds"] = 0
        # 复制到系统剪贴板
        if message.clipboard is not None:
            pyperclip.copy(message.clipboard)
            logger.info(f"Copied to clipboard: {message.clipboard}")
        # 输入中提示
        if message.typing is not None:
            self.osc_client.chatbox_typing(is_typing=message.typing)

        if message.data is None:
            return
        ctx = MsgContext(text=message.data, param=param)
        async for result in self.pipeline.process(ctx):
            self.osc_client.chatbox_input(result.text)
            yield result.text
        return

from dataclasses import dataclass

from vrcchatbox.config import Config
from vrcchatbox.handler import MsgContext, build_pipeline


@dataclass
class Message:
    data: str
    translation: bool | None = None

    @staticmethod
    def from_dict(data: dict) -> "Message":
        return Message(data=data.get("text", ""), translation=data.get("translation"))


class MessageProcessor:
    """消息加工与处理"""

    def __init__(self, config: Config):
        self.config = config
        self.pipeline = build_pipeline(config)

    async def process(self, message: Message):
        if message.translation is not None:
            self.config.translate.enable = message.translation

        ctx = MsgContext(text=message.data)
        async for result in self.pipeline.process(ctx):
            yield result.text
        return

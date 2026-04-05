from langchain_openai import ChatOpenAI
from vrcchatbox.config import Config
from vrcchatbox.handler import MsgContext, Pipeline, build_pipeline


class Message:
    """消息加工与处理"""

    def __init__(self, template: str = None, config: Config = None):
        self.template = template
        self.config = config

    async def process(self, text: str):
        pipeline: Pipeline = build_pipeline(self.config)
        ctx = MsgContext(text=text)
        async for result in pipeline.process(ctx):
            yield result.text
        return

import logging
from typing import Any, Callable

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from vrcchatbox.config import Config

logger = logging.getLogger(__name__)


class TranslateAgent:

    def __init__(self, config: Config):
        self.config = config
        self.model = ChatOpenAI(
            model=self.config.openai.model,
            base_url=self.config.openai.api_base,
            api_key=self.config.openai.api_key,
        )

    async def translate(self, input_text: str) -> str:
        if not self.config.translate.enable:
            raise ValueError("Translation is disabled in config.")
        if not self.config.translate.languages:
            raise ValueError("No translation languages configured.")

        model = ChatOpenAI(
            model=self.config.openai.model,
            base_url=self.config.openai.api_base,
            api_key=self.config.openai.api_key,
        )
        conversation = self._get_conversation(
            self.config.translate.languages, input_text
        )

        logger.debug(f"Translation agent start")
        tool_messages = []
        tools = self._create_tools(tool_messages)
        agent = create_agent(model=model, tools=tools)
        response: dict = await agent.ainvoke(conversation)

        # 如果使用了工具，返回工具的输出信息而不是AI生成结果
        if tool_messages:
            return "\n".join(tool_messages)

        try:
            messages = response.get("messages", [])
            if not isinstance(messages, list) or not messages:
                logger.error(
                    "Invalid response format: 'messages' is missing or not a list."
                )
                return "No content available."
            last_msg = messages[-1]
            logger.debug(f"Translation agent response: {last_msg}")
            return getattr(last_msg, "content", "No content available.")
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return "An error occurred while processing the response."

    @staticmethod
    def _get_conversation(languages: str, input_text: str) -> str:
        return {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a professional, authentic machine translation engine.",
                },
                {
                    "role": "user",
                    "content": "你的任务是读取用户输入,然后: "
                    "1.如果是普通对话,直接翻译成目标语言.多语言用换行隔开. "
                    "2.如果用户明确指出要修改翻译目标语言,并且当前语言和目标语言不一致,使用 change_target_language 工具. "
                    f"Current translate target language: {languages}.",
                },
                {
                    "role": "user",
                    "content": f"Translate the following input text. NO explanations. NO notes: \n\n{input_text}",
                },
            ]
        }

    def _create_tools(self, tool_messages: list[str]) -> list[Callable[..., Any]]:
        @tool
        def change_target_language(codes: list[str]):
            """在用户明确说要"切换"或“翻译”到不同语言时调用。例如 ["en", "zh", "ja"]"""
            self.config.translate.languages = codes
            logger.info(f"Translation target languages set to: {codes}")
            tool_messages.append(f"✓")
            return "翻译目标语言已更新"

        @tool
        def switch_translation(enable: bool):
            """在用户提到要打开或者关闭功能时调用。True 启用翻译，False 禁用翻译"""
            self.config.translate.enable = enable
            logger.info(f"Translation enabled set to: {enable}")
            tool_messages.append(f"[翻译功能已 {'启用' if enable else '禁用'}]")
            return f"翻译功能已 {'启用' if enable else '禁用'}"

        return [change_target_language]

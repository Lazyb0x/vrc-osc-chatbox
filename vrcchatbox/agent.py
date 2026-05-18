import json
import logging
from dataclasses import dataclass
from openai import AsyncOpenAI

from vrcchatbox.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    result: str
    end_conversation: bool = False


@dataclass
class AgentResult:
    content: str
    from_tool: bool = False


change_target_language = {
    "type": "function",
    "function": {
        "name": "change_target_language",
        "description": '在用户明确说要"切换"或"翻译"到不同语言时调用。例如 ["en", "zh", "ja"]',
        "parameters": {
            "type": "object",
            "properties": {
                "codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": '目标语言代码列表，如 ["en", "zh", "ja"]',
                }
            },
            "required": ["codes"],
        },
    },
}

switch_translation = {
    "type": "function",
    "function": {
        "name": "switch_translation",
        "description": "在用户提到要打开或者关闭功能时调用。True 启用翻译，False 禁用翻译",
        "parameters": {
            "type": "object",
            "properties": {
                "enable": {"type": "boolean", "description": "True 启用翻译，False 禁用翻译"}
            },
            "required": ["enable"],
        },
    },
}

TOOL_DEF_MAP = {
    "change_target_language": change_target_language,
    "switch_translation": switch_translation,
}
TOOL_CALL_MAP = {}


class TranslateAgent:
    def __init__(self, config: Config):
        self.config = config
        self._setup_tool_map()

    def _setup_tool_map(self):
        def change_target_language_impl(codes: list[str]) -> ToolResult:
            self.config.translate.languages = codes
            logger.info(f"Translation target languages set to: {codes}")
            return ToolResult(result=f"翻译目标语言已更新为 {codes}", end_conversation=True)

        def switch_translation_impl(enable: bool) -> ToolResult:
            self.config.translate.enable = enable
            logger.info(f"Translation enabled set to: {enable}")
            return ToolResult(
                result=f"翻译功能已 {'启用' if enable else '禁用'}", end_conversation=True
            )

        global TOOL_CALL_MAP
        TOOL_CALL_MAP = {
            "change_target_language": change_target_language_impl,
            "switch_translation": switch_translation_impl,
        }

    async def translate(self, input_text: str) -> str:
        if not self.config.translate.enable:
            raise ValueError("Translation is disabled in config.")
        if not self.config.translate.languages:
            raise ValueError("No translation languages configured.")

        extra_body = None
        if self.config.openai.thinking is not None:
            extra_body = {
                "thinking": {"type": "enabled" if self.config.openai.thinking else "disabled"},
            }

        client = AsyncOpenAI(
            api_key=self.config.openai.api_key,
            base_url=self.config.openai.api_base,
        )

        conversation = self._get_conversation(self.config.translate.languages, input_text)

        logger.debug("Translation agent start")

        res: AgentResult = await self._run_agent(client, conversation, extra_body)
        content = res.content
        if res.from_tool:
            content = "[" + content + "]"

        return content

    async def _run_agent(
        self, client: AsyncOpenAI, conversation: list[dict], extra_body: dict | None
    ) -> AgentResult:
        tools = [TOOL_DEF_MAP[t] for t in (self.config.translate.tools or []) if t in TOOL_DEF_MAP]

        while True:
            response = await client.chat.completions.create(
                model=self.config.openai.model,
                messages=conversation,
                tools=tools,
                extra_body=extra_body,
            )

            message = response.choices[0].message
            logger.debug(f"Response: {message}")

            conversation.append(response.choices[0].message)

            tool_calls = message.tool_calls

            if tool_calls is None:
                return AgentResult(content=message.content or "No content available.")

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_function = TOOL_CALL_MAP.get(tool_name)

                if tool_function:
                    tool_result: ToolResult = tool_function(**tool_args)
                    logger.debug(f"Tool result for {tool_name}: {tool_result}")
                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result.result,
                        }
                    )
                    if tool_result.end_conversation:
                        return AgentResult(content=tool_result.result, from_tool=True)
                else:
                    logger.warning(f"Unknown tool: {tool_name}")

    @staticmethod
    def _get_conversation(languages: str, input_text: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": "You are a professional, authentic machine translation engine.",
            },
            {
                "role": "user",
                "content": "你的任务是读取用户输入,然后: "
                "直接将对话翻译成目标语言.不要过多思考和废话.多语言译文用换行隔开. "
                f"Current translate target language: {languages}.",
            },
            {
                "role": "user",
                "content": f"Translate the following input text. NO explanations. NO notes: \n\n{input_text}",
            },
        ]

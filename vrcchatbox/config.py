import logging
import os
from dataclasses import dataclass, field, fields

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    model: str = "openai/gpt-4o"
    api_base: str = "https://openrouter.ai/api/v1"
    api_key: str = None
    prompt: str = None
    thinking: bool | None = None


@dataclass
class BaseConfig:
    logging_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    osc_host: str = "127.0.0.1"
    osc_port: int = 9000


@dataclass
class TranslateConfig:
    enable: bool = False
    languages: list[str] = field(default_factory=lambda: ["en"])


class Config:
    def __init__(self, file_path: str = None):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self._data: CommentedMap | None = None
        self.base: BaseConfig = BaseConfig()
        self.openai: OpenAIConfig = OpenAIConfig()
        self.translate: TranslateConfig = TranslateConfig()
        self.file_path: str = self._resolve_config_path(file_path)

    @staticmethod
    def _resolve_config_path(file_path: str) -> str:
        """解析配置文件路径"""
        from pathlib import Path

        if file_path is not None:
            return file_path

        cwd_config = Path.cwd() / "config.yml"
        if cwd_config.exists():
            return str(cwd_config)

        return str(cwd_config)

    def load(self):
        logger.info(f"Loading configuration from {self.file_path}")
        if not os.path.exists(self.file_path):
            self._create_default_config(self.file_path)
            logger.info(f"Created configuration file: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            self._data = self.yaml.load(f)

        self.base = BaseConfig(**self._data.get("base", {}))
        self.openai = OpenAIConfig(**self._data.get("openai", {}))
        self.translate = TranslateConfig(**self._data.get("translate", {}))

    def save(self):
        if self._data is None:
            self._data = CommentedMap()

        self._sync_to_commented_map(self._data, "base", self.base)
        self._sync_to_commented_map(self._data, "openai", self.openai)
        self._sync_to_commented_map(self._data, "translate", self.translate)

        logger.info(f"Saving configuration to {self.file_path}")
        with open(self.file_path, "w", encoding="utf-8") as f:
            self.yaml.dump(self._data, f)

    @staticmethod
    def _sync_to_commented_map(data: CommentedMap, key: str, dataclass_obj) -> None:
        """确保 section 存在，并将 dataclass 字段逐一写入，保留注释。"""
        if key not in data or not isinstance(data[key], CommentedMap):
            data[key] = CommentedMap()
        section = data[key]
        for f in fields(dataclass_obj):
            section[f.name] = getattr(dataclass_obj, f.name)

    def _create_default_config(self, file: str = "config.yml"):
        self._data = CommentedMap(
            {
                "base": CommentedMap(
                    {
                        "logging_level": self.base.logging_level,
                        "host": self.base.host,
                        "port": self.base.port,
                        "osc_host": self.base.osc_host,
                        "osc_port": self.base.osc_port,
                    }
                ),
                "openai": CommentedMap(
                    {
                        "model": self.openai.model,
                        "api_base": self.openai.api_base,
                        "api_key": self.openai.api_key,
                        "prompt": self.openai.prompt,
                        "thinking": self.openai.thinking,
                    }
                ),
                "translate": CommentedMap(
                    {
                        "enable": self.translate.enable,
                        "languages": self.translate.languages,
                    }
                ),
            }
        )

        base: CommentedMap = self._data["base"]
        base.yaml_set_comment_before_after_key(
            "logging_level", before="日志级别: DEBUG / INFO / WARNING / ERROR", indent=2
        )
        base.yaml_set_comment_before_after_key("host", before="监听地址", indent=2)
        base.yaml_set_comment_before_after_key("port", before="监听端口", indent=2)
        base.yaml_set_comment_before_after_key("osc_host", before="OSC 目标地址", indent=2)
        base.yaml_set_comment_before_after_key("osc_port", before="OSC 目标端口", indent=2)

        openai: CommentedMap = self._data["openai"]
        openai.yaml_set_comment_before_after_key(
            "model", before="翻译使用的模型，如 gpt-4o", indent=2
        )
        openai.yaml_set_comment_before_after_key(
            "api_base", before="API 地址，使用代理时修改此项", indent=2
        )
        openai.yaml_set_comment_before_after_key("api_key", before="API Key", indent=2)
        openai.yaml_set_comment_before_after_key("prompt", before="系统提示词", indent=2)
        openai.yaml_set_comment_before_after_key(
            "thinking",
            before="思考模式开关 (true/false)，空则使用模型默认设置。需要模型支持。小模型推荐开启",
            indent=2,
        )

        translate: CommentedMap = self._data["translate"]
        translate.yaml_set_comment_before_after_key("enable", before="是否启用翻译", indent=2)
        translate.yaml_set_comment_before_after_key(
            "languages", before="目标语言列表，如 [zh, en]", indent=2
        )

        with open(file, "w", encoding="utf-8") as f:
            self.yaml.dump(self._data, f)

    def __repr__(self):
        return f"<Config openai: {self.openai!r}, translate: {self.translate!r}>"

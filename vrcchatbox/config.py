import logging
import os
from dataclasses import dataclass, fields
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    model: str = "gpt-5-mini"
    api_base: str = "https://api.openai.com/v1"
    api_key: str = None
    prompt: str = None


@dataclass
class BaseConfig:
    logging_level: str = "INFO"


@dataclass
class TranslateConfig:
    enable: bool = False
    languages: list[str] = None


class Config:
    def __init__(self, file_path: str = "config.yml"):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self._data: CommentedMap | None = None
        self.file_path: str = file_path
        self.base: BaseConfig = BaseConfig()
        self.openai: OpenAIConfig = OpenAIConfig()
        self.translate: TranslateConfig = TranslateConfig()

    def load(self, file: str = None):
        if file is None:
            file = self.file_path
        if not os.path.exists(file):
            self._create_default_config(file)

        with open(file, "r", encoding="utf-8") as f:
            self._data = self.yaml.load(f)

        self.base = BaseConfig(**self._data.get("base", {}))
        self.openai = OpenAIConfig(**self._data.get("openai", {}))
        self.translate = TranslateConfig(**self._data.get("translate", {}))

    def save(self, file: str = None):
        if file is None:
            file = self.file_path
        if self._data is None:
            self._data = CommentedMap()

        self._sync_to_commented_map(self._data, "base", self.base)
        self._sync_to_commented_map(self._data, "openai", self.openai)
        self._sync_to_commented_map(self._data, "translate", self.translate)

        logger.info(f"Saving configuration to {file}")
        with open(file, "w", encoding="utf-8") as f:
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
                    }
                ),
                "openai": CommentedMap(
                    {
                        "model": self.openai.model,
                        "api_base": self.openai.api_base,
                        "api_key": self.openai.api_key,
                        "prompt": self.openai.prompt,
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
        with open(file, "w", encoding="utf-8") as f:
            self.yaml.dump(self._data, f)

    def __repr__(self):
        return f"<Config openai: {self.openai!r}, translate: {self.translate!r}>"

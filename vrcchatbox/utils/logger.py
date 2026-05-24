import logging
import logging.config
import sys
from pathlib import Path
from copy import deepcopy
import yaml

_log_config: dict | None = None


def _load_log_file() -> dict:
    if getattr(sys, "frozen", False):
        log_file = Path(sys._MEIPASS) / "logging.yml"
    else:
        log_file = Path(__file__).parent.parent.parent / "logging.yml"
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f.read())
    except FileNotFoundError:
        raise FileNotFoundError(f"Logging config file not found: {log_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid logging config file format: {e}")


def setup_logger(logging_level: str | None = None):
    global _log_config
    _log_config = _load_log_file()
    if logging_level is not None:
        _log_config["handlers"]["console_handler"]["level"] = logging_level
    logging.config.dictConfig(_log_config)


def get_log_config() -> dict:
    if _log_config is None:
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")
    return deepcopy(_log_config)

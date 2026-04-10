import logging
import logging.config
import os
from pathlib import Path

import yaml


def get_log_config():
    log_file = Path(__file__).parent.parent.parent / "logging.yml"
    with open(log_file, "r", encoding="utf-8") as f:
        log_config = yaml.safe_load(f.read())
    return log_config


def setup_logger(logging_level: str = None):
    log_config = get_log_config()

    # 如果
    file_handler_config = log_config.get("handlers", {}).get("file_handler", {})
    filename = file_handler_config.get("filename")
    if filename:
        log_dir = Path(filename).parent
        os.makedirs(log_dir, exist_ok=True)

    if logging_level:
        log_config["handlers"]["console_handler"]["level"] = logging_level

    logging.config.dictConfig(log_config)


def get_logger(name):
    return logging.getLogger(name)

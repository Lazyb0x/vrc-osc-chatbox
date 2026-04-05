import logging
import logging.config
import os

import yaml

from vrcchatbox.config import Config


def get_log_config():
    with open("logging.yml", "r", encoding="utf-8") as f:
        log_config = yaml.safe_load(f.read())
    return log_config


def setup_logger(config: Config):
    os.makedirs('logs', exist_ok=True)
    log_config = get_log_config()
    log_config["handlers"]["console_handler"]["level"] = config.base.logging_level
    logging.config.dictConfig(log_config)


def get_logger(name):
    return logging.getLogger(name)

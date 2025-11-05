import sys

from loguru import logger

from common.config import config

# Loguru config
logger.remove()
logger.add(sys.stderr, format=config.log_format, level=config.log_level, colorize=True)


def get_logger(name: str | None = None):
    return logger.bind(name=name) if name else logger

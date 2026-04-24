import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging(level: Optional[str] = None) -> None:
    log_level = getattr(logging, (level or settings.LOG_LEVEL).upper(), logging.INFO)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

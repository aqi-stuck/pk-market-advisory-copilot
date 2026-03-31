import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging(level: Optional[str] = None) -> None:
    """
    Set up logging configuration for the application
    """
    log_level = getattr(logging, (level or settings.LOG_LEVEL).upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    """
    return logging.getLogger(name)
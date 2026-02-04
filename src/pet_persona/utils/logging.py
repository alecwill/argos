"""Logging configuration for Pet Persona AI."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Global console for rich output
console = Console()

# Logger cache
_loggers: dict[str, logging.Logger] = {}


def setup_logging(level: str = "INFO") -> None:
    """
    Set up logging configuration with rich formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_path=False,
            )
        ],
    )

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name. If None, returns the root logger.

    Returns:
        Logger instance
    """
    if name is None:
        name = "pet_persona"

    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)

    return _loggers[name]

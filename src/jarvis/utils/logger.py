"""Logger Utility for JARVIS with Rich formatting support."""

import logging
import sys
from typing import Optional

try:
    from rich.logging import RichHandler
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def setup_logger(log_level: str = "INFO", name: str = "jarvis") -> logging.Logger:
    """Configure and return the root logger for JARVIS."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers on the root logger
    if not logger.handlers:
        if HAS_RICH:
            handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_path=False,
            )
            formatter = logging.Formatter("[bold cyan]%(name)s[/] - %(message)s")
            handler.setFormatter(formatter)
        else:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def get_logger(module_name: str, log_level: str = "INFO") -> logging.Logger:
    """Get a child logger under the jarvis namespace."""
    full_name = f"jarvis.{module_name}" if not module_name.startswith("jarvis") else module_name
    # Ensure root jarvis logger is initialized once
    setup_logger(log_level=log_level, name="jarvis")
    return logging.getLogger(full_name)

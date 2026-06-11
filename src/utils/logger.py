"""Logging configuration"""

import sys
from pathlib import Path
from loguru import logger as _logger


def setup_logger(log_file: Path = None, level: str = "INFO"):
    """Configure logger with file and console output"""

    # Ensure console can render non-ASCII glyphs (✓, emoji) regardless of the
    # OS code page. Windows consoles default to cp1252, which raises
    # UnicodeEncodeError inside the loguru handler on such characters.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # already wrapped or not reconfigurable

    # Remove default handler
    _logger.remove()

    # Add console handler with colors
    _logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
    )

    # Add file handler if specified
    if log_file:
        _logger.add(
            log_file,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
        )

    return _logger


# Initialize logger
logger = setup_logger(level="INFO")

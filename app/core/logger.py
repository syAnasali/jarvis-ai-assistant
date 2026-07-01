"""Logging configuration using Loguru."""

import sys
from pathlib import Path
from typing import Any
from loguru import logger
from app.core.constants import APP_NAME, DEFAULT_LOG_LEVEL

# Define log format
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[name]}</cyan> - <level>{message}</level>"
)


def setup_logger(log_level: str = DEFAULT_LOG_LEVEL, log_dir: str = "logs") -> None:
    """Configures the Loguru logger handlers.

    Args:
        log_level: The logging severity level to capture.
        log_dir: The directory where log files will be stored.
    """
    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=log_level,
        colorize=True,
    )

    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Add file handler with daily rotation
    log_file = log_path / "jarvis.log"
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[name]} - {message}",
        level=log_level,
        rotation="00:00",  # Daily rotation at midnight
        retention="30 days",
        compression="zip",
    )


def get_logger(name: str) -> Any:
    """Returns a raw Loguru logger instance bound with the given module name.

    Args:
        name: The name of the module/logger.

    Returns:
        A bound loguru logger instance.
    """
    return logger.bind(name=name)


class JarvisLogger:
    """Wrapper class around Loguru logger to standardize system logging."""

    def __init__(self, name: str) -> None:
        """Initializes JarvisLogger with a specific module name.

        Args:
            name: Name of the logger context.
        """
        self._logger = logger.bind(name=name)

    @classmethod
    def configure(cls, log_level: str = DEFAULT_LOG_LEVEL, log_dir: str = "logs") -> None:
        """Configures system-wide logging settings.

        Args:
            log_level: Logging severity level.
            log_dir: Path to storage directory.
        """
        setup_logger(log_level=log_level, log_dir=log_dir)

    @classmethod
    def get_logger(cls, name: str) -> "JarvisLogger":
        """Returns a new JarvisLogger instance.

        Args:
            name: Module name context.

        Returns:
            JarvisLogger: The logger wrapper.
        """
        return cls(name)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs an informational message.

        Args:
            message: The log message.
            args: Positional format arguments.
            kwargs: Keyword format arguments.
        """
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a warning message.

        Args:
            message: The log message.
            args: Positional format arguments.
            kwargs: Keyword format arguments.
        """
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs an error message.

        Args:
            message: The log message.
            args: Positional format arguments.
            kwargs: Keyword format arguments.
        """
        self._logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a debug message.

        Args:
            message: The log message.
            args: Positional format arguments.
            kwargs: Keyword format arguments.
        """
        self._logger.debug(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Logs a critical error message.

        Args:
            message: The log message.
            args: Positional format arguments.
            kwargs: Keyword format arguments.
        """
        self._logger.critical(message, *args, **kwargs)


# Initialize default setup
setup_logger()

"""Shared logging utilities for MCP server."""

import logging
import sys
from typing import ClassVar

from loguru import logger


class LoguruInterceptHandler(logging.Handler):
    """Intercept standard logging and route to Loguru.

    This handler bridges the standard Python logging module with Loguru,
    ensuring all logs (from both systems) use the same formatting.
    Preserves custom 'extra' fields (used for structured logging).
    """

    # Standard logging fields that should not be treated as custom extras
    _STANDARD_FIELDS: ClassVar[set[str]] = {
        "name",
        "msg",
        "args",
        "created",
        "msecs",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
    }

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Extract custom extra fields from the log record.
        # These are fields added via logger.warning(..., extra={...}).
        # By preserving them and passing to loguru via bind(), they become
        # part of the log record's extra dict, enabling Datadog faceting.
        extras = {k: v for k, v in record.__dict__.items() if k not in self._STANDARD_FIELDS}

        # Bind extras to loguru context, then log the message.
        # logger.bind() merges extras into the record["extra"] dict,
        # making them available to sinks (e.g., Datadog, ELK) that support
        # structured logging.
        logger.bind(**extras).opt(exception=record.exc_info).log(level, record.getMessage())


def intercept_standard_logging() -> None:
    """Configure standard logging to route through Loguru.

    This should be called after Loguru is configured to ensure all
    standard logging calls are intercepted and formatted consistently.
    """
    logging.basicConfig(handlers=[LoguruInterceptHandler()], level=0, force=True)


def setup_logging(level: str = "INFO", stdio_mode: bool = False) -> None:
    """Configure logging with Loguru."""
    logger.remove()

    # In stdio mode, use stderr (stdout is reserved for JSON-RPC)
    sink = sys.stderr if stdio_mode else sys.stdout

    if level == "DEBUG":
        format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{line}</cyan> | <level>{message}</level>"
    else:
        format_str = (
            "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        )

    logger.add(
        sink,
        format=format_str,
        level=level,
        colorize=(not stdio_mode),
        diagnose=(level == "DEBUG"),
    )

    intercept_standard_logging()

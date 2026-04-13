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

    # Standard fields populated on every ``logging.LogRecord`` by the stdlib
    # logging module itself. They are NOT custom extras passed via
    # ``logger.warning(..., extra={...})`` and forwarding them to loguru would
    # both clobber loguru's own keys and pollute the structured log payload
    # with redundant data.
    #
    # The set is the union of:
    #   * Attributes assigned in ``logging.LogRecord.__init__`` (CPython source:
    #     Lib/logging/__init__.py — ``LogRecord.__init__``). This covers
    #     ``name, msg, args, levelname, levelno, pathname, filename, module,
    #     exc_info, exc_text, stack_info, lineno, funcName, created, msecs,
    #     relativeCreated, thread, threadName, processName, process``.
    #   * ``taskName`` — added in Python 3.12 by ``LogRecord.__init__`` for
    #     asyncio task identification. Included unconditionally so the set
    #     stays correct on 3.10-3.11 (key just won't be present at runtime).
    #   * ``message`` — set lazily by ``LogRecord.getMessage()``; appears on
    #     ``record.__dict__`` after formatting.
    #   * ``asctime`` — set lazily by formatters that reference ``%(asctime)s``.
    #
    # Anything else in ``record.__dict__`` is, by stdlib convention, a custom
    # extra passed via the ``extra={...}`` kwarg, and IS forwarded to loguru.
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
        # Resolve the loguru level: prefer the named level (DEBUG/INFO/WARNING/
        # ERROR/CRITICAL — all built into loguru), and for custom or otherwise
        # unknown levels fall back to the integer ``levelno``. We pass an int
        # (not ``str(levelno)``) because loguru only resolves stringified
        # levels via name lookup — passing ``"42"`` raises ValueError, while
        # passing the integer ``42`` is accepted directly per loguru's API.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

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

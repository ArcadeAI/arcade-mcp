"""Shared logging utilities for MCP server."""

import logging

from loguru import logger


class LoguruInterceptHandler(logging.Handler):
    """Intercept standard logging and route to Loguru.

    This handler bridges the standard Python logging module with Loguru,
    ensuring all logs (from both systems) use the same formatting.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def intercept_standard_logging() -> None:
    """Configure standard logging to route through Loguru.

    This should be called after Loguru is configured to ensure all
    standard logging calls are intercepted and formatted consistently.
    """
    logging.basicConfig(handlers=[LoguruInterceptHandler()], level=0, force=True)

"""MCP Middleware System"""

from arcade_mcp_server.middleware.base import (
    CallNext,
    Middleware,
    MiddlewareContext,
)
from arcade_mcp_server.middleware.error_handling import ErrorHandlingMiddleware
from arcade_mcp_server.middleware.logging import LoggingMiddleware
from arcade_mcp_server.middleware.telemetry import (
    DEFAULT_PASSBACK_ATTRIBUTES,
    DEFAULT_PASSBACK_EVENT_NAMES,
    TelemetryPassbackMiddleware,
)

__all__ = [
    "DEFAULT_PASSBACK_ATTRIBUTES",
    "DEFAULT_PASSBACK_EVENT_NAMES",
    "CallNext",
    "ErrorHandlingMiddleware",
    "LoggingMiddleware",
    "Middleware",
    "MiddlewareContext",
    "TelemetryPassbackMiddleware",
]

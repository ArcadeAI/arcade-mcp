"""Logging middleware for MCP server."""

import logging
import time
from typing import Any

from arcade_mcp_server.middleware.base import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger("arcade.mcp")


class LoggingMiddleware(Middleware):
    """Middleware that logs all MCP messages and timing information."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize logging middleware.

        Args:
            log_level: The log level to use for message logging
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Log all messages with timing information."""
        start_time = time.time()

        # Log the incoming message
        self._log_request(context)

        try:
            # Process the message
            result = await call_next(context)
        except Exception as e:
            # Log error
            elapsed = time.time() - start_time
            self._log_error(context, e, elapsed)
            raise
        else:
            # Log success
            elapsed = time.time() - start_time
            self._log_response(context, result, elapsed)
            return result

    def _log_request(self, context: MiddlewareContext[Any]) -> None:
        """Log incoming request."""
        if not logger.isEnabledFor(self.log_level):
            return

        method = context.method or "unknown"
        msg_type = context.type

        # Build log message
        parts = [f"[{msg_type.upper()}]", f"method={method}"]

        if context.request_id:
            parts.append(f"request_id={context.request_id}")
        if context.session_id:
            parts.append(f"session_id={context.session_id}")

        # Log message details based on method
        if hasattr(context.message, "params"):
            params = getattr(context.message, "params", None)
            if params:
                if hasattr(params, "name"):
                    parts.append(f"name={params.name}")
                elif hasattr(params, "uri"):
                    parts.append(f"uri={params.uri}")

        logger.log(self.log_level, " ".join(parts))

    def _log_response(
        self,
        context: MiddlewareContext[Any],
        result: Any,
        elapsed: float,
    ) -> None:
        """Log response with timing."""
        if not logger.isEnabledFor(self.log_level):
            return

        method = context.method or "unknown"
        elapsed_ms = int(elapsed * 1000)

        # Build log message
        parts = ["[RESPONSE]", f"method={method}", f"elapsed={elapsed_ms}ms"]

        if context.request_id:
            parts.append(f"request_id={context.request_id}")

        # Add result info based on type
        if isinstance(result, list):
            parts.append(f"count={len(result)}")
        elif hasattr(result, "content"):
            content = getattr(result, "content", [])
            if isinstance(content, list):
                parts.append(f"content_blocks={len(content)}")

        logger.log(self.log_level, " ".join(parts))

    def _log_error(
        self,
        context: MiddlewareContext[Any],
        error: Exception,
        elapsed: float,
    ) -> None:
        """Log error with timing."""
        method = context.method or "unknown"
        elapsed_ms = int(elapsed * 1000)

        parts = ["[ERROR]", f"method={method}", f"elapsed={elapsed_ms}ms"]

        if context.request_id:
            parts.append(f"request_id={context.request_id}")

        parts.append(f"error={type(error).__name__}: {error!s}")

        logger.error(" ".join(parts))

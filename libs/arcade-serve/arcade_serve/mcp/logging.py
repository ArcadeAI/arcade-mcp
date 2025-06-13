import json
import logging
import sys
import time
from typing import Any

from arcade_serve.mcp.types import (
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPMessage,
)

logger = logging.getLogger("arcade.mcp")


class MCPLoggingMiddleware:
    """
    Middleware for logging MCP requests and responses.
    Logs request and response details, including timing and errors.
    """

    def __init__(
        self,
        log_level: str = "INFO",
        log_request_body: bool = False,
        log_response_body: bool = False,
        log_errors: bool = True,
        min_duration_to_log_ms: int = 0,
        stdio_mode: bool = False,
    ) -> None:
        """
        Initialize the MCP logging middleware.

        Args:
            log_level: Logging level (default: "INFO").
            log_request_body: Whether to log full request bodies (default: False).
            log_response_body: Whether to log full response bodies (default: False).
            log_errors: Whether to log errors at ERROR level (default: True).
            min_duration_to_log_ms: Minimum duration in ms to log (0 logs all).
            stdio_mode: Whether running in stdio mode (redirects logs to stderr).
        """
        self.log_level = getattr(logging, log_level.upper())
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.log_errors = log_errors
        self.min_duration_to_log_ms = min_duration_to_log_ms
        self.request_log_format = "[MCP>] {method}{params_str} (id: {id})"
        self.response_log_format = "[MCP<] {method} completed in {duration:.2f}ms (id: {id})"
        self.error_log_format = "[MCP!] {method} error: {error} (id: {id})"

        # If in stdio mode, ensure MCP logs go to stderr
        if stdio_mode:
            self._redirect_logs_to_stderr()

        # Log that middleware is initialized
        logger.debug(f"MCP logging middleware initialized (level: {log_level})")

    def _redirect_logs_to_stderr(self) -> None:
        """Redirect MCP logs to stderr to avoid interfering with stdio communication."""
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add a stderr handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

        # Ensure we're not propagating to root logger which might log to stdout
        logger.propagate = False

        logger.debug("MCP logs redirected to stderr for stdio mode")

    def __call__(self, message: MCPMessage, direction: str) -> MCPMessage:
        """
        Process and log an MCP message.

        Args:
            message: The MCP message to process.
            direction: The message direction ("request" or "response").

        Returns:
            The original message (unmodified).
        """
        if direction == "request":
            self._log_request(message)
        else:
            self._log_response(message)
        return message

    def _log_request(self, message: MCPMessage) -> None:
        """
        Log an MCP request message.
        """
        if not isinstance(message, JSONRPCRequest):
            logger.debug(f"Ignoring non-request message: {type(message).__name__}")
            return

        try:
            # Store request start time for duration calculation
            message._mcp_start_time = time.time()  # type: ignore[attr-defined]

            # Format parameters for logging
            params_str = ""
            if self.log_request_body and hasattr(message, "params") and message.params is not None:
                params_str = f": {self._format_params(message.params)}"

            log_msg = self.request_log_format.format(
                method=message.method, params_str=params_str, id=getattr(message, "id", "none")
            )

            logger.log(self.log_level, log_msg)
        except Exception:
            logger.exception("Error logging request")

    def _log_response(self, message: MCPMessage) -> None:
        """
        Log an MCP response message.
        """
        if not isinstance(message, (JSONRPCResponse, JSONRPCError)):
            logger.debug(f"Ignoring non-response message: {type(message).__name__}")
            return

        try:
            # Calculate request duration if we have the start time
            duration_ms = 0
            request = getattr(message, "_request", None)
            if request:
                start_time = getattr(request, "_mcp_start_time", None)
                if start_time:
                    duration_ms = (time.time() - start_time) * 1000
            else:
                start_time = getattr(message, "_mcp_start_time", None)
                if start_time:
                    duration_ms = (time.time() - start_time) * 1000

            # Skip if below minimum duration threshold
            if self.min_duration_to_log_ms > 0 and duration_ms < self.min_duration_to_log_ms:
                return

            # Handle error responses
            if hasattr(message, "error") and message.error is not None:
                if self.log_errors:
                    error_msg = self.error_log_format.format(
                        method=getattr(message, "method", "unknown"),
                        error=getattr(message.error, "message", str(message.error)),
                        id=getattr(message, "id", "none"),
                    )
                    logger.error(error_msg)
                return

            # Log successful response
            result_str = ""
            if self.log_response_body and hasattr(message, "result"):
                result_str = f": {self._format_result(message.result)}"

            log_msg = self.response_log_format.format(
                method=getattr(message, "method", "unknown"),
                duration=duration_ms,
                id=getattr(message, "id", "none"),
                result_str=result_str,
            )

            logger.log(self.log_level, log_msg)
        except Exception:
            logger.exception("Error logging response")

    def _format_params(self, params: Any) -> str:
        """
        Format parameters for logging.
        """
        try:
            if isinstance(params, dict):
                # Handle common MCP params specially
                if "name" in params and "arguments" in params:
                    return f"{params['name']}({json.dumps(params.get('arguments', {}))})"
                return json.dumps(params)
            return str(params)
        except Exception:
            logger.debug(f"Error formatting params {params!s}")
            return str(params)

    def _format_result(self, result: Any) -> str:
        """
        Format result for logging.
        """
        try:
            if isinstance(result, dict):
                return json.dumps(result)
            return str(result)
        except Exception as e:
            logger.debug(f"Error formatting result {e!s}")
            return str(result)


def create_mcp_logging_middleware(**config: Any) -> MCPLoggingMiddleware:
    """
    Create an MCP logging middleware with the given configuration.

    Args:
        **config: Configuration options.

    Returns:
        An MCPLoggingMiddleware instance.
    """
    return MCPLoggingMiddleware(
        log_level=config.get("log_level", "INFO"),
        log_request_body=config.get("log_request_body", False),
        log_response_body=config.get("log_response_body", False),
        log_errors=config.get("log_errors", True),
        min_duration_to_log_ms=config.get("min_duration_to_log_ms", 0),
        stdio_mode=config.get("stdio_mode", False),
    )

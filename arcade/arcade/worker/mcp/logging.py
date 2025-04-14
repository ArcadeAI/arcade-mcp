import json
import logging
import time
import traceback
from typing import Any

from mcp.types import (
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
)

logger = logging.getLogger("arcade.mcp")


class MCPLoggingMiddleware:
    """
    Middleware for logging MCP requests and responses.

    This middleware captures MCP messages, logs them with timing information,
    and provides detailed logs for debugging and monitoring.
    """

    def __init__(
        self,
        log_level: str = "INFO",
        log_request_body: bool = False,
        log_response_body: bool = False,
        log_errors: bool = True,
        min_duration_to_log_ms: int = 0,
    ):
        """
        Initialize the MCP logging middleware.

        Args:
            log_level: Logging level (default: "INFO")
            log_request_body: Whether to log full request bodies (default: False)
            log_response_body: Whether to log full response bodies (default: False)
            log_errors: Whether to log errors at ERROR level (default: True)
            min_duration_to_log_ms: Minimum duration in ms to log (0 logs all)
        """
        self.log_level = getattr(logging, log_level.upper())
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.log_errors = log_errors
        self.min_duration_to_log_ms = min_duration_to_log_ms
        self.request_log_format = "[MCP>] {method}{params_str} (id: {id})"
        self.response_log_format = "[MCP<] {method} completed in {duration:.2f}ms (id: {id})"
        self.error_log_format = "[MCP!] {method} error: {error} (id: {id})"

        # Log that middleware is initialized
        logger.debug(f"MCP logging middleware initialized (level: {log_level})")

    def __call__(self, message: JSONRPCMessage, direction: str = "request") -> JSONRPCMessage:
        """
        Process and log an MCP message.

        This method makes the middleware callable so it can be used
        directly with the message processor.

        Args:
            message: The MCP message to process
            direction: The message direction ("request" or "response")

        Returns:
            The original message (unmodified)
        """
        return self.process_message(message, direction)

    def process_message(
        self, message: JSONRPCMessage, direction: str = "request"
    ) -> JSONRPCMessage:
        """
        Process and log an MCP message.

        Args:
            message: The MCP message to process
            direction: The message direction ("request" or "response")

        Returns:
            The original message (unmodified)
        """
        try:
            if direction == "request":
                self._log_request(message)
            else:
                self._log_response(message)
        except Exception as e:
            # Never let logging failures break the actual functionality
            logger.exception(f"Error in MCP logging middleware: {e!s}")  # noqa: TRY401
            # Add stack trace for debugging
            logger.debug(f"Stack trace: {traceback.format_exc()}")

        return message

    def _log_request(self, message: JSONRPCMessage) -> None:
        """Log an MCP request message."""
        if not isinstance(message, JSONRPCRequest):
            logger.debug(f"Ignoring non-request message: {type(message).__name__}")
            return

        try:
            # Store request start time for duration calculation
            message._mcp_start_time = time.time()

            # Format parameters for logging
            params_str = ""
            if self.log_request_body and hasattr(message, "params") and message.params is not None:
                params_str = f": {self._format_params(message.params)}"

            log_msg = self.request_log_format.format(
                method=message.method, params_str=params_str, id=getattr(message, "id", "none")
            )

            logger.log(self.log_level, log_msg)
        except Exception as e:
            logger.exception(f"Error logging request: {e!s}")  # noqa: TRY401
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def _log_response(self, message: JSONRPCMessage) -> None:
        """Log an MCP response message."""
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
                logger.debug(f"No request found for response: {message.id}")

            # Skip if below minimum duration threshold
            if self.min_duration_to_log_ms > 0 and duration_ms < self.min_duration_to_log_ms:
                return

            # Handle error responses
            if isinstance(message, JSONRPCError):
                if self.log_errors:
                    error_msg = self.error_log_format.format(
                        method=getattr(request, "method", "unknown"),
                        error=message.error.message,
                        id=message.id,
                    )
                    logger.error(error_msg)
                return

            # Log successful response
            result_str = ""
            if self.log_response_body and hasattr(message, "result"):
                result_str = f": {self._format_result(message.result)}"

            log_msg = self.response_log_format.format(
                method=getattr(request, "method", "unknown"),
                duration=duration_ms,
                id=message.id,
                result_str=result_str,
            )

            logger.log(self.log_level, log_msg)
        except Exception as e:
            logger.exception(f"Error logging response: {e!s}")  # noqa: TRY401
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def _format_params(self, params: dict[str, Any]) -> str:
        """Format parameters for logging."""
        try:
            if isinstance(params, dict):
                # Handle common MCP params specially
                if "name" in params and "arguments" in params:
                    return f"{params['name']}({json.dumps(params.get('arguments', {}))})"
                return json.dumps(params)
            return str(params)
        except Exception as e:
            logger.debug(f"Error formatting params: {e!s}")
            return str(params)

    def _format_result(self, result: Any) -> str:
        """Format result for logging."""
        try:
            if isinstance(result, dict):
                return json.dumps(result)
            return str(result)
        except Exception as e:
            logger.debug(f"Error formatting result: {e!s}")
            return str(result)


def create_mcp_logging_middleware(**config) -> MCPLoggingMiddleware | None:
    """
    Create an MCP logging middleware with the given configuration.

    Args:
        **config: Configuration options
            log_level: Logging level (default: "INFO")
            log_request_body: Whether to log full request bodies (default: False)
            log_response_body: Whether to log full response bodies (default: False)
            log_errors: Whether to log errors at ERROR level (default: True)
            min_duration_to_log_ms: Minimum duration in ms to log (0 logs all)

    Returns:
        An MCPLoggingMiddleware instance or None if MCP is not available
    """
    return MCPLoggingMiddleware(
        log_level=config.get("log_level", "INFO"),
        log_request_body=config.get("log_request_body", False),
        log_response_body=config.get("log_response_body", False),
        log_errors=config.get("log_errors", True),
        min_duration_to_log_ms=config.get("min_duration_to_log_ms", 0),
    )

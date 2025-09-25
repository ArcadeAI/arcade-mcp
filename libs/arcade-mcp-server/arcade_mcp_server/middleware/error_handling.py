"""Error handling middleware for MCP server."""

import logging
from typing import Any

from arcade_mcp_server.convert import convert_content_to_structured_content, convert_to_mcp_content
from arcade_mcp_server.middleware.base import CallNext, Middleware, MiddlewareContext
from arcade_mcp_server.types import CallToolResult, JSONRPCError

logger = logging.getLogger("arcade.mcp")


class ErrorHandlingMiddleware(Middleware):
    """Middleware that handles errors and converts them to appropriate responses."""

    def __init__(self, mask_error_details: bool = True):
        """Initialize error handling middleware.

        Args:
            mask_error_details: Whether to mask error details in responses
        """
        self.mask_error_details = mask_error_details

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Wrap all messages with error handling."""
        try:
            return await call_next(context)
        except Exception as e:
            return self._handle_error(context, e)

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Handle tool call errors specially."""
        try:
            return await call_next(context)
        except Exception as e:
            # For tool calls, return error as CallToolResult
            error_message = self._get_error_message(e)
            logger.exception(f"Error calling tool: {error_message}")

            content = convert_to_mcp_content(error_message)
            structured_content = convert_content_to_structured_content({"error": error_message})

            return CallToolResult(
                content=content,
                structuredContent=structured_content,
                isError=True,
            )

    def _handle_error(self, context: MiddlewareContext[Any], error: Exception) -> Any:
        """Convert exception to appropriate error response."""
        error_message = self._get_error_message(error)

        # Log the full error
        logger.exception(f"Error processing {context.method}: {error}")

        # Get request ID if available
        request_id = context.request_id
        if not request_id and hasattr(context.message, "id"):
            request_id = str(getattr(context.message, "id", "unknown"))

        # Return JSON-RPC error
        return JSONRPCError(
            id=request_id or "unknown",
            error={
                "code": self._get_error_code(error),
                "message": error_message,
            },
        )

    def _get_error_message(self, error: Exception) -> str:
        """Get appropriate error message based on configuration."""
        if self.mask_error_details:
            # Return generic message for security
            error_type = type(error).__name__
            if error_type in ["ValueError", "TypeError", "KeyError"]:
                return "Invalid request parameters"
            elif error_type in ["NotFoundError", "FileNotFoundError"]:
                return "Resource not found"
            elif error_type in ["PermissionError", "AuthorizationError"]:
                return "Permission denied"
            else:
                return "Internal server error"
        else:
            # Return actual error message for debugging
            return str(error)

    def _get_error_code(self, error: Exception) -> int:
        """Get JSON-RPC error code for exception."""
        error_type = type(error).__name__

        # Map common errors to JSON-RPC codes
        if error_type in ["ValueError", "TypeError", "KeyError"]:
            return -32602  # Invalid params
        elif error_type in ["NotFoundError", "FileNotFoundError"]:
            return -32601  # Method not found
        elif error_type in ["PermissionError", "AuthorizationError"]:
            return -32603  # Internal error (used for auth)
        else:
            return -32603  # Generic internal error

"""Tests for Error Handling Middleware."""

import asyncio
from unittest.mock import Mock, patch

import pytest
from arcade_mcp_server.exceptions import (
    AuthorizationError,
    MCPError,
    NotFoundError,
    ServerError,
    ToolRuntimeError,
)
from arcade_mcp_server.middleware.base import MiddlewareContext
from arcade_mcp_server.middleware.error_handling import ErrorHandlingMiddleware
from arcade_mcp_server.types import JSONRPCError


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware class."""

    @pytest.fixture
    def error_middleware(self):
        """Create error handling middleware (no masking)."""
        return ErrorHandlingMiddleware(mask_error_details=False)

    @pytest.fixture
    def error_middleware_masked(self):
        """Create error handling middleware with masking."""
        return ErrorHandlingMiddleware(mask_error_details=True)

    @pytest.fixture
    def context(self):
        """Create a test context."""
        return MiddlewareContext(
            message={"id": 1, "method": "test"},
            mcp_context=Mock(),
            request_id="req-123",
        )

    @pytest.mark.asyncio
    async def test_successful_request(self, error_middleware, context):
        """Test that successful requests pass through."""

        async def handler(ctx):
            return {"result": "success"}

        result = await error_middleware(context, handler)

        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_not_found_error(self, error_middleware, context):
        """Test handling of NotFoundError."""

        async def handler(ctx):
            raise NotFoundError("Resource not found: test.txt")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.id == "req-123"
        assert result.error["code"] == -32601
        assert "Resource not found: test.txt" in result.error["message"]

    @pytest.mark.asyncio
    async def test_server_error(self, error_middleware, context):
        """Test handling of ServerError."""

        async def handler(ctx):
            raise ServerError("Server operation failed")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert "Server operation failed" in result.error["message"]

    @pytest.mark.asyncio
    async def test_authorization_error(self, error_middleware, context):
        """Test handling of AuthorizationError."""

        async def handler(ctx):
            raise AuthorizationError("User not authorized")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert "User not authorized" in result.error["message"]

    @pytest.mark.asyncio
    async def test_tool_runtime_error(self, error_middleware, context):
        """Test handling of ToolError."""

        async def handler(ctx):
            raise ToolRuntimeError("Tool execution failed: API rate limit")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert "Tool execution failed" in result.error["message"]

    @pytest.mark.asyncio
    async def test_generic_mcp_error(self, error_middleware, context):
        """Test handling of generic MCPError."""

        async def handler(ctx):
            raise MCPError("Something went wrong")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert "Something went wrong" in result.error["message"]

    @pytest.mark.asyncio
    async def test_unexpected_error(self, error_middleware, context):
        """Test handling of unexpected exceptions."""

        async def handler(ctx):
            raise RuntimeError("Unexpected error occurred")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert "Unexpected error occurred" in result.error["message"]

    @pytest.mark.asyncio
    async def test_error_masking(self, error_middleware_masked, context):
        """Test error detail masking in production."""

        async def handler(ctx):
            raise RuntimeError("Sensitive internal error with secrets")

        result = await error_middleware_masked(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603
        assert result.error["message"] == "Internal server error"
        # Should not include sensitive details
        assert "data" not in result.error

    @pytest.mark.asyncio
    async def test_error_with_traceback(self, error_middleware, context):
        """Test that error response contains expected structure (no traceback in current impl)."""

        async def handler(ctx):
            def nested():
                raise ValueError("Deep error")

            nested()

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32602
        assert "Deep error" in result.error["message"]

    @pytest.mark.asyncio
    async def test_notification_error_handling(self, error_middleware):
        """Test error handling for notifications (no ID)."""
        # Notifications don't have an ID
        context = MiddlewareContext(message={"method": "notification/test"}, mcp_context=Mock())

        async def handler(ctx):
            raise ValueError("Notification error")

        # For notifications, errors are still returned as JSONRPCError
        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert hasattr(result, "id")

    @pytest.mark.asyncio
    async def test_error_logging(self, error_middleware, context):
        """Test that errors are logged appropriately."""
        with patch("arcade_mcp_server.middleware.error_handling.logger") as mock_logger:

            async def handler(ctx):
                raise ToolRuntimeError("Tool failed")

            await error_middleware(context, handler)

            # Should log the error using exception
            mock_logger.exception.assert_called()
            call_args = mock_logger.exception.call_args[0][0]
            assert "Tool failed" in call_args

    @pytest.mark.asyncio
    async def test_preserves_error_code_mappings(self, error_middleware, context):
        """Test that error codes map per implementation."""
        test_cases = [
            (NotFoundError("Not found"), -32601),
            (AuthorizationError("Unauthorized"), -32603),
            (ToolRuntimeError("Tool error"), -32603),
            (RuntimeError("Boom"), -32603),
        ]

        for error, expected_code in test_cases:

            async def handler(ctx, e=error):
                raise e

            result = await error_middleware(context, handler)
            assert result.error["code"] == expected_code

    @pytest.mark.asyncio
    async def test_error_context_preservation(self, error_middleware):
        """Test that context information is preserved in errors."""
        context = MiddlewareContext(
            message={"id": 123, "method": "tools/call"},
            mcp_context=Mock(),
            request_id="req-456",
            session_id="sess-789",
        )

        async def handler(ctx):
            assert ctx.request_id == "req-456"
            raise ValueError("Context test")

        result = await error_middleware(context, handler)

        # Error response should use request_id when present
        assert result.id == "req-456"

    @pytest.mark.asyncio
    async def test_async_error_handling(self, error_middleware, context):
        """Test handling of errors in async operations."""

        async def handler(ctx):
            await asyncio.sleep(0.01)
            raise OSError("Async operation failed")

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert result.error["code"] == -32603

    @pytest.mark.asyncio
    async def test_chained_error_handling(self, error_middleware, context):
        """Test error handling with chained exceptions."""

        async def handler(ctx):
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e

        result = await error_middleware(context, handler)

        assert isinstance(result, JSONRPCError)
        assert "Wrapped error" in result.error["message"]

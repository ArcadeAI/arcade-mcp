"""Tests for Logging Middleware."""

import asyncio
import logging
from unittest.mock import Mock, patch

import pytest
from arcade_mcp_server.middleware.base import MiddlewareContext
from arcade_mcp_server.middleware.logging import LoggingMiddleware
from arcade_mcp_server.types import (
    JSONRPCError,
    JSONRPCResponse,
)


class TestLoggingMiddleware:
    """Test LoggingMiddleware class."""

    @pytest.fixture
    def logging_middleware(self):
        """Create logging middleware."""
        return LoggingMiddleware(log_level="INFO")

    @pytest.fixture
    def debug_logging_middleware(self):
        """Create debug logging middleware."""
        return LoggingMiddleware(log_level="DEBUG")

    @pytest.fixture
    def context(self):
        """Create a test context."""
        return MiddlewareContext(
            message={"id": 1, "method": "test/method", "params": {"key": "value"}},
            mcp_context=Mock(),
            method="test/method",
            request_id="req-123",
            session_id="sess-456",
            source="client",
            type="request",
        )

    @pytest.mark.asyncio
    async def test_request_logging(self, logging_middleware, context):
        """Test that requests are logged."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return {"result": "success"}

            await logging_middleware(context, handler)

            # Should log the request using log() method, not info()
            mock_logger.log.assert_called()
            # Check the first call (request log)
            first_call = mock_logger.log.call_args_list[0]
            call_args = first_call[0][1]  # Second arg is the message
            assert "req-123" in call_args
            assert "test/method" in call_args
            assert "REQUEST" in call_args

    @pytest.mark.asyncio
    async def test_response_logging(self, logging_middleware, context):
        """Test that responses are logged."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return JSONRPCResponse(id=1, result={"status": "ok"})

            await logging_middleware(context, handler)

            # Should log both request and response
            assert mock_logger.log.call_count >= 2

            # Find response log
            response_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "RESPONSE" in call[0][1]:
                    response_logged = True
                    assert "req-123" in call[0][1]
                    assert "elapsed=" in call[0][1]

            assert response_logged

    @pytest.mark.asyncio
    async def test_error_response_logging(self, logging_middleware, context):
        """Test that error responses are logged."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return JSONRPCError(id=1, error={"code": -32603, "message": "Internal error"})

            await logging_middleware(context, handler)

            # Should log response even for error responses
            response_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "RESPONSE" in call[0][1]:
                    response_logged = True

            assert response_logged

    @pytest.mark.asyncio
    async def test_exception_logging(self, logging_middleware, context):
        """Test that exceptions are logged."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                raise ValueError("Test exception")

            with pytest.raises(ValueError):
                await logging_middleware(context, handler)

            # Should log the exception
            mock_logger.error.assert_called()
            error_args = mock_logger.error.call_args[0][0]
            assert "ERROR" in error_args
            assert "ValueError" in error_args
            assert "Test exception" in error_args

    @pytest.mark.asyncio
    async def test_timing_information(self, logging_middleware, context):
        """Test that timing information is included."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                # Simulate some work
                await asyncio.sleep(0.05)
                return {"result": "success"}

            await logging_middleware(context, handler)

            # Find response log with timing
            timing_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "RESPONSE" in call[0][1] and "elapsed=" in call[0][1]:
                    timing_logged = True
                    # Should show elapsed time in ms
                    assert "ms" in call[0][1]

            assert timing_logged

    @pytest.mark.asyncio
    async def test_debug_level_logging(self, debug_logging_middleware, context):
        """Test debug level logging includes more details."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:
            # Set logger level to debug
            mock_logger.isEnabledFor.return_value = True

            async def handler(ctx):
                return {"result": "success", "data": {"nested": "value"}}

            await debug_logging_middleware(context, handler)

            # Should have log calls at debug level
            mock_logger.log.assert_called()
            # First call should be with DEBUG level (logging.DEBUG = 10)
            assert mock_logger.log.call_args_list[0][0][0] == logging.DEBUG

    @pytest.mark.asyncio
    async def test_notification_logging(self, logging_middleware):
        """Test logging of notifications (no ID)."""
        context = MiddlewareContext(
            message={"method": "notifications/test"},
            mcp_context=Mock(),
            method="notifications/test",
            type="notification",
        )

        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return None  # Notifications typically return None

            await logging_middleware(context, handler)

            # Should log notification
            mock_logger.log.assert_called()
            notification_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "NOTIFICATION" in call[0][1]:
                    notification_logged = True

            assert notification_logged

    @pytest.mark.asyncio
    async def test_log_filtering(self, logging_middleware):
        """Test that logging respects log level."""
        # Create middleware with high log level
        middleware = LoggingMiddleware(log_level="ERROR")

        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:
            # Configure mock logger level
            mock_logger.isEnabledFor.side_effect = lambda level: level >= logging.ERROR

            context = MiddlewareContext(
                message={"id": 1, "method": "test"}, mcp_context=Mock(), method="test"
            )

            async def handler(ctx):
                return {"result": "success"}

            await middleware(context, handler)

            # Should not log info level messages
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_method_specific_logging(self, logging_middleware):
        """Test logging includes method-specific information."""
        # Test tool call
        # Create a mock object with params attribute for the middleware to access
        message = Mock()
        params_mock = Mock()
        params_mock.name = "MyTool"  # Set as attribute, not in constructor
        params_mock.arguments = {"x": 1}
        message.params = params_mock

        tool_context = MiddlewareContext(message=message, mcp_context=Mock(), method="tools/call")

        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return {"result": "tool result"}

            await logging_middleware(tool_context, handler)

            # Should log tool name
            tool_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "name=MyTool" in call[0][1]:
                    tool_logged = True

            assert tool_logged

    @pytest.mark.asyncio
    async def test_session_tracking(self, logging_middleware, context):
        """Test that session ID is included in logs."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return {"result": "success"}

            await logging_middleware(context, handler)

            # Should include session ID
            session_logged = False
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1 and "sess-456" in call[0][1]:
                    session_logged = True

            assert session_logged

    @pytest.mark.asyncio
    async def test_large_message_truncation(self, logging_middleware):
        """Test that large messages are truncated."""
        # Create a large message
        large_data = "x" * 10000
        context = MiddlewareContext(
            message={"id": 1, "method": "test", "params": {"data": large_data}},
            mcp_context=Mock(),
            method="test",
        )

        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:

            async def handler(ctx):
                return {"result": large_data}

            await logging_middleware(context, handler)

            # Log messages should be reasonable size
            for call in mock_logger.log.call_args_list:
                if len(call[0]) > 1:
                    log_msg = call[0][1]
                    # Should not include the full large data
                    assert len(log_msg) < 5000

    @pytest.mark.asyncio
    async def test_concurrent_request_logging(self, logging_middleware):
        """Test logging handles concurrent requests correctly."""
        with patch("arcade_mcp_server.middleware.logging.logger") as mock_logger:
            # Track which requests were logged
            logged_ids = set()

            def track_logs(level, msg, *args, **kwargs):
                # Extract request IDs from log messages
                if "req-" in msg:
                    import re

                    match = re.search(r"req-(\d+)", msg)
                    if match:
                        logged_ids.add(match.group(1))

            mock_logger.log.side_effect = track_logs

            # Create multiple concurrent requests
            async def make_request(req_id):
                ctx = MiddlewareContext(
                    message={"id": req_id, "method": "test"},
                    mcp_context=Mock(),
                    method="test",
                    request_id=f"req-{req_id}",
                )

                async def handler(c):
                    await asyncio.sleep(0.01)  # Simulate work
                    return {"result": f"result-{req_id}"}

                return await logging_middleware(ctx, handler)

            # Run concurrent requests
            await asyncio.gather(*[make_request(i) for i in range(5)])

            # All requests should be logged
            assert len(logged_ids) >= 5

    def test_log_level_configuration(self):
        """Test log level configuration."""
        # Test different log levels
        for level_str, level_int in [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
        ]:
            middleware = LoggingMiddleware(log_level=level_str)
            assert middleware.log_level == level_int

        # Test case insensitive - log_level is stored as integer
        middleware = LoggingMiddleware(log_level="info")
        assert middleware.log_level == logging.INFO

"""Tests for Middleware base classes."""

from unittest.mock import Mock

import pytest
from arcade_mcp_server.middleware.base import (
    Middleware,
    MiddlewareContext,
)


class TestMiddlewareBase:
    """Test base middleware functionality."""

    def test_middleware_context_creation(self):
        """Test MiddlewareContext creation."""
        message = {"method": "test", "params": {}}
        context = MiddlewareContext(
            message=message,
            mcp_context=Mock(),
            source="client",
            type="request",
            method="test",
            request_id="req-123",
            session_id="sess-456",
        )

        assert context.message == message
        assert context.source == "client"
        assert context.type == "request"
        assert context.method == "test"
        assert context.request_id == "req-123"
        assert context.session_id == "sess-456"

    def test_middleware_context_metadata(self):
        """Test metadata management in context."""
        context = MiddlewareContext(message={}, mcp_context=Mock())

        # Initial metadata is empty
        assert context.metadata == {}

        # Add metadata
        context.metadata["key1"] = "value1"
        context.metadata["key2"] = {"nested": "value"}

        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"]["nested"] == "value"

    @pytest.mark.asyncio
    async def test_basic_middleware(self):
        """Test basic middleware implementation."""
        # Track calls
        middleware_called = False

        class TestMiddleware(Middleware):
            async def __call__(self, context, call_next):
                nonlocal middleware_called
                middleware_called = True
                # Pass through to next
                return await call_next(context)

        # Create middleware
        middleware = TestMiddleware()

        # Mock next handler
        async def next_handler(ctx):
            return {"result": "success"}

        # Execute
        context = MiddlewareContext(message={}, mcp_context=Mock())
        result = await middleware(context, next_handler)

        assert middleware_called
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_middleware_modification(self):
        """Test middleware that modifies context."""

        class ModifyingMiddleware(Middleware):
            async def __call__(self, context, call_next):
                # Modify context before
                context.metadata["before"] = True

                # Call next
                result = await call_next(context)

                # Modify result after
                if isinstance(result, dict):
                    result["after"] = True

                return result

        middleware = ModifyingMiddleware()

        async def next_handler(ctx):
            assert ctx.metadata["before"] is True
            return {"original": "value"}

        context = MiddlewareContext(message={}, mcp_context=Mock())
        result = await middleware(context, next_handler)

        assert result == {"original": "value", "after": True}

    @pytest.mark.asyncio
    async def test_middleware_chain(self):
        """Test chaining multiple middleware."""
        call_order = []

        class Middleware1(Middleware):
            async def __call__(self, context, call_next):
                call_order.append("m1_before")
                result = await call_next(context)
                call_order.append("m1_after")
                return result

        class Middleware2(Middleware):
            async def __call__(self, context, call_next):
                call_order.append("m2_before")
                result = await call_next(context)
                call_order.append("m2_after")
                return result

        # Build chain manually
        async def final_handler(ctx):
            call_order.append("handler")
            return "result"

        m2 = Middleware2()
        m1 = Middleware1()

        # Chain: m1 -> m2 -> handler
        async def m2_wrapped(ctx):
            return await m2(ctx, final_handler)

        context = MiddlewareContext(message={}, mcp_context=Mock())
        result = await m1(context, m2_wrapped)

        # Check order
        assert call_order == ["m1_before", "m2_before", "handler", "m2_after", "m1_after"]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_middleware_error_propagation(self):
        """Test error propagation through middleware."""

        class ErrorMiddleware(Middleware):
            async def __call__(self, context, call_next):
                try:
                    return await call_next(context)
                except ValueError as e:
                    # Transform error
                    raise RuntimeError(f"Wrapped: {e}")

        middleware = ErrorMiddleware()

        async def failing_handler(ctx):
            raise ValueError("Original error")

        context = MiddlewareContext(message={}, mcp_context=Mock())

        with pytest.raises(RuntimeError) as exc_info:
            await middleware(context, failing_handler)

        assert "Wrapped: Original error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_middleware_short_circuit(self):
        """Test middleware that short-circuits the chain."""

        class ShortCircuitMiddleware(Middleware):
            async def __call__(self, context, call_next):
                # Don't call next for certain conditions
                if context.message.get("skip"):
                    return {"short_circuited": True}
                return await call_next(context)

        middleware = ShortCircuitMiddleware()

        # Normal flow
        context1 = MiddlewareContext(message={}, mcp_context=Mock())

        async def handler(ctx):
            return {"normal": True}

        result1 = await middleware(context1, handler)
        assert result1 == {"normal": True}

        # Short circuit
        context2 = MiddlewareContext(message={"skip": True}, mcp_context=Mock())
        result2 = await middleware(context2, handler)
        assert result2 == {"short_circuited": True}

    def test_middleware_protocol(self):
        """Test that Middleware follows the protocol."""
        # Middleware should be a protocol/ABC
        assert callable(Middleware)

        # Should not be instantiable directly
        # (This is more of a documentation test since Python protocols are flexible)

        # But subclasses should work
        class ConcreteMiddleware(Middleware):
            async def __call__(self, context, call_next):
                return await call_next(context)

        # Should be instantiable
        middleware = ConcreteMiddleware()
        assert isinstance(middleware, Middleware)

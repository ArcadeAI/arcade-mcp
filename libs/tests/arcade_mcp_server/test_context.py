"""Tests for MCP Context implementation."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_mcp_server.context import Context
from arcade_mcp_server.context import get_current_model_context as get_current_context
from arcade_mcp_server.context import set_current_model_context as set_current_context
from arcade_mcp_server.types import (
    ModelHint,
    ModelPreferences,
)


class TestContext:
    """Test Context class and context management."""

    def test_context_creation(self, mcp_server):
        """Test context creation with various parameters."""
        # Basic context
        context = Context(server=mcp_server)

        assert context.server == mcp_server
        assert context.request_id is None
        assert context.session_id is None

        # Context with request ID
        context2 = Context(server=mcp_server, request_id="req-123")

        assert context2.request_id == "req-123"
        assert context2.session_id is None  # No session set yet

    def test_context_implements_protocol(self):
        """Test that Context implements MCPContext protocol."""
        # Context should expose namespaced adapters
        assert hasattr(Context, "log")
        assert hasattr(Context, "progress")
        assert hasattr(Context, "resources")
        assert hasattr(Context, "tools")
        assert hasattr(Context, "prompts")
        assert hasattr(Context, "sampling")
        assert hasattr(Context, "ui")
        assert hasattr(Context, "notifications")

    def test_context_var_management(self):
        """Test context variable get/set functionality."""
        server = Mock()
        context = Context(server=server)

        # Initially no current context
        assert get_current_context() is None

        # Set context
        token = set_current_context(context)
        assert get_current_context() == context

        # Clear context
        set_current_context(None, token)
        assert get_current_context() is None

    @pytest.mark.asyncio
    async def test_context_isolation(self):
        """Test that contexts are isolated between async tasks."""
        server = Mock()
        context1 = Context(server=server, request_id="req-1")
        context2 = Context(server=server, request_id="req-2")

        results = []

        async def task1():
            set_current_context(context1)
            results.append(get_current_context())

        async def task2():
            set_current_context(context2)
            results.append(get_current_context())

        # Run tasks
        await asyncio.gather(task1(), task2())

        # Each task should have its own context
        assert len(results) == 2
        # Context vars are task-local, so both should see their own context
        assert context1 in results
        assert context2 in results

    @pytest.mark.asyncio
    async def test_logging_methods(self, mcp_server):
        """Test logging methods."""
        session = Mock()
        session.send_log_message = AsyncMock()

        context = Context(server=mcp_server)
        context.set_session(session)

        # Test all log levels
        await context.log.debug("Debug message")
        await context.log.info("Info message")
        await context.log.warning("Warning message")
        await context.log.error("Error message")

        # Verify calls
        assert session.send_log_message.call_count == 4

        # Test with extra metadata
        await context.log("info", "Test message", logger_name="test.logger", extra={"key": "value"})

        # Check the call - context passes logger_name but session expects logger
        call_kwargs = session.send_log_message.call_args[1]
        assert call_kwargs["level"] == "info"
        assert isinstance(call_kwargs["data"], dict)
        assert call_kwargs["data"]["msg"] == "Test message"
        assert call_kwargs["data"]["extra"] == {"key": "value"}
        assert call_kwargs["logger"] == "test.logger"

    @pytest.mark.asyncio
    async def test_logging_without_session(self, mcp_server):
        """Test logging when session is not available."""
        context = Context(server=mcp_server)

        # Should not raise errors
        await context.log.debug("Debug message")
        await context.log.info("Info message")
        await context.log.warning("Warning message")
        await context.log.error("Error message")

    @pytest.mark.asyncio
    async def test_tools_methods(self, mcp_server):
        """Test tools methods."""
        context = Context(server=mcp_server)

        # Test list tools
        tools = await context.tools.list()
        assert len(tools) == 2

        # Test call raw for tool that doesn't exist
        result = await context.tools.call_raw("TheLimitDoesNotExist", {"param": "value"})
        assert result.isError is True

        # Test call raw for tool that exists
        result = await context.tools.call_raw(
            "TestToolkit_test_tool", {"text": "The text to send to tool"}
        )
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_progress_reporting(self, mcp_server):
        """Test progress reporting functionality."""
        session = Mock()
        session.send_progress_notification = AsyncMock()
        session._request_meta = Mock(progressToken="task-123")

        context = Context(server=mcp_server)
        context.set_session(session)

        # Report progress
        await context.progress.report(50, 100, "Processing...")

        session.send_progress_notification.assert_called_once_with(
            progress_token="task-123", progress=50, total=100, message="Processing..."
        )

        # Without total
        await context.progress.report(0.75, message="Almost done")

        assert session.send_progress_notification.call_count == 2

        # Test without progress token - should not call send_progress_notification
        session2 = Mock(spec=["send_progress_notification"])
        session2.send_progress_notification = AsyncMock()
        # Without _request_meta attribute, progress won't be reported
        context2 = Context(server=mcp_server)
        context2.set_session(session2)

        await context2.progress.report(25, 100)
        session2.send_progress_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_resource_reading(self, mcp_server):
        """Test resource reading through context."""
        # Mock server's resource reading
        mcp_server._mcp_read_resource = AsyncMock(
            return_value=[{"uri": "file://test.txt", "text": "Test content"}]
        )

        context = Context(server=mcp_server)

        resources = await context.resources.read("file://test.txt")

        assert len(resources) == 1
        assert resources[0]["text"] == "Test content"
        mcp_server._mcp_read_resource.assert_called_once_with("file://test.txt")

    @pytest.mark.asyncio
    async def test_list_roots(self, mcp_server):
        """Test listing roots."""
        session = Mock()
        # Return an object with roots attribute
        result = Mock()
        result.roots = [{"uri": "file:///home", "name": "Home"}]
        session.list_roots = AsyncMock(return_value=result)

        context = Context(server=mcp_server)
        context.set_session(session)

        roots = await context.resources.list_roots()

        assert len(roots) == 1
        assert roots[0]["name"] == "Home"

    @pytest.mark.asyncio
    async def test_sampling(self, mcp_server):
        """Test sampling functionality."""
        session = Mock()
        # Mock the response with content attribute
        result = Mock()
        result.content = {"type": "text", "text": "Response"}
        session.create_message = AsyncMock(return_value=result)

        context = Context(server=mcp_server)
        context.set_session(session)

        # Mock client capabilities check
        session.check_client_capability = Mock(return_value=True)

        # Test basic sampling
        result = await context.sampling.create_message(
            messages="Hello", system_prompt="Be helpful", temperature=0.7, max_tokens=100
        )

        assert result["type"] == "text"
        assert result["text"] == "Response"

        # Test with model preferences
        result = await context.sampling.create_message(
            messages=[{"role": "user", "content": "Hello"}],
            model_preferences=ModelPreferences(hints=[ModelHint(name="claude-3")]),
        )

        assert session.create_message.call_count == 2

    @pytest.mark.asyncio
    async def test_sampling_without_capability(self, mcp_server):
        """Test sampling when client doesn't support it."""
        session = Mock()
        context = Context(server=mcp_server)
        context.set_session(session)

        # Mock client capabilities check to return False
        session.check_client_capability = Mock(return_value=False)

        with pytest.raises(ValueError) as exc_info:
            await context.sampling.create_message(messages=["Hello"], max_tokens=32)

        assert "Client does not support sampling" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_elicitation(self, mcp_server):
        """Test user input elicitation."""
        session = Mock()
        # Mock the elicit method on session
        session.elicit = AsyncMock(return_value={"value": "user input"})

        context = Context(server=mcp_server)
        context.set_session(session)

        # Test string elicitation
        result = await context.ui.elicit("Enter your name:")

        assert result == {"value": "user input"}
        session.elicit.assert_called_once_with(
            message="Enter your name:",
            requested_schema={"type": "object", "properties": {}},
            timeout=300.0,
        )

        # Test with schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = await context.ui.elicit("Enter details:", schema=schema)

        assert result == {"value": "user input"}
        assert session.elicit.call_count == 2
        session.elicit.assert_called_with(
            message="Enter details:", requested_schema=schema, timeout=300
        )

    @pytest.mark.asyncio
    async def test_notification_queueing(self, mcp_server):
        """Test notification queueing methods."""
        session = Mock()
        session.send_tool_list_changed = AsyncMock()
        session.send_resource_list_changed = AsyncMock()
        session.send_prompt_list_changed = AsyncMock()

        context = Context(server=mcp_server)
        context.set_session(session)

        # Queue notifications - they are queued and not sent immediately
        await context.notifications.tools.list_changed()
        await context.notifications.resources.list_changed()
        await context.notifications.prompts.list_changed()

        # Notifications should be queued, not sent immediately
        assert "notifications/tools/list_changed" in context._notification_queue
        assert "notifications/resources/list_changed" in context._notification_queue
        assert "notifications/prompts/list_changed" in context._notification_queue

        # Mock the notification manager
        nm = Mock()
        nm.notify_tool_list_changed = AsyncMock()
        nm.notify_resource_list_changed = AsyncMock()
        mcp_server.notification_manager = nm

        # Add session_id to session
        session.session_id = "test-session-123"

        # Now flush notifications
        await context._flush_notifications()

        # Queue should be cleared after flush
        assert len(context._notification_queue) == 0

        # Verify notifications were sent with the session_id
        nm.notify_tool_list_changed.assert_called_once_with(["test-session-123"])
        nm.notify_resource_list_changed.assert_called_once_with(["test-session-123"])

    def test_parse_model_preferences(self, mcp_server):
        """Test model preferences parsing."""
        context = Context(server=mcp_server)

        # Test with ModelPreferences object
        prefs = ModelPreferences(hints=[ModelHint(name="gpt-4")])
        parsed = context._parse_model_preferences(prefs)
        assert parsed == prefs

        # Test with string
        parsed = context._parse_model_preferences("gpt-4")
        assert isinstance(parsed, ModelPreferences)
        assert len(parsed.hints) == 1
        assert parsed.hints[0].name == "gpt-4"

        # Test with list of strings
        parsed = context._parse_model_preferences(["gpt-4", "claude-3"])
        assert isinstance(parsed, ModelPreferences)
        assert len(parsed.hints) == 2
        assert parsed.hints[0].name == "gpt-4"
        assert parsed.hints[1].name == "claude-3"

        # Test with None
        parsed = context._parse_model_preferences(None)
        assert parsed is None

        # Test with invalid type
        with pytest.raises(ValueError, match="Invalid model preferences type"):
            context._parse_model_preferences({"invalid": "dict"})

    @pytest.mark.asyncio
    async def test_context_without_server(self):
        """Test operations that require server when server is None."""
        # Create a context with a server that will be garbage collected
        server = Mock()
        context = Context(server=server)
        # Clear the strong reference to server
        del server

        with pytest.raises(RuntimeError) as exc_info:
            # This should raise because the weak reference is dead
            _ = context.server

        assert "Server instance is no longer available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_without_session(self, mcp_server):
        """Test operations that require session when session is None."""
        context = Context(server=mcp_server)

        # These should return empty/None without raising
        roots = await context.resources.list_roots()
        assert roots == []

        # Sampling should raise ValueError when session is None
        with pytest.raises(ValueError, match="Session not available"):
            await context.sampling.create_message(messages=["Hello"], max_tokens=32)

        # Elicit should also raise ValueError when session is None
        with pytest.raises(ValueError, match="Session not available"):
            await context.ui.elicit("Enter text")

    @pytest.mark.asyncio
    async def test_context_as_context_manager(self, mcp_server):
        """Test using context as an async context manager."""
        context = Context(server=mcp_server)

        # Enter context
        async with context as ctx:
            assert ctx == context
            # Context should be set as current
            assert get_current_context() == context

        # After exit, context should be reset
        assert get_current_context() is None

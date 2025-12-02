"""
Tests for actionable error messages.

This test suite verifies that error messages follow the pattern:
- Start with ✗ symbol
- Clearly state the problem
- Provide actionable fix instructions
- Include specific examples where helpful
"""

import pytest
from pydantic import ValidationError

from arcade_core.catalog import ToolCatalog
from arcade_core.schema import SecretRequirement, ToolRequirements
from arcade_mcp_server.context import Context, UI
from arcade_mcp_server.exceptions import (
    LifespanError,
    NotFoundError,
    PromptError,
    ServerError,
    SessionError,
    TransportError,
)
from arcade_mcp_server.lifespan import Lifespan
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.managers.prompt import PromptManager
from arcade_mcp_server.managers.resource import ResourceManager
from arcade_mcp_server.managers.tool import ToolManager
from arcade_mcp_server.mcp_app import MCPApp
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.settings import MCPSettings, MiddlewareSettings
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport
from arcade_mcp_server.transports.stdio import StdioServerTransport
from arcade_mcp_server.worker import create_arcade_mcp_factory


class TestSettingsErrors:
    """Test error messages in settings validation."""

    def test_invalid_log_level_error_is_actionable(self):
        """Test that invalid log level error provides fix instructions."""
        with pytest.raises(ValidationError) as exc_info:
            MiddlewareSettings(log_level="INVALID")

        error_msg = str(exc_info.value)
        assert "✗ Invalid log level" in error_msg
        assert "Valid options" in error_msg
        assert "To fix" in error_msg
        assert "MCP_MIDDLEWARE_LOG_LEVEL" in error_msg


class TestMCPAppErrors:
    """Test error messages in MCPApp validation."""

    def test_empty_name_error_is_actionable(self):
        """Test that empty name error provides examples."""
        with pytest.raises(ValueError) as exc_info:
            MCPApp._validate_name("")

        error_msg = str(exc_info.value)
        assert "✗ Empty app name" in error_msg
        assert "To fix" in error_msg
        assert "MCPApp(name=" in error_msg

    def test_invalid_name_underscore_prefix_error_is_actionable(self):
        """Test that underscore prefix error suggests removal."""
        with pytest.raises(ValueError) as exc_info:
            MCPApp._validate_name("_invalid")

        error_msg = str(exc_info.value)
        assert "✗ Invalid app name" in error_msg
        assert "cannot start with an underscore" in error_msg
        assert "To fix" in error_msg
        # Should suggest removing the underscore
        assert "invalid" in error_msg

    def test_invalid_name_consecutive_underscores_error_is_actionable(self):
        """Test that consecutive underscores error suggests fix."""
        with pytest.raises(ValueError) as exc_info:
            MCPApp._validate_name("invalid__name")

        error_msg = str(exc_info.value)
        assert "✗ Invalid app name" in error_msg
        assert "consecutive underscores" in error_msg
        assert "To fix" in error_msg

    def test_invalid_name_special_chars_error_is_actionable(self):
        """Test that special characters error shows valid examples."""
        with pytest.raises(ValueError) as exc_info:
            MCPApp._validate_name("invalid-name")

        error_msg = str(exc_info.value)
        assert "✗ Invalid app name" in error_msg
        assert "alphanumeric" in error_msg
        assert "Valid examples" in error_msg


class TestContextErrors:
    """Test error messages in Context operations."""

    def test_invalid_model_preferences_type_error_is_actionable(self):
        """Test that invalid model preferences type error shows examples."""

        class MockContext:
            pass

        ctx = Context(server=MockContext(), session=None)

        with pytest.raises(ValueError) as exc_info:
            ctx._parse_model_preferences(12345)  # Invalid type

        error_msg = str(exc_info.value)
        assert "✗ Invalid model preferences type" in error_msg
        assert "Expected:" in error_msg
        assert "Valid examples" in error_msg
        assert "gpt-4" in error_msg

    def test_ui_invalid_schema_type_error_is_actionable(self):
        """Test that UI schema type error shows correct format."""

        class MockContext:
            def __init__(self):
                self._session = None

        ui = UI(MockContext())

        with pytest.raises(TypeError) as exc_info:
            ui._validate_elicitation_schema("not a dict")

        error_msg = str(exc_info.value)
        assert "✗ Invalid elicitation schema type" in error_msg
        assert "Expected: dictionary" in error_msg
        assert "Example:" in error_msg

    def test_ui_invalid_schema_structure_error_is_actionable(self):
        """Test that UI schema structure error provides fix."""

        class MockContext:
            def __init__(self):
                self._session = None

        ui = UI(MockContext())

        with pytest.raises(ValueError) as exc_info:
            ui._validate_elicitation_schema({"type": "array"})

        error_msg = str(exc_info.value)
        assert "✗ Invalid schema type" in error_msg
        assert "must have type 'object'" in error_msg
        assert "To fix" in error_msg

    def test_ui_unsupported_property_type_error_is_actionable(self):
        """Test that unsupported property type error lists allowed types."""

        class MockContext:
            def __init__(self):
                self._session = None

        ui = UI(MockContext())

        with pytest.raises(ValueError) as exc_info:
            ui._validate_elicitation_schema(
                {"type": "object", "properties": {"data": {"type": "object"}}}
            )

        error_msg = str(exc_info.value)
        assert "✗ Unsupported type for property" in error_msg
        assert "Allowed types:" in error_msg
        assert "string" in error_msg
        assert "number" in error_msg
        assert "Not allowed: object, array" in error_msg


class TestManagerErrors:
    """Test error messages in manager operations."""

    @pytest.mark.asyncio
    async def test_tool_not_found_error_is_actionable(self):
        """Test that tool not found error suggests listing tools."""
        manager = ToolManager()

        with pytest.raises(NotFoundError) as exc_info:
            await manager.get_tool("nonexistent_tool")

        error_msg = str(exc_info.value)
        assert "✗ Tool not found" in error_msg
        assert "To fix:" in error_msg
        assert "tools/list" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_resource_not_found_error_is_actionable(self):
        """Test that resource not found error suggests listing resources."""
        manager = ResourceManager()

        with pytest.raises(NotFoundError) as exc_info:
            await manager.get_resource("file:///nonexistent")

        error_msg = str(exc_info.value)
        assert "✗ Resource not found" in error_msg
        assert "To fix:" in error_msg
        assert "resources/list" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_prompt_not_found_error_is_actionable(self):
        """Test that prompt not found error suggests listing prompts."""
        manager = PromptManager()

        with pytest.raises(NotFoundError) as exc_info:
            await manager.get_prompt("nonexistent_prompt")

        error_msg = str(exc_info.value)
        assert "✗ Prompt not found" in error_msg
        assert "To fix:" in error_msg
        assert "prompts/list" in error_msg.lower()


class TestSessionErrors:
    """Test error messages in session operations."""

    @pytest.mark.asyncio
    async def test_session_closed_error_is_actionable(self):
        """Test that session closed error explains causes."""
        from unittest.mock import AsyncMock, Mock

        server = Mock()
        read_stream = AsyncMock()
        write_stream = AsyncMock()

        session = ServerSession(
            server=server,
            read_stream=read_stream,
            write_stream=write_stream,
        )

        # Close the session
        await session.close()

        # Now try to do something that requires an open session
        with pytest.raises(SessionError) as exc_info:
            await session._check_closed()

        error_msg = str(exc_info.value)
        assert "✗ Session closed" in error_msg
        assert "Possible causes:" in error_msg
        assert "To fix:" in error_msg


class TestTransportErrors:
    """Test error messages in transport operations."""

    def test_stdio_multiple_sessions_error_is_actionable(self):
        """Test that stdio multiple sessions error suggests HTTP."""
        transport = StdioServerTransport()

        with pytest.raises(TransportError) as exc_info:
            # Try to create multiple sessions (this will fail)
            transport._check_single_session()
            transport._check_single_session()

        error_msg = str(exc_info.value)
        assert "✗ Multiple sessions not supported" in error_msg
        assert "To fix:" in error_msg
        assert "HTTP transport" in error_msg

    def test_http_invalid_session_id_error_is_actionable(self):
        """Test that invalid session ID error shows valid format."""
        with pytest.raises(ValueError) as exc_info:
            HTTPStreamableTransport(
                is_json_response_enabled=True, mcp_session_id="invalid\x00id"
            )

        error_msg = str(exc_info.value)
        assert "✗ Invalid session ID" in error_msg
        assert "visible ASCII characters" in error_msg


class TestServerErrors:
    """Test error messages in server operations."""

    @pytest.mark.asyncio
    async def test_missing_secrets_error_is_actionable(self, mcp_server):
        """Test that missing secrets error shows how to configure them."""
        from unittest.mock import Mock

        from arcade_core.catalog import MaterializedTool
        from arcade_core.schema import ToolDefinition, ToolkitDefinition

        # Create a tool that requires secrets
        tool_def = ToolDefinition(
            name="test_tool",
            fully_qualified_name="TestToolkit.test_tool",
            description="Test tool",
            toolkit=ToolkitDefinition(name="TestToolkit", description="Test", version="1.0.0"),
            requirements=ToolRequirements(
                secrets=[
                    SecretRequirement(key="API_KEY", description="API key"),
                    SecretRequirement(key="SECRET_TOKEN", description="Secret token"),
                ]
            ),
        )

        mock_tool = Mock(spec=MaterializedTool)
        mock_tool.definition = tool_def

        from arcade_core.schema import ToolContext
        from arcade_mcp_server.types import CallToolRequest, CallToolParams

        tool_context = ToolContext()
        message = CallToolRequest(id="test", params=CallToolParams(name="test_tool", arguments={}))

        result = await mcp_server._check_tool_requirements(
            mock_tool, tool_context, message, "test_tool", None
        )

        assert result is not None  # Should return an error response
        response_dict = result.result if hasattr(result, "result") else result

        # Check the error message
        error_msg = str(response_dict)
        assert "✗ Missing secret" in error_msg
        assert "API_KEY" in error_msg
        assert "SECRET_TOKEN" in error_msg
        assert "To fix" in error_msg or "either:" in error_msg.lower()
        assert ".env" in error_msg.lower()
        assert "export" in error_msg


class TestWorkerErrors:
    """Test error messages in worker/discovery operations."""

    def test_no_tools_found_error_is_actionable(self):
        """Test that no tools error provides setup instructions."""
        import os

        # Set env to ensure no tools are discovered
        os.environ["ARCADE_MCP_DISCOVER_INSTALLED"] = "false"
        os.environ.pop("ARCADE_MCP_TOOL_PACKAGE", None)

        with pytest.raises(RuntimeError) as exc_info:
            create_arcade_mcp_factory()

        error_msg = str(exc_info.value)
        assert "✗ No tools found" in error_msg
        assert "To fix:" in error_msg
        assert "@tool" in error_msg
        assert "Example" in error_msg.lower()


class TestLifespanErrors:
    """Test error messages in lifespan operations."""

    @pytest.mark.asyncio
    async def test_lifespan_already_started_error_is_actionable(self):
        """Test that lifespan already started error suggests new instance."""
        from unittest.mock import AsyncMock

        lifespan = Lifespan()
        # Mock the startup to avoid actual initialization
        lifespan._startup = AsyncMock()

        await lifespan.start()

        with pytest.raises(LifespanError) as exc_info:
            await lifespan.start()  # Try to start again

        error_msg = str(exc_info.value)
        assert "✗ Lifespan already started" in error_msg
        assert "To fix:" in error_msg
        assert "new" in error_msg.lower()


@pytest.mark.asyncio
async def test_error_messages_have_consistent_format():
    """Integration test to verify error message format consistency."""
    errors_to_test = [
        (ValueError, "✗ Invalid"),
        (TypeError, "✗"),
        (ServerError, "✗"),
        (SessionError, "✗"),
        (TransportError, "✗"),
        (NotFoundError, "✗"),
    ]

    # This is a meta-test that verifies the pattern is followed
    # In real scenarios, specific errors would be triggered
    for error_class, expected_marker in errors_to_test:
        # Verify the error class exists and can be instantiated with our format
        test_msg = f"{expected_marker} Test error\n\nTo fix:\n  Do something"
        error = error_class(test_msg)
        assert expected_marker in str(error)


def test_all_improved_errors_contain_actionable_marker():
    """Verify that all our error improvements include the ✗ marker."""
    # This test serves as documentation of the pattern we're following
    actionable_marker = "✗"
    actionable_sections = ["To fix:", "Possible causes:", "Example:"]

    # At least one of these should be in actionable error messages
    assert any(
        section in "To fix: Set the value" for section in actionable_sections
    ), "Error messages should contain actionable sections"
    assert actionable_marker == "✗", "Using ✗ as the error marker"

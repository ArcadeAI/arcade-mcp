"""Tests for MCP Server implementation."""

import asyncio
import contextlib
import json
from typing import Annotated
from unittest.mock import AsyncMock, Mock, patch

import pytest
from arcade_core.auth import OAuth2
from arcade_core.catalog import MaterializedTool, ToolMeta, create_func_models
from arcade_core.errors import ErrorKind, ToolRuntimeError
from arcade_core.schema import (
    InputParameter,
    OAuth2Requirement,
    ToolAuthRequirement,
    ToolCallError,
    ToolCallOutput,
    ToolContext,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ToolSecretRequirement,
    ValueSchema,
)
from arcade_mcp_server import tool
from arcade_mcp_server.exceptions import IncompleteAuthContextError
from arcade_mcp_server.middleware import Middleware
from arcade_mcp_server.resource_server.base import ResourceOwner
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import InitializationState
from arcade_mcp_server.types import (
    CallToolRequest,
    CallToolResult,
    InitializeRequest,
    InitializeResult,
    JSONRPCError,
    JSONRPCResponse,
    ListToolsRequest,
    ListToolsResult,
    PingRequest,
    TaskStatus,
    URLElicitationRequiredError,
)


class TestMCPServer:
    """Test MCPServer class."""

    def test_server_initialization(self, tool_catalog, mcp_settings):
        """Test server initialization with various configurations."""
        # Basic initialization
        server = MCPServer(
            catalog=tool_catalog,
            name="Test Server",
            version="1.9.0",
            settings=mcp_settings,
        )

        assert server.name == "Test Server"
        assert server.version == "1.9.0"
        assert server.title == "Test Server"
        assert server.settings == mcp_settings

        # With custom title and instructions
        server2 = MCPServer(
            catalog=tool_catalog,
            name="Test Server",
            version="1.0.0",
            title="Custom Title",
            instructions="Custom instructions",
        )

        assert server2.title == "Custom Title"
        assert server2.instructions == "Custom instructions"

    def test_server_initialization_with_settings_defaults(self, tool_catalog):
        """Test server initialization uses settings when parameters not provided."""
        from arcade_mcp_server.settings import MCPSettings, ServerSettings

        settings = MCPSettings(
            server=ServerSettings(
                name="SettingsName",
                version="2.0.0",
                title="SettingsTitle",
                instructions="Settings instructions",
            )
        )

        # Initialize without name/version - should use settings
        server = MCPServer(catalog=tool_catalog, settings=settings)

        assert server.name == "SettingsName"
        assert server.version == "2.0.0"
        assert server.title == "SettingsTitle"
        assert server.instructions == "Settings instructions"

    def test_server_initialization_parameters_override_settings(self, tool_catalog):
        """Test server initialization parameters override settings."""
        from arcade_mcp_server.settings import MCPSettings, ServerSettings

        settings = MCPSettings(
            server=ServerSettings(
                name="SettingsName",
                version="2.0.0",
                title="SettingsTitle",
                instructions="Settings instructions",
            )
        )

        # Initialize with explicit parameters (should override settings)
        server = MCPServer(
            catalog=tool_catalog,
            name="ParamName",
            version="3.0.0",
            title="ParamTitle",
            instructions="Param instructions",
            settings=settings,
        )

        assert server.name == "ParamName"
        assert server.version == "3.0.0"
        assert server.title == "ParamTitle"
        assert server.instructions == "Param instructions"

    def test_server_initialization_title_fallback_logic(self, tool_catalog):
        """Test server initialization title fallback logic."""
        from arcade_mcp_server.settings import MCPSettings, ServerSettings

        # Test 1: Title parameter provided (should be used)
        server1 = MCPServer(
            catalog=tool_catalog,
            name="TestServer",
            title="ExplicitTitle",
        )
        assert server1.title == "ExplicitTitle"

        # Test 2: No title parameter but settings has non-default title
        settings2 = MCPSettings(
            server=ServerSettings(
                name="SettingsServer",
                title="CustomSettingsTitle",
            )
        )
        server2 = MCPServer(catalog=tool_catalog, settings=settings2)
        assert server2.title == "CustomSettingsTitle"

        # Test 3: No title parameter, settings has default title (should use name)
        settings3 = MCPSettings(
            server=ServerSettings(
                name="SettingsServer",
                title="ArcadeMCP",  # Default value
            )
        )
        server3 = MCPServer(catalog=tool_catalog, settings=settings3)
        assert server3.title == "SettingsServer"

        # Test 4: No title parameter, no settings title (should use name)
        settings4 = MCPSettings(
            server=ServerSettings(
                name="SettingsServer",
                title=None,
            )
        )
        server4 = MCPServer(catalog=tool_catalog, settings=settings4)
        assert server4.title == "SettingsServer"

    def test_server_initialization_instructions_fallback(self, tool_catalog):
        """Test server initialization instructions fallback logic."""
        from arcade_mcp_server.settings import MCPSettings, ServerSettings

        # Test 1: Instructions parameter provided (should be used)
        server1 = MCPServer(
            catalog=tool_catalog,
            instructions="Explicit instructions",
        )
        assert server1.instructions == "Explicit instructions"

        # Test 2: No instructions parameter (should use settings)
        settings2 = MCPSettings(
            server=ServerSettings(
                instructions="Settings instructions",
            )
        )
        server2 = MCPServer(catalog=tool_catalog, settings=settings2)
        assert server2.instructions == "Settings instructions"

        # Test 3: No instructions parameter, no settings (should use default)
        settings3 = MCPSettings(
            server=ServerSettings(
                instructions=None,
            )
        )
        server3 = MCPServer(catalog=tool_catalog, settings=settings3)
        assert "available tools" in server3.instructions.lower()

    def test_handler_registration(self, tool_catalog):
        """Test that all required handlers are registered."""
        server = MCPServer(catalog=tool_catalog)

        expected_handlers = [
            "ping",
            "initialize",
            "tools/list",
            "tools/call",
            "resources/list",
            "resources/templates/list",
            "resources/read",
            "prompts/list",
            "prompts/get",
            "logging/setLevel",
        ]

        for method in expected_handlers:
            assert method in server._handlers
            assert callable(server._handlers[method])

    @pytest.mark.asyncio
    async def test_server_lifecycle(self, tool_catalog, mcp_settings):
        """Test server startup and shutdown."""
        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
        )

        # Start server
        await server.start()

        # Stop server
        await server.stop()

    @pytest.mark.asyncio
    async def test_handle_ping(self, mcp_server):
        """Test ping request handling."""
        message = PingRequest(jsonrpc="2.0", id=1, method="ping")

        response = await mcp_server._handle_ping(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 1
        assert response.result == {}

    @pytest.mark.asyncio
    async def test_handle_initialize(self, mcp_server):
        """Test initialize request handling."""
        message = InitializeRequest(
            jsonrpc="2.0",
            id=1,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Create mock session
        session = Mock()
        session.set_client_params = Mock()

        response = await mcp_server._handle_initialize(message, session=session)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 1
        assert isinstance(response.result, InitializeResult)
        assert response.result.protocolVersion is not None
        assert response.result.serverInfo.name == mcp_server.name
        assert response.result.serverInfo.version == mcp_server.version

        # Check session was updated
        session.set_client_params.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_list_tools(self, mcp_server):
        """Test list tools request handling."""
        message = ListToolsRequest(jsonrpc="2.0", id=2, method="tools/list", params={})

        response = await mcp_server._handle_list_tools(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 2
        assert isinstance(response.result, ListToolsResult)
        assert len(response.result.tools) > 0

    @pytest.mark.asyncio
    async def test_handle_call_tool(self, mcp_server):
        """Test tool call request handling."""
        message = CallToolRequest(
            jsonrpc="2.0",
            id=3,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "Hello"}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 3
        assert isinstance(response.result, CallToolResult)
        assert response.result.structuredContent is not None
        assert "result" in response.result.structuredContent
        assert "Echo: Hello" in response.result.structuredContent["result"]

    @pytest.mark.asyncio
    async def test_handle_call_tool_with_requires_auth(self, mcp_server):
        """Test tool call request handling with authorization."""

        # Mock arcade client so the server thinks API key is configured
        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        mock_auth_response = Mock()
        mock_auth_response.status = "pending"
        mock_auth_response.url = "https://example.com/auth"

        # Patch the _check_authorization method to return a tool that has unsatisfied authorization
        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        message = CallToolRequest(
            jsonrpc="2.0",
            id=3,
            method="tools/call",
            params={"name": "TestToolkit.sample_tool_with_auth", "arguments": {"text": "Hello"}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 3
        assert isinstance(response.result, CallToolResult)
        assert response.result.structuredContent is None
        content_text = response.result.content[0].text
        assert "Authorization required" in content_text
        assert "needs your permission" in content_text
        # The authorization URL is included in the human-readable message
        assert "https://example.com/auth" in content_text

    @pytest.mark.asyncio
    async def test_handle_call_tool_with_requires_auth_no_api_key(self, mcp_server):
        """Test tool call request handling with authorization when no Arcade API key is configured."""

        # Ensure no arcade client is configured
        mcp_server.arcade = None

        message = CallToolRequest(
            jsonrpc="2.0",
            id=3,
            method="tools/call",
            params={"name": "TestToolkit.sample_tool_with_auth", "arguments": {"text": "Hello"}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.id == 3
        assert isinstance(response.result, CallToolResult)
        assert response.result.structuredContent is None
        content_text = response.result.content[0].text
        assert "Missing Arcade API key" in content_text
        assert "requires authorization" in content_text
        assert "arcade login" in content_text
        assert "ARCADE_API_KEY" in content_text

    @pytest.mark.asyncio
    async def test_handle_call_tool_not_found(self, mcp_server):
        """Test calling a non-existent tool returns JSON-RPC error."""
        message = CallToolRequest(
            jsonrpc="2.0",
            id=3,
            method="tools/call",
            params={"name": "NonExistent.tool", "arguments": {}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602
        assert "Unknown tool" in response.error["message"]

    @pytest.mark.asyncio
    async def test_handle_message_routing(self, mcp_server, initialized_server_session):
        """Test message routing to appropriate handlers."""
        # Test valid method
        message = {"jsonrpc": "2.0", "id": 1, "method": "ping"}

        response = await mcp_server.handle_message(message, session=initialized_server_session)

        assert response is not None
        assert str(response.id) == "1"
        assert response.result == {}

        # Test invalid method
        message = {"jsonrpc": "2.0", "id": 2, "method": "invalid/method"}

        response = await mcp_server.handle_message(message, session=initialized_server_session)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601
        assert "Method not found" in response.error["message"]

    @pytest.mark.asyncio
    async def test_handle_message_invalid_format(self, mcp_server):
        """Test handling of invalid message formats."""
        # Non-dict message
        response = await mcp_server.handle_message("invalid", session=None)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32600
        assert "Invalid request" in response.error["message"]

    @pytest.mark.asyncio
    async def test_initialization_state_enforcement(self, mcp_server):
        """Test that non-initialize methods are blocked before initialization."""
        # Create uninitialized session
        session = Mock()
        session.initialization_state = InitializationState.NOT_INITIALIZED

        # Try to call tools/list before initialization
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

        response = await mcp_server.handle_message(message, session=session)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32600
        assert "Not initialized" in response.error["message"]
        assert "cannot be processed before the session is initialized" in response.error["message"]

    @pytest.mark.asyncio
    async def test_notification_handling(self, mcp_server):
        """Test handling of notification messages."""
        session = Mock()
        session.mark_initialized = Mock()

        # Send initialized notification
        message = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        response = await mcp_server.handle_message(message, session=session)

        # Notifications should not return a response
        assert response is None
        # Session should be marked as initialized
        session.mark_initialized.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_chain(self, tool_catalog, mcp_settings):
        """Test middleware chain execution."""
        # Create a test middleware
        test_middleware_called = False

        class TestMiddleware(Middleware):
            async def __call__(self, context, call_next):
                nonlocal test_middleware_called
                test_middleware_called = True
                # Modify context
                context.metadata["test"] = "value"
                return await call_next(context)

        # Create server with middleware
        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            middleware=[TestMiddleware()],
        )
        await server.start()

        # Send a message
        message = {"jsonrpc": "2.0", "id": 1, "method": "ping"}

        response = await server.handle_message(message)

        # Middleware should have been called
        assert test_middleware_called
        assert response is not None

    @pytest.mark.asyncio
    async def test_error_handling_middleware(self, mcp_server):
        """Test that error handling middleware catches exceptions."""

        # Mock a handler to raise an exception
        async def failing_handler(*args, **kwargs):
            raise Exception("Test error")

        mcp_server._handlers["test/fail"] = failing_handler

        message = {"jsonrpc": "2.0", "id": 1, "method": "test/fail"}

        response = await mcp_server.handle_message(message)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603
        # Error details should be masked in production
        if mcp_server.settings.middleware.mask_error_details:
            assert response.error["message"] == "Internal error"
        else:
            assert "Test error" in response.error["message"]

    @pytest.mark.asyncio
    async def test_session_management(self, mcp_server):
        """Test session creation and cleanup."""

        # Create a mock read stream that waits
        async def mock_stream():
            try:
                while True:
                    await asyncio.sleep(1)  # Keep the session alive
                    yield None  # Yield nothing
            except asyncio.CancelledError:
                pass

        mock_read_stream = mock_stream()
        mock_write_stream = AsyncMock()

        # Track sessions
        initial_sessions = len(mcp_server._sessions)

        # Create a new connection
        session_task = asyncio.create_task(
            mcp_server.run_connection(mock_read_stream, mock_write_stream)
        )

        # Give it time to register
        await asyncio.sleep(0.1)

        # Should have one more session
        assert len(mcp_server._sessions) == initial_sessions + 1

        # Cancel the session
        session_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await session_task

        # Give it time to clean up
        await asyncio.sleep(0.1)

        # Session should be cleaned up
        assert len(mcp_server._sessions) == initial_sessions

    @pytest.mark.asyncio
    async def test_authorization_check(self, mcp_server):
        """Test tool authorization checking."""

        # Ensure the arcade client is not configured in the case that the test environment
        # unintentionally has the ARCADE_API_KEY set
        mcp_server.arcade = None

        tool = Mock()
        tool.definition.requirements.authorization = ToolAuthRequirement(
            provider_type="oauth2", provider_id="test-provider"
        )

        # Without arcade client configured
        with pytest.raises(Exception) as exc_info:
            await mcp_server._check_authorization(tool)

        assert "Authorization check called without Arcade API key configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_tool_requirements_no_requirements(self, mcp_server, materialized_tool):
        """Test tool requirements checking when tool has no requirements."""

        # Create a tool with no requirements
        tool = materialized_tool
        tool.definition.requirements = None

        tool_context = ToolContext()
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "Hello"}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.test_tool"
        )

        # Should return None when no requirements because this means the tool can be executed
        assert result is None

    @pytest.mark.asyncio
    async def test_check_tool_requirements_auth_no_arcade_client(self, mcp_server):
        """Test tool requirements checking when tool requires auth but no Arcade client configured."""

        # Ensure no arcade client is configured
        mcp_server.arcade = None

        # Create a tool that requires authorization
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            )
        )

        tool_context = ToolContext()
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.auth_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.auth_tool"
        )

        # Should return error response
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        content_text = result.result.content[0].text
        assert "Missing Arcade API key" in content_text
        assert "requires authorization" in content_text
        assert "ARCADE_API_KEY" in content_text
        assert result.result.structuredContent is None

    @pytest.mark.asyncio
    async def test_check_tool_requirements_auth_pending(self, mcp_server):
        """Test tool requirements checking when authorization is pending."""

        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        # Create a tool that requires authorization
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            )
        )

        mock_auth_response = Mock()
        mock_auth_response.status = "pending"
        mock_auth_response.url = "https://example.com/auth"

        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        tool_context = ToolContext()
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.auth_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.auth_tool"
        )

        # Should return error response with authorization URL in content
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert result.result.structuredContent is None
        content_text = result.result.content[0].text
        assert "Authorization required" in content_text
        assert "needs your permission" in content_text
        # The authorization URL is included in the human-readable message
        assert "https://example.com/auth" in content_text
        # Machine-readable fields (authorization_url, llm_instructions) are in content[1]
        assert len(result.result.content) >= 2
        extra_data = json.loads(result.result.content[1].text)
        assert extra_data["authorization_url"] == "https://example.com/auth"
        assert "llm_instructions" in extra_data

    @pytest.mark.asyncio
    async def test_check_tool_requirements_auth_completed(self, mcp_server):
        """Test tool requirements checking when authorization is completed."""

        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        # Create a tool that requires authorization
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            )
        )

        # Mock authorization response as completed
        mock_auth_response = Mock()
        mock_auth_response.status = "completed"
        mock_auth_response.context = Mock()
        mock_auth_response.context.token = "test-token"
        mock_auth_response.context.user_info = {"user_id": "test-user"}

        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        tool_context = ToolContext()
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.auth_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.auth_tool"
        )

        # Should return None (no error) and set authorization context
        assert result is None
        assert tool_context.authorization is not None
        assert tool_context.authorization.token == "test-token"
        assert tool_context.authorization.user_info == {"user_id": "test-user"}

    @pytest.mark.asyncio
    async def test_check_tool_requirements_auth_error(self, mcp_server):
        """Test tool requirements checking when authorization fails."""

        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        # Create a tool that requires authorization
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            )
        )

        # Mock authorization to raise an error
        mcp_server._check_authorization = AsyncMock(side_effect=ToolRuntimeError("Auth failed"))

        tool_context = ToolContext()
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.auth_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.auth_tool"
        )

        # Should return error response
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert result.result.structuredContent is None
        content_text = result.result.content[0].text
        assert "Authorization error" in content_text
        assert "failed to authorize" in content_text
        assert "Auth failed" in content_text

    @pytest.mark.asyncio
    async def test_check_tool_requirements_secrets_missing(self, mcp_server):
        """Test tool requirements checking when required secrets are missing."""

        # Create a tool that requires secrets
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            secrets=[
                ToolSecretRequirement(key="API_KEY"),
                ToolSecretRequirement(key="DATABASE_URL"),
            ]
        )

        # Mock tool context to raise ValueError for missing secrets
        tool_context = Mock(spec=ToolContext)
        tool_context.get_secret = Mock(side_effect=ValueError("Secret not found"))

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.secret_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.secret_tool"
        )

        # Should return error response
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert result.result.structuredContent is None
        content_text = result.result.content[0].text
        assert "Missing secret" in content_text
        assert "API_KEY, DATABASE_URL" in content_text
        assert ".env file" in content_text

    @pytest.mark.asyncio
    async def test_check_tool_requirements_secrets_partial_missing(self, mcp_server):
        """Test tool requirements checking when some required secrets are missing."""

        # Create a tool that requires secrets
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            secrets=[
                ToolSecretRequirement(key="API_KEY"),
                ToolSecretRequirement(key="DATABASE_URL"),
            ]
        )

        # Mock tool context to return a strict subset of the required secrets
        tool_context = Mock(spec=ToolContext)

        def mock_get_secret(key):
            if key == "API_KEY":
                return "test-api-key"
            else:
                raise ValueError("Secret not found")

        tool_context.get_secret = Mock(side_effect=mock_get_secret)

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.secret_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.secret_tool"
        )

        # Should return error response for missing DATABASE_URL
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert result.result.structuredContent is None
        content_text = result.result.content[0].text
        assert "DATABASE_URL" in content_text
        assert "API_KEY" not in content_text

    @pytest.mark.asyncio
    async def test_check_tool_requirements_secrets_available(self, mcp_server):
        """Test tool requirements checking when all required secrets are available."""

        # Create a tool that requires secrets
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            secrets=[
                ToolSecretRequirement(key="API_KEY"),
                ToolSecretRequirement(key="DATABASE_URL"),
            ]
        )

        # Mock tool context to return all secrets
        tool_context = Mock(spec=ToolContext)

        def mock_get_secret(key):
            return f"test-{key.lower()}-value"

        tool_context.get_secret = Mock(side_effect=mock_get_secret)

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.secret_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.secret_tool"
        )

        # Should return None (no error) when all secrets are available
        assert result is None

    @pytest.mark.asyncio
    async def test_check_tool_requirements_combined_auth_and_secrets(self, mcp_server):
        """Test tool requirements checking with both auth and secrets requirements."""

        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        # Create a tool that requires both auth and secrets
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            ),
            secrets=[
                ToolSecretRequirement(key="API_KEY"),
            ],
        )

        # Mock successful authorization
        mock_auth_response = Mock()
        mock_auth_response.status = "completed"
        mock_auth_response.context = Mock()
        mock_auth_response.context.token = "test-token"
        mock_auth_response.context.user_info = {"user_id": "test-user"}

        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        tool_context = ToolContext()
        tool_context.set_secret("API_KEY", "test-api-key")

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.combined_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.combined_tool"
        )

        # Should return None (no error) when both requirements are satisfied
        assert result is None
        # Authorization context should be set
        assert tool_context.authorization is not None

    @pytest.mark.asyncio
    async def test_check_tool_requirements_combined_auth_fails_first(self, mcp_server):
        """Test tool requirements checking when auth fails before secrets are checked."""

        mock_arcade = Mock()
        mcp_server.arcade = mock_arcade

        # Create a tool that requires both auth and secrets
        tool = Mock()
        tool.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
            ),
            secrets=[
                ToolSecretRequirement(key="API_KEY"),
            ],
        )

        # Mock authorization as pending (should fail before secrets check)
        mock_auth_response = Mock()
        mock_auth_response.status = "pending"
        mock_auth_response.url = "https://example.com/auth"

        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        # Create real tool context (secrets check shouldn't be reached)
        tool_context = ToolContext()
        tool_context.set_secret("API_KEY", "test-api-key")

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.combined_tool", "arguments": {}},
        )

        result = await mcp_server._check_tool_requirements(
            tool, tool_context, message, "TestToolkit.combined_tool"
        )

        # Should return auth error (auth is checked first)
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert result.result.structuredContent is None
        content_text = result.result.content[0].text
        # The authorization URL appears in the human-readable message text
        assert "https://example.com/auth" in content_text

    @pytest.mark.asyncio
    async def test_http_transport_blocks_tool_with_auth(
        self, mcp_server, materialized_tool_with_auth
    ):
        """Test that HTTP transport blocks tools requiring oauth."""
        # Create a mock session with HTTP transport
        session = Mock()
        session.init_options = {"transport_type": "http"}

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={
                "name": "TestToolkit.sample_tool_with_auth",
                "arguments": {"text": "test"},
            },
        )
        response = await mcp_server._handle_call_tool(message, session=session)

        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is True
        assert response.result.structuredContent is None
        content_text = response.result.content[0].text
        assert "HTTP transport" in content_text

    @pytest.mark.asyncio
    async def test_http_transport_blocks_tool_with_secrets(self, mcp_server):
        """Test that HTTP transport blocks tools requiring secrets."""
        from arcade_core.schema import ToolSecretRequirement

        tool_def = ToolDefinition(
            name="secret_tool",
            fully_qualified_name="TestToolkit.secret_tool",
            description="A tool requiring secrets",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="text",
                        required=True,
                        description="Input text",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(
                description="Tool output", value_schema=ValueSchema(val_type="string")
            ),
            requirements=ToolRequirements(
                secrets=[ToolSecretRequirement(key="API_KEY", description="API Key")]
            ),
        )

        @tool(requires_secrets=["SECRET_KEY"])
        def secret_tool_func(text: Annotated[str, "Input text"]) -> Annotated[str, "Secret text"]:
            """Secret tool function"""
            return "Secret"

        input_model, output_model = create_func_models(secret_tool_func)
        meta = ToolMeta(module=secret_tool_func.__module__, toolkit="TestToolkit")
        materialized_tool = MaterializedTool(
            tool=secret_tool_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        await mcp_server._tool_manager.add_tool(materialized_tool)

        # Create a mock session with HTTP transport
        session = Mock()
        session.init_options = {"transport_type": "http"}

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.secret_tool", "arguments": {"text": "test"}},
        )

        response = await mcp_server._handle_call_tool(message, session=session)

        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is True
        assert response.result.structuredContent is None
        content_text = response.result.content[0].text
        assert "HTTP transport" in content_text
        assert "secrets" in content_text

    @pytest.mark.asyncio
    async def test_http_transport_blocks_tool_with_both_auth_and_secrets(self, mcp_server):
        """Test that HTTP transport blocks tools requiring both auth and secrets."""
        from arcade_core.schema import ToolSecretRequirement

        # Create a tool with both auth and secret requirements
        tool_def = ToolDefinition(
            name="combined_tool",
            fully_qualified_name="TestToolkit.combined_tool",
            description="A tool requiring both auth and secrets",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="text",
                        required=True,
                        description="Input text",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(
                description="Tool output", value_schema=ValueSchema(val_type="string")
            ),
            requirements=ToolRequirements(
                authorization=ToolAuthRequirement(
                    provider_type="oauth2",
                    provider_id="test-provider",
                    id="test-provider",
                    oauth2=OAuth2Requirement(scopes=["test.scope"]),
                ),
                secrets=[ToolSecretRequirement(key="API_KEY", description="API Key")],
            ),
        )

        @tool(
            requires_auth=OAuth2(id="test-provider", scopes=["test.scope"]),
            requires_secrets=["API_KEY"],
        )
        def combined_tool_func(
            text: Annotated[str, "Input text"],
        ) -> Annotated[str, "Combined text"]:
            """Combined tool function"""
            return f"Combined: {text}"

        input_model, output_model = create_func_models(combined_tool_func)
        meta = ToolMeta(module=combined_tool_func.__module__, toolkit="TestToolkit")
        materialized_tool = MaterializedTool(
            tool=combined_tool_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        await mcp_server._tool_manager.add_tool(materialized_tool)

        # Create a mock session with HTTP transport
        session = Mock()
        session.init_options = {"transport_type": "http"}

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.combined_tool", "arguments": {"text": "test"}},
        )

        response = await mcp_server._handle_call_tool(message, session=session)

        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is True
        assert response.result.structuredContent is None
        content_text = response.result.content[0].text
        assert "Unsupported transport" in content_text
        assert "HTTP transport" in content_text
        assert "authorization" in content_text

    @pytest.mark.asyncio
    async def test_stdio_transport_allows_tool_with_auth(
        self, mcp_server, materialized_tool_with_auth
    ):
        """Test that stdio transport allows tools requiring authentication."""
        # Mock Arcade client
        mcp_server.arcade = Mock()
        mock_auth_response = Mock()
        mock_auth_response.status = "completed"
        mock_auth_response.context = Mock()
        mock_auth_response.context.token = "test-token"
        mock_auth_response.context.user_info = {}
        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        # Create a mock session with stdio transport
        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "test-session"

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={
                "name": "TestToolkit.sample_tool_with_auth",
                "arguments": {"text": "test"},
            },
        )

        response = await mcp_server._handle_call_tool(message, session=session)

        # Should succeed (isn't blocked by transport check)
        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)

        assert response.result.isError is False

    @pytest.mark.asyncio
    async def test_no_transport_type_allows_tool_with_auth(
        self, mcp_server, materialized_tool_with_auth
    ):
        """Test backwards compatibility: no transport_type specified allows tools."""
        # Mock Arcade client
        mcp_server.arcade = Mock()
        mock_auth_response = Mock()
        mock_auth_response.status = "completed"
        mock_auth_response.context = Mock()
        mock_auth_response.context.token = "test-token"
        mock_auth_response.context.user_info = {}
        mcp_server._check_authorization = AsyncMock(return_value=mock_auth_response)

        # Create a mock session without transport_type
        session = Mock()
        session.init_options = {}  # No transport_type
        session.session_id = "test-session"

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={
                "name": "TestToolkit.sample_tool_with_auth",
                "arguments": {"text": "test"},
            },
        )

        response = await mcp_server._handle_call_tool(message, session=session)

        # Should succeed (no transport restriction applies)
        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is False

    @pytest.mark.asyncio
    async def test_http_transport_allows_tool_without_requirements(self, mcp_server):
        """Test that HTTP transport allows tools without auth/secret requirements."""
        # Create a mock session with HTTP transport
        session = Mock()
        session.init_options = {"transport_type": "http"}
        session.session_id = "test-session"

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "test"}},
        )

        response = await mcp_server._handle_call_tool(message, session=session)

        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is False


class TestMissingSecretsWarnings:
    """Test startup warnings for missing tool secrets."""

    @pytest.mark.asyncio
    async def test_warns_missing_secrets_on_startup(self, tool_catalog, mcp_settings, caplog):
        """Test that missing secrets trigger warnings during server startup."""
        import logging

        # Create tool definition with secret requirements
        tool_def = ToolDefinition(
            name="fetch_data",
            fully_qualified_name="TestToolkit.fetch_data",
            description="Fetch data from API.",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="query",
                        required=True,
                        description="Search query",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(description="Result", value_schema=ValueSchema(val_type="string")),
            requirements=ToolRequirements(
                secrets=[
                    ToolSecretRequirement(key="API_KEY", description="API Key"),
                    ToolSecretRequirement(key="SECRET_TOKEN", description="Secret Token"),
                ]
            ),
        )

        @tool
        def fetch_data(query: Annotated[str, "Search query"]) -> Annotated[str, "Result"]:
            """Fetch data from API."""
            return f"Data for {query}"

        # Add tool to catalog

        input_model, output_model = create_func_models(fetch_data)
        meta = ToolMeta(module=fetch_data.__module__, toolkit="TestToolkit")
        materialized = MaterializedTool(
            tool=fetch_data,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        tool_catalog._tools[tool_def.get_fully_qualified_name()] = materialized

        # Clear any existing secrets from environment
        import os

        old_api_key = os.environ.pop("API_KEY", None)
        old_secret_token = os.environ.pop("SECRET_TOKEN", None)

        try:
            # Ensure worker routes are disabled (no ARCADE_WORKER_SECRET)
            mcp_settings.arcade.server_secret = None

            # Create and start server
            with caplog.at_level(logging.WARNING):
                server = MCPServer(
                    catalog=tool_catalog,
                    name="Test Server",
                    version="1.0.0",
                    settings=mcp_settings,
                )
                await server.start()

                # Check for warning message
                warning_messages = [
                    rec.message for rec in caplog.records if rec.levelno == logging.WARNING
                ]

                # Should have a warning about missing secrets
                assert any("fetch_data" in msg and "API_KEY" in msg for msg in warning_messages), (
                    f"Expected warning about missing API_KEY for fetch_data. Got: {warning_messages}"
                )
                assert any(
                    "fetch_data" in msg and "SECRET_TOKEN" in msg for msg in warning_messages
                ), (
                    f"Expected warning about missing SECRET_TOKEN for fetch_data. Got: {warning_messages}"
                )

                await server.stop()
        finally:
            # Restore environment
            if old_api_key is not None:
                os.environ["API_KEY"] = old_api_key
            if old_secret_token is not None:
                os.environ["SECRET_TOKEN"] = old_secret_token

    @pytest.mark.asyncio
    async def test_no_warning_when_secrets_present(self, tool_catalog, mcp_settings, caplog):
        """Test that no warnings are shown when secrets are available."""
        import logging

        # Create tool definition with secret requirements
        tool_def = ToolDefinition(
            name="secure_tool",
            fully_qualified_name="TestToolkit.secure_tool",
            description="Secure tool.",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="data",
                        required=True,
                        description="Data",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(description="Result", value_schema=ValueSchema(val_type="string")),
            requirements=ToolRequirements(
                secrets=[ToolSecretRequirement(key="PRESENT_KEY", description="Present Key")]
            ),
        )

        @tool
        def secure_tool(data: Annotated[str, "Data"]) -> Annotated[str, "Result"]:
            """Secure tool."""
            return f"Processed {data}"

        # Add tool to catalog

        input_model, output_model = create_func_models(secure_tool)
        meta = ToolMeta(module=secure_tool.__module__, toolkit="TestToolkit")
        materialized = MaterializedTool(
            tool=secure_tool,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        tool_catalog._tools[tool_def.get_fully_qualified_name()] = materialized

        # Set the secret in environment
        import os

        old_value = os.environ.get("PRESENT_KEY")
        os.environ["PRESENT_KEY"] = "test-value"

        try:
            # Ensure worker routes are disabled
            mcp_settings.arcade.server_secret = None

            # Create and start server
            with caplog.at_level(logging.WARNING):
                server = MCPServer(
                    catalog=tool_catalog,
                    name="Test Server",
                    version="1.0.0",
                    settings=mcp_settings,
                )
                await server.start()

                # Check that no warning is logged for this tool
                warning_messages = [
                    rec.message for rec in caplog.records if rec.levelno == logging.WARNING
                ]
                assert not any(
                    "secure_tool" in msg and "PRESENT_KEY" in msg for msg in warning_messages
                ), f"Should not warn about PRESENT_KEY when it's set. Got: {warning_messages}"

                await server.stop()
        finally:
            # Restore environment
            if old_value is not None:
                os.environ["PRESENT_KEY"] = old_value
            else:
                os.environ.pop("PRESENT_KEY", None)

    @pytest.mark.asyncio
    async def test_no_warning_when_worker_routes_enabled(self, tool_catalog, mcp_settings, caplog):
        """Test that warnings are skipped when worker routes are enabled."""
        import logging

        # Create tool definition with secret requirements
        tool_def = ToolDefinition(
            name="worker_tool",
            fully_qualified_name="TestToolkit.worker_tool",
            description="Worker tool.",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="param",
                        required=True,
                        description="Param",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(description="Result", value_schema=ValueSchema(val_type="string")),
            requirements=ToolRequirements(
                secrets=[ToolSecretRequirement(key="WORKER_API_KEY", description="Worker API Key")]
            ),
        )

        @tool
        def worker_tool(param: Annotated[str, "Param"]) -> Annotated[str, "Result"]:
            """Worker tool."""
            return f"Result: {param}"

        # Add tool to catalog

        input_model, output_model = create_func_models(worker_tool)
        meta = ToolMeta(module=worker_tool.__module__, toolkit="TestToolkit")
        materialized = MaterializedTool(
            tool=worker_tool,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        tool_catalog._tools[tool_def.get_fully_qualified_name()] = materialized

        # Clear the secret from environment
        import os

        old_value = os.environ.pop("WORKER_API_KEY", None)

        try:
            # Enable worker routes by setting ARCADE_WORKER_SECRET
            mcp_settings.arcade.server_secret = "test-worker-secret"

            # Create and start server
            with caplog.at_level(logging.WARNING):
                server = MCPServer(
                    catalog=tool_catalog,
                    name="Test Server",
                    version="1.0.0",
                    settings=mcp_settings,
                )
                await server.start()

                # Check that no warning is logged (worker routes are enabled)
                warning_messages = [
                    rec.message for rec in caplog.records if rec.levelno == logging.WARNING
                ]
                assert not any(
                    "worker_tool" in msg and "WORKER_API_KEY" in msg for msg in warning_messages
                ), f"Should not warn when worker routes are enabled. Got: {warning_messages}"

                await server.stop()
        finally:
            # Restore environment
            if old_value is not None:
                os.environ["WORKER_API_KEY"] = old_value

    @pytest.mark.asyncio
    async def test_warning_format(self, tool_catalog, mcp_settings, caplog):
        """Test that warnings use the expected format."""
        import logging

        # Create tool definition with secret requirement
        tool_def = ToolDefinition(
            name="format_test_tool",
            fully_qualified_name="TestToolkit.format_test_tool",
            description="Format test tool.",
            toolkit=ToolkitDefinition(
                name="TestToolkit", description="Test toolkit", version="1.0.0"
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="x",
                        required=True,
                        description="Input",
                        value_schema=ValueSchema(val_type="integer"),
                    )
                ]
            ),
            output=ToolOutput(description="Output", value_schema=ValueSchema(val_type="integer")),
            requirements=ToolRequirements(
                secrets=[
                    ToolSecretRequirement(key="FORMAT_TEST_KEY", description="Format Test Key")
                ]
            ),
        )

        @tool
        def format_test_tool(x: Annotated[int, "Input"]) -> Annotated[int, "Output"]:
            """Format test tool."""
            return x * 2

        # Add tool to catalog
        input_model, output_model = create_func_models(format_test_tool)
        meta = ToolMeta(module=format_test_tool.__module__, toolkit="TestToolkit")
        materialized = MaterializedTool(
            tool=format_test_tool,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        tool_catalog._tools[tool_def.get_fully_qualified_name()] = materialized

        # Clear the secret from environment
        import os

        old_value = os.environ.pop("FORMAT_TEST_KEY", None)

        try:
            # Ensure worker routes are disabled
            mcp_settings.arcade.server_secret = None

            # Create and start server
            with caplog.at_level(logging.WARNING):
                server = MCPServer(
                    catalog=tool_catalog,
                    name="Test Server",
                    version="1.0.0",
                    settings=mcp_settings,
                )
                await server.start()

                # Check warning format matches specification
                warning_messages = [
                    rec.message for rec in caplog.records if rec.levelno == logging.WARNING
                ]

                # Find the warning for our tool
                matching_warnings = [msg for msg in warning_messages if "format_test_tool" in msg]
                assert len(matching_warnings) > 0, (
                    f"Expected warning for format_test_tool. Got: {warning_messages}"
                )

                warning = matching_warnings[0]
                # Check format: "⚠ Tool 'name' declares secret(s) 'KEY' which are not set"
                assert "Tool 'format_test_tool'" in warning
                assert "not set" in warning

                await server.stop()
        finally:
            # Restore environment
            if old_value is not None:
                os.environ["FORMAT_TEST_KEY"] = old_value


class TestServerToolMetaExtensions:
    """Tests for _meta extensions on tools (e.g., MCP Apps ui.resourceUri)."""

    @pytest.mark.asyncio
    async def test_tool_meta_extensions_applied(self, tool_catalog, mcp_settings):
        """tool_meta_extensions adds _meta.ui.resourceUri to tools."""
        # Get the FQN of the first tool in the catalog
        first_tool = next(iter(tool_catalog))
        fqn = first_tool.definition.fully_qualified_name

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            tool_meta_extensions={fqn: {"ui": {"resourceUri": "ui://test/index.html"}}},
        )
        await server.start()
        try:
            tools = await server.tools.list_tools()
            # Find the tool by its sanitized name
            sanitized = fqn.replace(".", "_")
            matched = [t for t in tools if t.name == sanitized]
            assert len(matched) == 1
            assert matched[0].meta is not None
            assert matched[0].meta["ui"]["resourceUri"] == "ui://test/index.html"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_no_tool_meta_extensions_by_default(self, tool_catalog, mcp_settings):
        """Without extensions, tools that have no arcade meta have _meta=None or no ui key."""
        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
        )
        await server.start()
        try:
            tools = await server.tools.list_tools()
            for t in tools:
                if t.meta:
                    assert "ui" not in t.meta
        finally:
            await server.stop()


class TestServerInitialResources:
    """Tests for loading build-time resources into MCPServer."""

    @pytest.mark.asyncio
    async def test_server_loads_initial_resources(self, tool_catalog, mcp_settings):
        """MCPServer with initial_resources makes them available via list/read."""
        from arcade_mcp_server.types import Resource

        resource = Resource(uri="ui://app/index.html", name="App UI", mimeType="text/html")

        def handler(uri: str) -> str:
            return "<html>hello</html>"

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            initial_resources=[(resource, handler)],
        )
        await server.start()
        try:
            resources = await server.resources.list_resources()
            uris = [r.uri for r in resources]
            assert "ui://app/index.html" in uris

            contents = await server.resources.read_resource("ui://app/index.html")
            assert len(contents) == 1
            assert contents[0].text == "<html>hello</html>"  # type: ignore[attr-defined]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_no_initial_resources_by_default(self, tool_catalog, mcp_settings):
        """Backward compat: no initial resources by default."""
        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
        )
        await server.start()
        try:
            resources = await server.resources.list_resources()
            assert resources == []
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_initial_resources_with_async_handler(self, tool_catalog, mcp_settings):
        """Async handlers work for initial resources."""
        from arcade_mcp_server.types import Resource

        resource = Resource(uri="ui://app/data.json", name="Data", mimeType="application/json")

        async def async_handler(uri: str) -> str:
            return '{"key": "value"}'

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            initial_resources=[(resource, async_handler)],
        )
        await server.start()
        try:
            contents = await server.resources.read_resource("ui://app/data.json")
            assert len(contents) == 1
            assert contents[0].text == '{"key": "value"}'  # type: ignore[attr-defined]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_handle_read_resource_round_trip(self, tool_catalog, mcp_settings):
        """Integration: _handle_read_resource returns correct JSONRPCResponse."""
        from arcade_mcp_server.types import (
            ReadResourceParams,
            ReadResourceRequest,
            ReadResourceResult,
            Resource,
            TextResourceContents,
        )

        resource = Resource(uri="ui://app/page.html", name="Page", mimeType="text/html")

        def handler(uri: str) -> str:
            return "<html><body>Hello</body></html>"

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            initial_resources=[(resource, handler)],
        )
        await server.start()
        try:
            request = ReadResourceRequest(
                id=1,
                params=ReadResourceParams(uri="ui://app/page.html"),
            )
            response = await server._handle_read_resource(request)

            assert not hasattr(response, "error"), f"Expected success, got error: {response}"
            result = response.result
            assert isinstance(result, ReadResourceResult)
            assert len(result.contents) == 1
            content = result.contents[0]
            assert isinstance(content, TextResourceContents)
            assert content.text == "<html><body>Hello</body></html>"
            assert content.mimeType == "text/html"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_loads_initial_template_resources(self, tool_catalog, mcp_settings):
        """MCPServer with initial ResourceTemplate registers it as a template."""
        from arcade_mcp_server.types import ResourceTemplate

        tmpl = ResourceTemplate(uriTemplate="data://{item_id}", name="Data", mimeType="text/plain")

        def handler(uri: str, item_id: str) -> str:
            return f"item-{item_id}"

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            initial_resources=[(tmpl, handler)],
        )
        await server.start()
        try:
            templates = await server.resources.list_resource_templates()
            assert any(t.uriTemplate == "data://{item_id}" for t in templates)

            contents = await server.resources.read_resource("data://42")
            assert contents[0].text == "item-42"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_loads_template_without_handler(self, tool_catalog, mcp_settings):
        """MCPServer with ResourceTemplate and no handler registers template only."""
        from arcade_mcp_server.types import ResourceTemplate

        tmpl = ResourceTemplate(uriTemplate="schema://{type}", name="Schema")

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            initial_resources=[(tmpl, None)],
        )
        await server.start()
        try:
            templates = await server.resources.list_resource_templates()
            assert any(t.uriTemplate == "schema://{type}" for t in templates)
        finally:
            await server.stop()


class TestVersionNegotiationInInitialize:
    """Test version negotiation during initialize handshake."""

    @pytest.mark.asyncio
    async def test_initialize_with_2025_06_18_returns_2025_06_18(self, mcp_server, server_session):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        assert isinstance(response.result, InitializeResult)
        assert response.result.protocolVersion == "2025-06-18"

    @pytest.mark.asyncio
    async def test_initialize_with_2025_11_25_returns_2025_11_25(self, mcp_server, server_session):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        assert isinstance(response.result, InitializeResult)
        assert response.result.protocolVersion == "2025-11-25"

    @pytest.mark.asyncio
    async def test_initialize_with_unsupported_returns_latest(self, mcp_server, server_session):
        """Unsupported version -> server returns latest (2025-11-25)."""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2030-01-01",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        assert isinstance(response.result, InitializeResult)
        assert response.result.protocolVersion == "2025-11-25"

    @pytest.mark.asyncio
    async def test_initialize_2025_06_18_has_no_tasks_capability(self, mcp_server, server_session):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        result_dict = response.result.capabilities.model_dump(exclude_none=True)
        assert "tasks" not in result_dict

    @pytest.mark.asyncio
    async def test_initialize_2025_11_25_has_tasks_capability_with_nested_structure(
        self, mcp_server, server_session
    ):
        """2025-11-25 tasks capability includes nested requests structure.
        tasks.list is included for ALL session types (auth and non-auth)."""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        # ServerCapabilities uses extra="allow", so tasks will be accessible via model_dump
        caps_dict = response.result.capabilities.model_dump(exclude_none=True)
        assert "tasks" in caps_dict
        tasks_cap = caps_dict["tasks"]
        assert "list" in tasks_cap
        assert "cancel" in tasks_cap
        assert "requests" in tasks_cap
        assert "tools" in tasks_cap["requests"]
        assert "call" in tasks_cap["requests"]["tools"]

    @pytest.mark.asyncio
    async def test_session_stores_negotiated_version(self, mcp_server, server_session):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        await mcp_server.handle_message(message, session=server_session)
        assert server_session.negotiated_version == "2025-11-25"

    @pytest.mark.asyncio
    async def test_initialize_2025_06_18_server_info_no_2025_11_25_fields(
        self, mcp_server, server_session
    ):
        """2025-06-18 already supports title (present in 2025-06-18 schema), but
        icons/description/websiteUrl are 2025-11-25-only and must not appear."""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        }
        response = await mcp_server.handle_message(message, session=server_session)
        result_dict = response.result.model_dump(exclude_none=True)
        server_info = result_dict.get("serverInfo", {})
        # title IS allowed for 2025-06-18 (already in 2025-06-18 schema)
        assert "icons" not in server_info
        assert "description" not in server_info
        assert "websiteUrl" not in server_info

    def test_build_server_info_gates_branding_on_implementation_metadata_not_tasks(
        self, tool_catalog, mcp_settings
    ):
        """Regression: branding fields (icons, description, websiteUrl) must be
        gated on the dedicated ``implementation_metadata`` feature, not on the
        unrelated ``tasks`` feature. If a future protocol version ships the
        Tasks primitive without implementation_metadata (or vice versa), the
        old ``tasks``-gated code would silently produce the wrong output.
        """
        from arcade_mcp_server.types import VERSION_FEATURES

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            name="test-server",
            version="1.0.0",
            icons=[{"src": "https://example.com/icon.png", "mimeType": "image/png"}],
            description="Server description",
            website_url="https://example.com",
        )

        info = server._build_server_info("2025-11-25")
        assert info["icons"] == [{"src": "https://example.com/icon.png", "mimeType": "image/png"}]
        assert info["description"] == "Server description"
        assert info["websiteUrl"] == "https://example.com"

        # Legacy version -- implementation_metadata absent -> branding stripped.
        info_legacy = server._build_server_info("2025-06-18")
        assert "icons" not in info_legacy
        assert "description" not in info_legacy
        assert "websiteUrl" not in info_legacy

        # Confirm the registry shape the production code relies on: these
        # two features happen to co-occur today, but are independent features.
        assert "implementation_metadata" in VERSION_FEATURES["2025-11-25"]
        assert "tasks" in VERSION_FEATURES["2025-11-25"]
        assert "implementation_metadata" not in VERSION_FEATURES["2025-06-18"]


class TestToolMetaExtensionEdgeCases:
    """Test apply_meta_extensions edge cases on ToolManager directly."""

    @pytest.mark.asyncio
    async def test_missing_fqn_logs_warning(self, tool_catalog, mcp_settings, caplog):
        """Extensions referencing non-existent tools log a warning and skip."""
        import logging

        server = MCPServer(
            catalog=tool_catalog,
            settings=mcp_settings,
            tool_meta_extensions={"NonExistent.Tool": {"ui": {"resourceUri": "ui://x"}}},
        )
        with caplog.at_level(logging.WARNING, logger="arcade.mcp.managers.tool"):
            await server.start()
        try:
            assert "skipped: tool not found" in caplog.text
        finally:
            await server.stop()


class TestSubCapabilityGatedDispatch:
    """Tests that sub-capability-gated methods are rejected when specific sub-capability not negotiated.

    Parties MUST only use capabilities that were successfully negotiated.
    Tasks sub-capabilities: tasks.list, tasks.cancel, tasks.requests.tools.call."""

    # Full tasks capability structure for tests
    FULL_TASKS_CAP = {"tasks": {"list": {}, "cancel": {}, "requests": {"tools": {"call": {}}}}}
    # Tasks without list
    TASKS_NO_LIST = {"tasks": {"cancel": {}, "requests": {"tools": {"call": {}}}}}
    # Tasks without cancel
    TASKS_NO_CANCEL = {"tasks": {"list": {}, "requests": {"tools": {"call": {}}}}}

    @pytest.mark.asyncio
    async def test_tasks_get_rejected_without_tasks_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/get must return method-not-found when base tasks capability not declared."""
        initialized_server_session.negotiated_version = "2025-06-18"
        # 2025-06-18 sessions have no tasks capability
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601  # METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_tasks_list_rejected_without_tasks_list_sub_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/list requires tasks.list sub-capability, not just base tasks."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.TASKS_NO_LIST
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_list_accepted_with_tasks_list_sub_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/list works when tasks.list sub-capability is declared."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.FULL_TASKS_CAP
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        if isinstance(response, JSONRPCError):
            assert response.error["code"] != -32601  # NOT method-not-found

    @pytest.mark.asyncio
    async def test_tasks_cancel_rejected_without_tasks_cancel_sub_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/cancel requires tasks.cancel sub-capability."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.TASKS_NO_CANCEL
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/cancel", "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_result_rejected_without_tasks_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/result requires base tasks capability."""
        initialized_server_session.negotiated_version = "2025-06-18"
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result", "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_get_accepted_with_base_tasks_capability(
        self, mcp_server, initialized_server_session
    ):
        """tasks/get only requires base tasks capability (always present when tasks declared).
        (May return 'task not found' error, but not -32601.)"""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = (
            self.TASKS_NO_LIST
        )  # no list, but base tasks exists
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": "nonexistent"},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        if isinstance(response, JSONRPCError):
            assert response.error["code"] != -32601  # NOT method-not-found

    @pytest.mark.asyncio
    async def test_2025_11_25_session_without_tasks_capability_rejects_all_tasks(
        self, mcp_server, initialized_server_session
    ):
        """Dispatch gating works even with manually cleared capabilities."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = {}  # no tasks at all
        for method in ["tasks/get", "tasks/result", "tasks/list", "tasks/cancel"]:
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {"taskId": "t1"} if method != "tasks/list" else {},
            }
            response = await mcp_server.handle_message(message, initialized_server_session)
            assert isinstance(response, JSONRPCError), f"{method} should be rejected"
            assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_existing_methods_work_for_both_versions(
        self, mcp_server, initialized_server_session
    ):
        """tools/list, ping, etc. work regardless of version."""
        for version in ["2025-06-18", "2025-11-25"]:
            initialized_server_session.negotiated_version = version
            message = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
            response = await mcp_server.handle_message(message, initialized_server_session)
            assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_capability_gated_methods_rejected_when_no_negotiated_version(
        self, mcp_server, initialized_server_session
    ):
        """If session has no negotiated_version (shouldn't happen, but defensive), reject gated methods."""
        initialized_server_session.negotiated_version = None
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601


def _enable_tasks(session):
    """Set up a session with 2025-11-25 and full tasks capability."""
    session.negotiated_version = "2025-11-25"
    session._negotiated_capabilities = {
        "tools": {"listChanged": True},
        "logging": {},
        "prompts": {"listChanged": True},
        "resources": {"subscribe": True, "listChanged": True},
        "tasks": {
            "list": {},
            "cancel": {},
            "requests": {"tools": {"call": {}}},
        },
    }


class TestTaskContextKey:
    """Tests for _get_task_context_key."""

    @pytest.mark.asyncio
    async def test_session_fallback_when_no_resource_owner(
        self, mcp_server, initialized_server_session
    ):
        key = mcp_server._get_task_context_key(initialized_server_session, None)
        assert key == f"session:{initialized_server_session.session_id}"

    @pytest.mark.asyncio
    async def test_auth_context_with_full_claims(self, mcp_server, initialized_server_session):
        owner = ResourceOwner(
            user_id="alice",
            client_id="my-app",
            claims={"iss": "https://accounts.google.com", "sub": "alice", "azp": "my-app"},
        )
        key = mcp_server._get_task_context_key(initialized_server_session, owner)
        assert key.startswith("auth:")
        assert "alice" in key

    @pytest.mark.asyncio
    async def test_percent_encoding_of_issuer(self, mcp_server, initialized_server_session):
        owner = ResourceOwner(
            user_id="alice",
            client_id="app1",
            claims={"iss": "https://accounts.google.com", "sub": "alice"},
        )
        key = mcp_server._get_task_context_key(initialized_server_session, owner)
        # The issuer URL should be percent-encoded (colons encoded)
        assert "https" not in key.split(":")[1:]  # raw "https" not appearing as a split component

    @pytest.mark.asyncio
    async def test_missing_iss_raises(self, mcp_server, initialized_server_session):
        owner = ResourceOwner(
            user_id="alice",
            client_id="app1",
            claims={"client_id": "app1"},  # no iss
        )
        with pytest.raises(IncompleteAuthContextError):
            mcp_server._get_task_context_key(initialized_server_session, owner)

    @pytest.mark.asyncio
    async def test_unknown_client_id_produces_key(self, mcp_server, initialized_server_session):
        owner = ResourceOwner(
            user_id="alice",
            client_id="unknown",
            claims={"iss": "https://accounts.google.com", "sub": "alice"},
        )
        key = mcp_server._get_task_context_key(initialized_server_session, owner)
        assert key.startswith("auth:")
        assert "unknown" in key

    @pytest.mark.asyncio
    async def test_unknown_client_id_logs_warning(
        self, mcp_server, initialized_server_session, caplog
    ):
        owner = ResourceOwner(
            user_id="alice",
            client_id="unknown",
            claims={"iss": "https://accounts.google.com", "sub": "alice"},
        )
        mcp_server._get_task_context_key(initialized_server_session, owner)
        assert any("lacks azp/client_id claims" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_colons_in_claims_are_encoded(self, mcp_server, initialized_server_session):
        owner = ResourceOwner(
            user_id="alice",
            client_id="client:with:colons",
            claims={"iss": "https://accounts.google.com", "azp": "client:with:colons"},
        )
        key = mcp_server._get_task_context_key(initialized_server_session, owner)
        assert key.startswith("auth:")
        # Raw "https" shouldn't appear as its own split component
        parts = key.split(":")
        assert "https" not in parts


class TestTaskHandlers:
    """Task handler tests."""

    @pytest.mark.asyncio
    async def test_handle_get_task_returns_flat_result(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.taskId == task.taskId

    @pytest.mark.asyncio
    async def test_handle_get_task_returns_immediately(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": task.taskId},
        }
        response = await asyncio.wait_for(
            mcp_server.handle_message(message, initialized_server_session), timeout=1.0
        )
        assert response.result.status == TaskStatus.WORKING

    @pytest.mark.asyncio
    async def test_handle_get_task_not_found(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": "nonexistent"},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_handle_get_task_cross_context_isolation(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        task = await mcp_server._task_manager.create_task(
            context_key="auth:https://other-issuer.com:other-client:other-user"
        )
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_handle_list_tasks(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert len(response.result.tasks) >= 1

    @pytest.mark.asyncio
    async def test_handle_list_tasks_returns_next_cursor_when_more_available(
        self, mcp_server, initialized_server_session
    ):
        """tasks/list MUST set nextCursor when more tasks remain beyond the page."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        for _ in range(25):
            await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        # Default page size is 20 -- 25 > 20 so nextCursor must be set.
        assert len(response.result.tasks) == 20
        assert response.result.nextCursor is not None

    @pytest.mark.asyncio
    async def test_handle_list_tasks_next_page_does_not_overlap(
        self, mcp_server, initialized_server_session
    ):
        """Passing the issued nextCursor back returns a disjoint next page."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        for _ in range(25):
            await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        msg1 = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        resp1 = await mcp_server.handle_message(msg1, initialized_server_session)
        assert resp1.result.nextCursor is not None
        msg2 = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tasks/list",
            "params": {"cursor": resp1.result.nextCursor},
        }
        resp2 = await mcp_server.handle_message(msg2, initialized_server_session)
        assert not isinstance(resp2, JSONRPCError)
        page1_ids = {t.taskId for t in resp1.result.tasks}
        page2_ids = {t.taskId for t in resp2.result.tasks}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_handle_list_tasks_invalid_cursor_returns_minus_32602(
        self, mcp_server, initialized_server_session
    ):
        """Invalid / unresolvable cursor -> JSON-RPC -32602."""
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/list",
            "params": {"cursor": "not-a-valid-cursor!!"},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_handle_list_tasks_ordering_is_newest_first(
        self, mcp_server, initialized_server_session
    ):
        """Tasks are returned newest-first (createdAt descending)."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        created = []
        for _ in range(5):
            t = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
            created.append(t)
            await asyncio.sleep(0.01)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        resp = await mcp_server.handle_message(message, initialized_server_session)
        returned_ids = [t.taskId for t in resp.result.tasks]
        # Reverse of creation order.
        assert returned_ids == [t.taskId for t in reversed(created)]

    @pytest.mark.asyncio
    async def test_notify_task_status_change_sends_full_task_params(
        self, mcp_server, initialized_server_session
    ):
        """notifications/tasks/status params MUST be the FULL Task object
        (allOf: NotificationParams & Task) -- taskId, status, createdAt,
        lastUpdatedAt, ttl, ..."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id

        sent_messages: list[str] = []

        async def fake_send(msg: str) -> None:
            sent_messages.append(msg)

        initialized_server_session.write_stream = type("W", (), {"send": staticmethod(fake_send)})()

        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}", ttl=60_000)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)
        await mcp_server._notify_task_status_change(task.taskId, initialized_server_session)

        assert len(sent_messages) == 1
        payload = json.loads(sent_messages[0])
        assert payload["method"] == "notifications/tasks/status"
        params = payload["params"]
        assert params["taskId"] == task.taskId
        assert params["status"] == TaskStatus.COMPLETED.value
        # Per plan 3479: full Task fields must be present.
        assert "createdAt" in params
        assert "lastUpdatedAt" in params
        assert "ttl" in params
        assert params["ttl"] == 60_000

    @pytest.mark.asyncio
    async def test_handle_cancel_task_returns_flat_result(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/cancel",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_handle_tasks_result_blocks_until_complete(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "answer"}], "isError": False}

        async def complete_later():
            await asyncio.sleep(0.1)
            await mcp_server._task_manager.set_result(task.taskId, result_data)
            await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/result",
            "params": {"taskId": task.taskId},
        }

        # NOTE: asyncio.TaskGroup is 3.11+; use plain create_task for 3.10 compat.
        completer = asyncio.create_task(complete_later())
        try:
            response = await asyncio.wait_for(
                mcp_server.handle_message(message, initialized_server_session), timeout=5.0
            )
        finally:
            await completer
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_handle_tasks_result_returns_immediately_for_completed(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "done"}]}
        await mcp_server._task_manager.set_result(task.taskId, result_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/result",
            "params": {"taskId": task.taskId},
        }
        response = await asyncio.wait_for(
            mcp_server.handle_message(message, initialized_server_session), timeout=1.0
        )
        assert not isinstance(response, JSONRPCError)


class TestTaskAugmentedToolCall:
    """Tests for task-augmented tools/call."""

    @pytest.mark.asyncio
    async def test_tool_call_with_task_returns_create_task_result(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.test_tool",
                "arguments": {"text": "hello"},
                "_meta": {},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "task")
        assert response.result.task.status == TaskStatus.WORKING
        assert response.result.task.taskId is not None

    @pytest.mark.asyncio
    async def test_tool_call_without_task_returns_normal_result(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "content")
        assert not hasattr(response.result, "task")

    @pytest.mark.asyncio
    async def test_task_augmented_tool_completes_in_background(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.test_tool",
                "arguments": {"text": "hello"},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = response.result.task.taskId

        result = await asyncio.wait_for(
            mcp_server._task_manager.get_result(task_id, context_key=f"session:{sid}"), timeout=5.0
        )
        task = await mcp_server._task_manager.get_task(task_id, context_key=f"session:{sid}")
        assert task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]

    @pytest.mark.asyncio
    async def test_task_augmented_tool_error_captured(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.failing_tool", "arguments": {}, "task": {"ttl": 60000}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = response.result.task.taskId
        await asyncio.wait_for(
            mcp_server._task_manager.get_result(task_id, context_key=f"session:{sid}"), timeout=5.0
        )
        task = await mcp_server._task_manager.get_task(task_id, context_key=f"session:{sid}")
        assert task.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancel_running_task_cancels_tool_execution(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.slow_tool", "arguments": {}, "task": {"ttl": 60000}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = response.result.task.taskId

        # Cancel while running
        cancel_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tasks/cancel",
            "params": {"taskId": task_id},
        }
        await mcp_server.handle_message(cancel_msg, initialized_server_session)
        task = await mcp_server._task_manager.get_task(task_id, context_key=f"session:{sid}")
        assert task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_task_augmented_call_runs_check_tool_requirements(
        self, mcp_server, initialized_server_session
    ):
        """Regression: task-augmented calls must invoke _check_tool_requirements
        BEFORE creating a task so OAuth tokens are fetched against the caller
        and missing requirements surface as immediate errors (not as tasks
        that silently fail at execution time with an unpopulated auth context).
        """
        _enable_tasks(initialized_server_session)

        check_tool_requirements_calls: list[str] = []
        original = mcp_server._check_tool_requirements

        async def _tracking_check(tool, tool_context, message, tool_name, session=None):
            check_tool_requirements_calls.append(tool_name)
            return await original(tool, tool_context, message, tool_name, session)

        mcp_server._check_tool_requirements = _tracking_check  # type: ignore[method-assign]

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.scoped_task_tool",
                "arguments": {"text": "hello"},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)

        # With no Arcade API key configured, _check_tool_requirements should
        # return a synchronous error response -- NOT create a background task.
        assert not isinstance(response, JSONRPCError), (
            "Handler returned a protocol-level error; expected an early tool-error response"
        )
        # Must be a CallToolResult with isError=True, not a CreateTaskResult.
        assert hasattr(response.result, "isError")
        assert getattr(response.result, "isError", False) is True
        assert not hasattr(response.result, "task"), (
            "Task must not be created when _check_tool_requirements fails"
        )
        assert check_tool_requirements_calls == ["TestToolkit.scoped_task_tool"], (
            "Expected _check_tool_requirements to be invoked once for the task-augmented call"
        )
        # No task entry should have been created.
        assert len(mcp_server._task_manager._tasks) == 0

    @pytest.mark.asyncio
    async def test_background_task_survives_ttl_eviction_on_completion(
        self, mcp_server, initialized_server_session
    ):
        """Regression: if the task is evicted (TTL cleanup) between
        ``set_result`` and ``update_status`` in the background path, the
        resulting ``NotFoundError`` from ``update_status`` must be suppressed.
        Previously only ``InvalidTaskStateError`` was suppressed, so the
        background ``asyncio.Task`` would crash with an unhandled exception.
        """
        from arcade_mcp_server.managers.task_manager import NotFoundError

        _enable_tasks(initialized_server_session)
        original_update_status = mcp_server._task_manager.update_status
        call_count = {"n": 0}

        async def _update_status_raises_notfound(task_id, status, message=None):
            call_count["n"] += 1
            # Simulate TTL eviction before the status transition lands.
            raise NotFoundError(f"Task not found (evicted): {task_id}")

        mcp_server._task_manager.update_status = _update_status_raises_notfound  # type: ignore[method-assign]
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "TestToolkit.test_tool",
                    "arguments": {"text": "hello"},
                    "task": {"ttl": 60000},
                },
            }
            create_response = await mcp_server.handle_message(message, initialized_server_session)
            task_id = create_response.result.task.taskId

            # The background task should finish cleanly; any leaked
            # NotFoundError would surface here as a crashed asyncio.Task.
            bg = mcp_server._task_manager._bg_tasks.get(task_id)
            assert bg is not None
            await asyncio.wait_for(bg, timeout=5.0)
            # No exception from the background task.
            assert bg.exception() is None
            assert call_count["n"] >= 1
        finally:
            mcp_server._task_manager.update_status = original_update_status  # type: ignore[method-assign]

    @pytest.mark.asyncio
    async def test_background_task_error_preserves_additional_prompt_content(
        self, mcp_server, initialized_server_session
    ):
        """Regression: the background-task error path must preserve
        ``error.additional_prompt_content`` (retry guidance emitted by typed
        errors like ``RetryableToolError``). Previously the path used
        ``str(error)`` and dropped the field, degrading error context for
        long-running tools served under tasks.
        """
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.retryable_failing_tool",
                "arguments": {},
                "task": {"ttl": 60000},
            },
        }
        create_response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = create_response.result.task.taskId

        stored = await asyncio.wait_for(
            mcp_server._task_manager.get_result(task_id, context_key=f"session:{sid}"),
            timeout=5.0,
        )
        assert getattr(stored, "isError", None) is True
        content_texts = [getattr(c, "text", "") for c in getattr(stored, "content", []) or []]
        joined = "\n".join(content_texts)
        assert "Upstream was rate limited" in joined, "message should be in the error content"
        assert "Wait 60s and try again with a narrower query." in joined, (
            "additional_prompt_content must be preserved in the task-augmented error"
        )

    @pytest.mark.asyncio
    async def test_background_task_error_result_has_no_structured_content(
        self, mcp_server, initialized_server_session
    ):
        """Regression: CallToolResult persisted by the background-execution
        path must have ``structuredContent=None`` on error, matching the
        synchronous path. The MCP spec requires structuredContent to validate
        against outputSchema; an error payload will not, so serving a non-None
        structuredContent on error is a spec violation.
        """
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.failing_tool",
                "arguments": {},
                "task": {"ttl": 60000},
            },
        }
        create_response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = create_response.result.task.taskId

        # Block until background execution completes and stores a result.
        stored = await asyncio.wait_for(
            mcp_server._task_manager.get_result(task_id, context_key=f"session:{sid}"),
            timeout=5.0,
        )

        assert getattr(stored, "isError", None) is True, "failing_tool should produce isError=True"
        assert getattr(stored, "structuredContent", "sentinel") is None, (
            "structuredContent MUST be None on error CallToolResult (spec requirement)"
        )


class TestTaskHandlersSessionRequired:
    """Regression tests for task handlers requiring a non-None session.

    Previously these handlers fell back to a ``"session:unknown"`` context
    key when called with ``session=None``, which silently returned
    ``"Task not found"`` for every call -- indistinguishable from a real
    miss. They now return an explicit error.
    """

    @pytest.mark.asyncio
    async def test_get_task_without_session_returns_error(self, mcp_server):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": "task_abc"},
        }
        response = await mcp_server._handle_get_task(message, session=None)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603
        assert "session" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_list_tasks_without_session_returns_error(self, mcp_server):
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server._handle_list_tasks(message, session=None)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603
        assert "session" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_task_without_session_returns_error(self, mcp_server):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/cancel",
            "params": {"taskId": "task_abc"},
        }
        response = await mcp_server._handle_cancel_task(message, session=None)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603
        assert "session" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_get_task_result_without_session_returns_error(self, mcp_server):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/result",
            "params": {"taskId": "task_abc"},
        }
        response = await mcp_server._handle_get_task_result(message, session=None)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603
        assert "session" in response.error["message"].lower()


class TestRelatedTaskMetadata:
    """Tests for _meta.io.modelcontextprotocol/related-task propagation."""

    @pytest.mark.asyncio
    async def test_create_task_result_includes_related_task_meta(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.test_tool",
                "arguments": {"text": "hello"},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = response.result.model_dump(exclude_none=True, by_alias=True)
        meta = result_dict.get("_meta", {})
        related = meta.get("io.modelcontextprotocol/related-task", {})
        assert "taskId" in related
        assert related["taskId"] == response.result.task.taskId

    @pytest.mark.asyncio
    async def test_tasks_result_success_response_includes_related_task_meta(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "done"}]}
        await mcp_server._task_manager.set_result(task.taskId, result_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/result",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        # The result should be a dict with _meta injected
        result = response.result
        if isinstance(result, dict):
            meta = result.get("_meta", {})
            related = meta.get("io.modelcontextprotocol/related-task", {})
            assert related.get("taskId") == task.taskId
        else:
            # Pydantic model
            result_dict = (
                result.model_dump(exclude_none=True, by_alias=True)
                if hasattr(result, "model_dump")
                else {}
            )
            meta = result_dict.get("_meta", {})
            related = meta.get("io.modelcontextprotocol/related-task", {})
            assert related.get("taskId") == task.taskId

    @pytest.mark.asyncio
    async def test_tasks_result_error_response_returns_underlying_error_unchanged(
        self, mcp_server, initialized_server_session
    ):
        """tasks/result for a FAILED task returns the underlying JSON-RPC error unchanged."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        error_data = {"code": -32603, "message": "Internal error"}
        await mcp_server._task_manager.set_error(task.taskId, error_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.FAILED)

        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/result",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603

    @pytest.mark.asyncio
    async def test_tasks_get_response_should_not_include_related_task_meta(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/get",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = (
            response.result.model_dump(exclude_none=True, by_alias=True)
            if hasattr(response.result, "model_dump")
            else {}
        )
        meta = result_dict.get("_meta", {})
        assert "io.modelcontextprotocol/related-task" not in meta

    @pytest.mark.asyncio
    async def test_tasks_cancel_response_should_not_include_related_task_meta(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/cancel",
            "params": {"taskId": task.taskId},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = (
            response.result.model_dump(exclude_none=True, by_alias=True)
            if hasattr(response.result, "model_dump")
            else {}
        )
        meta = result_dict.get("_meta", {})
        assert "io.modelcontextprotocol/related-task" not in meta


class TestToolTaskNegotiationEnforcement:
    """Tests for ToolExecution.taskSupport enforcement rules."""

    @pytest.mark.asyncio
    async def test_forbidden_tool_rejects_task_metadata(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.forbidden_task_tool",
                "arguments": {},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_required_tool_rejects_non_task_call(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.required_task_tool", "arguments": {}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_optional_tool_accepts_task_metadata(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.test_tool",
                "arguments": {"text": "hello"},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_optional_tool_accepts_normal_call(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_default_no_execution_rejects_task_metadata(
        self, mcp_server, initialized_server_session
    ):
        _enable_tasks(initialized_server_session)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.no_execution_tool",
                "arguments": {},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601


class TestCapabilityFallback:
    """Tests for capability fallback: task metadata ignored when not negotiated."""

    @pytest.mark.asyncio
    async def test_2025_06_18_session_ignores_task_metadata(
        self, mcp_server, initialized_server_session
    ):
        initialized_server_session.negotiated_version = "2025-06-18"
        initialized_server_session._negotiated_capabilities = {
            "tools": {"listChanged": True},
            "logging": {},
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
        }
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "TestToolkit.test_tool",
                "arguments": {"text": "hello"},
                "task": {"ttl": 60000},
            },
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "content")  # CallToolResult shape
        assert not hasattr(response.result, "task")  # NOT CreateTaskResult

    @pytest.mark.asyncio
    async def test_required_policy_enforced_for_legacy_clients(
        self, mcp_server, initialized_server_session
    ):
        """Regression: a tool with taskSupport="required" must reject synchronous
        calls from ALL clients, including legacy 2025-06-18 sessions that cannot
        negotiate task support. Previously the policy check was gated behind
        ``server_declared_task_tools``, so legacy clients could invoke a
        "required" tool synchronously and silently bypass the contract.
        """
        initialized_server_session.negotiated_version = "2025-06-18"
        initialized_server_session._negotiated_capabilities = {
            "tools": {"listChanged": True},
            "logging": {},
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
        }
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.required_task_tool", "arguments": {}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601
        assert "required" in response.error["message"].lower()


class TestURLElicitationRequiredErrorType:
    """Tests that the URLElicitationRequiredError type and error code -32042 are
    correctly modeled. Full end-to-end workflow tests (third-party auth detection,
    retry-after-completion, auth-context-bound state) are deferred to a follow-up PR."""

    def test_error_code_is_minus_32042(self):
        """URLElicitationRequiredError must use code -32042."""
        err = URLElicitationRequiredError(
            code=-32042,
            message="Elicitation required",
            data={
                "elicitations": [
                    {
                        "mode": "url",
                        "elicitationId": "e1",
                        "url": "https://example.com/auth",
                        "message": "Auth needed",
                    }
                ]
            },
        )
        assert err.code == -32042

    def test_error_data_structure(self):
        """Error data must include elicitations array with mode, elicitationId, url."""
        err = URLElicitationRequiredError(
            code=-32042,
            message="Elicitation required",
            data={
                "elicitations": [
                    {
                        "mode": "url",
                        "elicitationId": "e1",
                        "url": "https://example.com/auth",
                        "message": "Auth needed",
                    }
                ]
            },
        )
        elicitations = err.data["elicitations"]
        assert len(elicitations) == 1
        assert elicitations[0]["mode"] == "url"
        assert "elicitationId" in elicitations[0]
        assert "url" in elicitations[0]

    def test_error_default_code(self):
        """URLElicitationRequiredError defaults to -32042 when code not specified."""
        err = URLElicitationRequiredError(message="Elicitation required", data={"elicitations": []})
        assert err.code == -32042


# ============================================================================
# Tool name & schema validation tests
# ============================================================================

from arcade_mcp_server.exceptions import UnsupportedSchemaDialectError
from arcade_mcp_server.validation import _validate_schema_dialect, is_valid_tool_name


class TestToolNameValidation:
    """Tests for tool name validation guidance.

    Rules are SHOULD (not MUST), so we warn at registration time, not reject."""

    def test_valid_tool_name_accepted(self):
        assert is_valid_tool_name("getUser")
        assert is_valid_tool_name("DATA_EXPORT_v2")
        assert is_valid_tool_name("admin.tools.list")
        assert is_valid_tool_name("my-tool-123")

    def test_tool_name_with_spaces_warns(self):
        assert not is_valid_tool_name("my tool")

    def test_tool_name_too_long_warns(self):
        assert not is_valid_tool_name("a" * 129)

    def test_tool_name_empty_warns(self):
        assert not is_valid_tool_name("")

    def test_tool_name_special_chars_warns(self):
        assert not is_valid_tool_name("tool@name")
        assert not is_valid_tool_name("tool,name")


class TestSchemaDialectValidation:
    """Tests for JSON Schema 2020-12 dialect support."""

    def test_schema_without_dollar_schema_is_valid(self):
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        _validate_schema_dialect(schema)

    def test_schema_with_2020_12_dialect_is_valid(self):
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}
        _validate_schema_dialect(schema)

    def test_schema_with_unsupported_dialect_raises_error(self):
        schema = {"$schema": "https://json-schema.org/draft/04/schema", "type": "object"}
        with pytest.raises(UnsupportedSchemaDialectError):
            _validate_schema_dialect(schema)

    def test_schema_with_mcp_spec_version_tagged_uri_is_valid(self):
        schema = {"$schema": "https://json-schema.org/2025-11-25/2020-12/schema", "type": "object"}
        _validate_schema_dialect(schema)

    def test_schema_with_2020_12_http_variant_is_valid(self):
        schema = {"$schema": "http://json-schema.org/draft/2020-12/schema", "type": "object"}
        _validate_schema_dialect(schema)

    def test_schema_with_draft_07_raises_error(self):
        schema = {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"}
        with pytest.raises(UnsupportedSchemaDialectError):
            _validate_schema_dialect(schema)


class TestInputValidationAsToolError:
    """Input validation behavior is VERSION-GATED (response shape differs):
    - 2025-11-25: invalid args -> CallToolResult(isError=True)
    - 2025-06-18: invalid args -> JSONRPCError -32602 (Invalid params)"""

    @pytest.mark.asyncio
    async def test_invalid_tool_params_returns_tool_error_for_2025_11_25(
        self, mcp_server, initialized_server_session
    ):
        """2025-11-25: Input validation errors should be CallToolResult(isError=True)."""
        initialized_server_session.negotiated_version = "2025-11-25"
        # Pass a dict for a string param to trigger ValidationError -> ToolInputError
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": {"nested": "dict"}}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.isError is True

    @pytest.mark.asyncio
    async def test_invalid_tool_params_returns_json_rpc_error_for_2025_06_18(
        self, mcp_server, initialized_server_session
    ):
        """2025-06-18: Input validation errors are JSONRPCError with -32602."""
        initialized_server_session.negotiated_version = "2025-06-18"
        # Pass a dict for a string param to trigger ValidationError -> ToolInputError
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": {"nested": "dict"}}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602


class TestUnknownToolProtocolError:
    """Unknown tools are protocol errors (JSON-RPC -32602), NOT tool execution errors."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_json_rpc_error(
        self, mcp_server, initialized_server_session
    ):
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_known_tool_bad_input_returns_tool_error_for_2025_11_25(
        self, mcp_server, initialized_server_session
    ):
        initialized_server_session.negotiated_version = "2025-11-25"
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": {"nested": "dict"}}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.isError is True

    @pytest.mark.asyncio
    async def test_known_tool_bad_input_returns_json_rpc_error_for_2025_06_18(
        self, mcp_server, initialized_server_session
    ):
        initialized_server_session.negotiated_version = "2025-06-18"
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": {"nested": "dict"}}},
        }
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)


class TestJSONRPCErrorIdHandling:
    """Tests that JSON-RPC error responses use proper id values."""

    @pytest.mark.asyncio
    async def test_error_with_none_id_serializes_as_json_null(self):
        """When request id is unknown, error id is None -> serializes as JSON null."""
        error = JSONRPCError(id=None, error={"code": -32600, "message": "Invalid"})
        json_str = error.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["id"] is None

    @pytest.mark.asyncio
    async def test_invalid_request_no_method_uses_actual_id(self, mcp_server):
        """Invalid request (no method field) uses the id from the message."""
        session = Mock()
        session.initialization_state = InitializationState.NOT_INITIALIZED
        message = {"jsonrpc": "2.0", "id": 99}  # no "method" field
        response = await mcp_server.handle_message(message, session)
        assert isinstance(response, JSONRPCError)
        assert response.id == 99

    @pytest.mark.asyncio
    async def test_method_not_found_uses_request_id(self, mcp_server, initialized_server_session):
        """Method-not-found error uses the request's id."""
        message = {"jsonrpc": "2.0", "id": "req-1", "method": "nonexistent/method"}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.id == "req-1"

    @pytest.mark.asyncio
    async def test_broad_except_handler_uses_request_id(
        self, mcp_server, initialized_server_session
    ):
        """Broad except handler uses the request's actual id."""
        from unittest.mock import patch

        # Patch _parse_message to raise an unexpected error, triggering the broad except
        message = {
            "jsonrpc": "2.0",
            "id": "abc-123",
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"}},
        }
        with patch.object(mcp_server, "_parse_message", side_effect=RuntimeError("unexpected")):
            response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.id == "abc-123"


class TestToolErrorResponse:
    """Test that tool error responses surface structured error data to agents."""

    def _make_error_output(
        self,
        message: str = "Something went wrong",
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        kind: ErrorKind = ErrorKind.TOOL_RUNTIME_FATAL,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                additional_prompt_content=additional_prompt_content,
                kind=kind,
            )
        )

    @pytest.mark.asyncio
    async def test_tool_error_content_includes_additional_prompt(self, mcp_server):
        error_output = self._make_error_output(
            message="Spreadsheet not found",
            additional_prompt_content="Available options: X, Y",
        )
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "test"}},
        )

        with patch(
            "arcade_mcp_server.server.ToolExecutor.run",
            new_callable=AsyncMock,
            return_value=error_output,
        ):
            response = await mcp_server._handle_call_tool(message)

        assert response.result.isError is True
        text = response.result.content[0].text
        assert "Available options: X, Y" in text

    @pytest.mark.asyncio
    async def test_tool_error_structured_content_is_none(self, mcp_server):
        """Per MCP spec, structuredContent must be None on error responses so
        consumers don't attempt to validate an error payload against the tool's
        declared outputSchema. Error details are conveyed via content text."""
        error_output = self._make_error_output(message="fail")
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "test"}},
        )

        with patch(
            "arcade_mcp_server.server.ToolExecutor.run",
            new_callable=AsyncMock,
            return_value=error_output,
        ):
            response = await mcp_server._handle_call_tool(message)

        assert response.result.isError is True
        assert response.result.structuredContent is None
        assert "fail" in response.result.content[0].text

    @pytest.mark.asyncio
    async def test_tool_error_content_no_pydantic_repr(self, mcp_server):
        error_output = self._make_error_output(message="fail")
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "test"}},
        )

        with patch(
            "arcade_mcp_server.server.ToolExecutor.run",
            new_callable=AsyncMock,
            return_value=error_output,
        ):
            response = await mcp_server._handle_call_tool(message)

        text = response.result.content[0].text
        assert "kind=<ErrorKind" not in text

    @pytest.mark.asyncio
    async def test_tool_error_developer_message_not_in_client_content(self, mcp_server):
        """developer_message can contain stack frames/file paths/sensitive data
        and must never appear in agent-facing content. It is logged structurally
        for Datadog instead."""
        error_output = self._make_error_output(
            message="Something failed",
            developer_message="Traceback: /home/user/secret/foo.py line 42",
        )
        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "TestToolkit.test_tool", "arguments": {"text": "test"}},
        )

        with patch(
            "arcade_mcp_server.server.ToolExecutor.run",
            new_callable=AsyncMock,
            return_value=error_output,
        ):
            response = await mcp_server._handle_call_tool(message)

        text = response.result.content[0].text
        assert "Traceback" not in text
        assert "/home/user/secret" not in text
        assert "Details:" not in text


class TestLogToolCallError:
    """Direct unit tests for MCPServer._log_tool_call_error.

    The structured ``extra`` dict is the contract Datadog facets on; tests here
    lock the field names and value sources so accidental renames can't silently
    break ops dashboards. Tested in isolation (no full request flow needed)."""

    def test_extra_fields_match_contract(self, mcp_server, caplog):
        import logging

        err = ToolCallError(
            message="Spreadsheet not found",
            developer_message="dev: ssn=123",
            kind=ErrorKind.TOOL_RUNTIME_FATAL,
            status_code=404,
            can_retry=False,
        )
        with caplog.at_level(logging.WARNING, logger="arcade.mcp"):
            mcp_server._log_tool_call_error("MyToolkit.MyTool", err)

        record = next(r for r in caplog.records if "MyToolkit.MyTool error" in r.getMessage())
        # Renderable text is the human-readable summary.
        assert "Spreadsheet not found" in record.getMessage()
        # Structured fields — the Datadog contract.
        assert record.tool_name == "MyToolkit.MyTool"
        assert record.error_kind == "TOOL_RUNTIME_FATAL"
        assert record.error_message == "Spreadsheet not found"
        assert record.error_developer_message == "dev: ssn=123"
        assert record.error_status_code == 404
        assert record.error_can_retry is False

    def test_kind_value_used_when_available(self, mcp_server, caplog):
        import logging

        err = ToolCallError(message="x", kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT)
        with caplog.at_level(logging.WARNING, logger="arcade.mcp"):
            mcp_server._log_tool_call_error("t", err)

        record = next(r for r in caplog.records if "t error" in r.getMessage())
        # Enum's .value (the string code) is what Datadog facets on, NOT repr().
        assert record.error_kind == "UPSTREAM_RUNTIME_RATE_LIMIT"
        assert "ErrorKind." not in record.error_kind

    def test_emits_warning_level(self, mcp_server, caplog):
        import logging

        err = ToolCallError(message="boom", kind=ErrorKind.TOOL_RUNTIME_FATAL)
        with caplog.at_level(logging.DEBUG, logger="arcade.mcp"):
            mcp_server._log_tool_call_error("t", err)

        record = next(r for r in caplog.records if "t error" in r.getMessage())
        # WARNING (30) is the load-bearing level for ops alerting.
        assert record.levelno == logging.WARNING

    def test_optional_fields_propagate_none(self, mcp_server, caplog):
        """status_code / developer_message default to None and must propagate
        as None (not be dropped, not be coerced) so Datadog can distinguish
        'unset' from 'set to falsy'."""
        import logging

        err = ToolCallError(message="x", kind=ErrorKind.TOOL_RUNTIME_FATAL)
        with caplog.at_level(logging.WARNING, logger="arcade.mcp"):
            mcp_server._log_tool_call_error("t", err)

        record = next(r for r in caplog.records if "t error" in r.getMessage())
        assert record.error_developer_message is None
        assert record.error_status_code is None

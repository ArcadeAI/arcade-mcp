"""Tests for MCP Server implementation."""

import asyncio
import contextlib
from typing import Annotated
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_core.auth import OAuth2
from arcade_core.catalog import MaterializedTool, ToolMeta, create_func_models
from arcade_core.errors import ToolRuntimeError
from arcade_core.schema import (
    InputParameter,
    OAuth2Requirement,
    ToolAuthRequirement,
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
from arcade_mcp_server.middleware import Middleware
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
        assert response.result.structuredContent is not None
        assert "authorization_url" in response.result.structuredContent
        assert response.result.structuredContent["authorization_url"] == "https://example.com/auth"
        assert "message" in response.result.structuredContent
        assert "Authorization required" in response.result.structuredContent["message"]
        assert "needs your permission" in response.result.structuredContent["message"]

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
        assert response.result.structuredContent is not None
        assert "message" in response.result.structuredContent
        assert "Missing Arcade API key" in response.result.structuredContent["message"]
        assert "requires authorization" in response.result.structuredContent["message"]
        assert "arcade login" in response.result.structuredContent["message"]
        assert "ARCADE_API_KEY" in response.result.structuredContent["message"]
        assert "ARCADE_API_KEY" in response.result.structuredContent["llm_instructions"]

    @pytest.mark.asyncio
    async def test_handle_call_tool_not_found(self, mcp_server):
        """Test calling a non-existent tool."""
        message = CallToolRequest(
            jsonrpc="2.0",
            id=3,
            method="tools/call",
            params={"name": "NonExistent.tool", "arguments": {}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCResponse)
        assert response.result.isError
        assert "error" in response.result.structuredContent
        assert "Unknown tool" in response.result.structuredContent["error"]

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
        assert "Missing Arcade API key" in result.result.structuredContent["message"]
        assert "requires authorization" in result.result.structuredContent["message"]
        assert "ARCADE_API_KEY" in result.result.structuredContent["message"]
        assert "ARCADE_API_KEY" in result.result.structuredContent["llm_instructions"]

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

        # Should return error response with authorization URL
        assert isinstance(result, JSONRPCResponse)
        assert isinstance(result.result, CallToolResult)
        assert result.result.isError is True
        assert "authorization_url" in result.result.structuredContent
        assert result.result.structuredContent["authorization_url"] == "https://example.com/auth"
        assert "Authorization required" in result.result.structuredContent["message"]
        assert "needs your permission" in result.result.structuredContent["message"]

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
        assert "Authorization error" in result.result.structuredContent["message"]
        assert "failed to authorize" in result.result.structuredContent["message"]
        assert "Auth failed" in result.result.structuredContent["message"]

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
        assert "Missing secret" in result.result.structuredContent["message"]
        assert "API_KEY, DATABASE_URL" in result.result.structuredContent["message"]
        assert ".env file" in result.result.structuredContent["message"]
        assert ".env file" in result.result.structuredContent["llm_instructions"]

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
        assert "DATABASE_URL" in result.result.structuredContent["message"]
        assert "API_KEY" not in result.result.structuredContent["message"]

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
        assert "authorization_url" in result.result.structuredContent

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
        assert "HTTP transport" in response.result.structuredContent["message"]

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
        assert "HTTP transport" in response.result.structuredContent["message"]
        assert "secrets" in response.result.structuredContent["message"]

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
        assert "Unsupported transport" in response.result.structuredContent["message"]
        assert "HTTP transport" in response.result.structuredContent["message"]
        assert "authorization" in response.result.structuredContent["message"]

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

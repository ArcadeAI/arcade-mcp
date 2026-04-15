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

        tmpl = ResourceTemplate(
            uriTemplate="data://{item_id}", name="Data", mimeType="text/plain"
        )

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

        tmpl = ResourceTemplate(
            uriTemplate="schema://{type}", name="Schema"
        )

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
    Per spec (lifecycle.mdx:221): parties MUST only use capabilities that were successfully negotiated.
    Tasks sub-capabilities (tasks.mdx:45-107): tasks.list, tasks.cancel, tasks.requests.tools.call."""

    # Full tasks capability structure for tests
    FULL_TASKS_CAP = {
        "tasks": {"list": {}, "cancel": {}, "requests": {"tools": {"call": {}}}}
    }
    # Tasks without list
    TASKS_NO_LIST = {
        "tasks": {"cancel": {}, "requests": {"tools": {"call": {}}}}
    }
    # Tasks without cancel
    TASKS_NO_CANCEL = {
        "tasks": {"list": {}, "requests": {"tools": {"call": {}}}}
    }

    @pytest.mark.asyncio
    async def test_tasks_get_rejected_without_tasks_capability(self, mcp_server, initialized_server_session):
        """tasks/get must return method-not-found when base tasks capability not declared."""
        initialized_server_session.negotiated_version = "2025-06-18"
        # 2025-06-18 sessions have no tasks capability
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601  # METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_tasks_list_rejected_without_tasks_list_sub_capability(self, mcp_server, initialized_server_session):
        """tasks/list requires tasks.list sub-capability, not just base tasks."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.TASKS_NO_LIST
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_list_accepted_with_tasks_list_sub_capability(self, mcp_server, initialized_server_session):
        """tasks/list works when tasks.list sub-capability is declared."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.FULL_TASKS_CAP
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/list", "params": {}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        if isinstance(response, JSONRPCError):
            assert response.error["code"] != -32601  # NOT method-not-found

    @pytest.mark.asyncio
    async def test_tasks_cancel_rejected_without_tasks_cancel_sub_capability(self, mcp_server, initialized_server_session):
        """tasks/cancel requires tasks.cancel sub-capability."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.TASKS_NO_CANCEL
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/cancel",
                   "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_result_rejected_without_tasks_capability(self, mcp_server, initialized_server_session):
        """tasks/result requires base tasks capability."""
        initialized_server_session.negotiated_version = "2025-06-18"
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result",
                   "params": {"taskId": "t1"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_tasks_get_accepted_with_base_tasks_capability(self, mcp_server, initialized_server_session):
        """tasks/get only requires base tasks capability (always present when tasks declared).
        (May return 'task not found' error, but not -32601.)"""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = self.TASKS_NO_LIST  # no list, but base tasks exists
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": "nonexistent"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        if isinstance(response, JSONRPCError):
            assert response.error["code"] != -32601  # NOT method-not-found

    @pytest.mark.asyncio
    async def test_2025_11_25_session_without_tasks_capability_rejects_all_tasks(self, mcp_server, initialized_server_session):
        """Dispatch gating works even with manually cleared capabilities."""
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._negotiated_capabilities = {}  # no tasks at all
        for method in ["tasks/get", "tasks/result", "tasks/list", "tasks/cancel"]:
            message = {"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": {"taskId": "t1"} if method != "tasks/list" else {}}
            response = await mcp_server.handle_message(message, initialized_server_session)
            assert isinstance(response, JSONRPCError), f"{method} should be rejected"
            assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_existing_methods_work_for_both_versions(self, mcp_server, initialized_server_session):
        """tools/list, ping, etc. work regardless of version."""
        for version in ["2025-06-18", "2025-11-25"]:
            initialized_server_session.negotiated_version = version
            message = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
            response = await mcp_server.handle_message(message, initialized_server_session)
            assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_capability_gated_methods_rejected_when_no_negotiated_version(self, mcp_server, initialized_server_session):
        """If session has no negotiated_version (shouldn't happen, but defensive), reject gated methods."""
        initialized_server_session.negotiated_version = None
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": "t1"}}
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
    async def test_session_fallback_when_no_resource_owner(self, mcp_server, initialized_server_session):
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
    async def test_unknown_client_id_logs_warning(self, mcp_server, initialized_server_session, caplog):
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
    async def test_handle_get_task_returns_flat_result(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.taskId == task.taskId

    @pytest.mark.asyncio
    async def test_handle_get_task_returns_immediately(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": task.taskId}}
        response = await asyncio.wait_for(
            mcp_server.handle_message(message, initialized_server_session), timeout=1.0
        )
        assert response.result.status == TaskStatus.WORKING

    @pytest.mark.asyncio
    async def test_handle_get_task_not_found(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": "nonexistent"}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602

    @pytest.mark.asyncio
    async def test_handle_get_task_cross_context_isolation(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        task = await mcp_server._task_manager.create_task(
            context_key="auth:https://other-issuer.com:other-client:other-user"
        )
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": task.taskId}}
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
    async def test_handle_cancel_task_returns_flat_result(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/cancel",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert response.result.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_handle_tasks_result_blocks_until_complete(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "answer"}], "isError": False}

        async def complete_later():
            await asyncio.sleep(0.1)
            await mcp_server._task_manager.set_result(task.taskId, result_data)
            await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result",
                   "params": {"taskId": task.taskId}}

        async with asyncio.TaskGroup() as tg:
            tg.create_task(complete_later())
            response = await asyncio.wait_for(
                mcp_server.handle_message(message, initialized_server_session), timeout=5.0
            )
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_handle_tasks_result_returns_immediately_for_completed(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "done"}]}
        await mcp_server._task_manager.set_result(task.taskId, result_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result",
                   "params": {"taskId": task.taskId}}
        response = await asyncio.wait_for(
            mcp_server.handle_message(message, initialized_server_session), timeout=1.0
        )
        assert not isinstance(response, JSONRPCError)


class TestTaskAugmentedToolCall:
    """Tests for task-augmented tools/call."""

    @pytest.mark.asyncio
    async def test_tool_call_with_task_returns_create_task_result(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"},
                              "_meta": {}, "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "task")
        assert response.result.task.status == TaskStatus.WORKING
        assert response.result.task.taskId is not None

    @pytest.mark.asyncio
    async def test_tool_call_without_task_returns_normal_result(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "content")
        assert not hasattr(response.result, "task")

    @pytest.mark.asyncio
    async def test_task_augmented_tool_completes_in_background(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"},
                              "task": {"ttl": 60000}}}
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
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.failing_tool", "arguments": {},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = response.result.task.taskId
        await asyncio.wait_for(
            mcp_server._task_manager.get_result(task_id, context_key=f"session:{sid}"), timeout=5.0
        )
        task = await mcp_server._task_manager.get_task(task_id, context_key=f"session:{sid}")
        assert task.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancel_running_task_cancels_tool_execution(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.slow_tool", "arguments": {},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        task_id = response.result.task.taskId

        # Cancel while running
        cancel_msg = {"jsonrpc": "2.0", "id": 2, "method": "tasks/cancel",
                      "params": {"taskId": task_id}}
        await mcp_server.handle_message(cancel_msg, initialized_server_session)
        task = await mcp_server._task_manager.get_task(task_id, context_key=f"session:{sid}")
        assert task.status == TaskStatus.CANCELLED


class TestRelatedTaskMetadata:
    """Tests for _meta.io.modelcontextprotocol/related-task propagation."""

    @pytest.mark.asyncio
    async def test_create_task_result_includes_related_task_meta(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = response.result.model_dump(exclude_none=True, by_alias=True)
        meta = result_dict.get("_meta", {})
        related = meta.get("io.modelcontextprotocol/related-task", {})
        assert "taskId" in related
        assert related["taskId"] == response.result.task.taskId

    @pytest.mark.asyncio
    async def test_tasks_result_success_response_includes_related_task_meta(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        result_data = {"content": [{"type": "text", "text": "done"}]}
        await mcp_server._task_manager.set_result(task.taskId, result_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.COMPLETED)

        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        # The result should be a dict with _meta injected
        result = response.result
        if isinstance(result, dict):
            meta = result.get("_meta", {})
            related = meta.get("io.modelcontextprotocol/related-task", {})
            assert related.get("taskId") == task.taskId
        else:
            # Pydantic model
            result_dict = result.model_dump(exclude_none=True, by_alias=True) if hasattr(result, "model_dump") else {}
            meta = result_dict.get("_meta", {})
            related = meta.get("io.modelcontextprotocol/related-task", {})
            assert related.get("taskId") == task.taskId

    @pytest.mark.asyncio
    async def test_tasks_result_error_response_returns_underlying_error_unchanged(self, mcp_server, initialized_server_session):
        """tasks/result for a FAILED task returns the underlying JSON-RPC error unchanged."""
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        error_data = {"code": -32603, "message": "Internal error"}
        await mcp_server._task_manager.set_error(task.taskId, error_data)
        await mcp_server._task_manager.update_status(task.taskId, TaskStatus.FAILED)

        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/result",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32603

    @pytest.mark.asyncio
    async def test_tasks_get_response_should_not_include_related_task_meta(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/get",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = response.result.model_dump(exclude_none=True, by_alias=True) if hasattr(response.result, "model_dump") else {}
        meta = result_dict.get("_meta", {})
        assert "io.modelcontextprotocol/related-task" not in meta

    @pytest.mark.asyncio
    async def test_tasks_cancel_response_should_not_include_related_task_meta(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        sid = initialized_server_session.session_id
        task = await mcp_server._task_manager.create_task(context_key=f"session:{sid}")
        message = {"jsonrpc": "2.0", "id": 1, "method": "tasks/cancel",
                   "params": {"taskId": task.taskId}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        result_dict = response.result.model_dump(exclude_none=True, by_alias=True) if hasattr(response.result, "model_dump") else {}
        meta = result_dict.get("_meta", {})
        assert "io.modelcontextprotocol/related-task" not in meta


class TestToolTaskNegotiationEnforcement:
    """Tests for Tool.execution.taskSupport enforcement rules."""

    @pytest.mark.asyncio
    async def test_forbidden_tool_rejects_task_metadata(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.forbidden_task_tool", "arguments": {},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_required_tool_rejects_non_task_call(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.required_task_tool", "arguments": {}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_optional_tool_accepts_task_metadata(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_optional_tool_accepts_normal_call(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)

    @pytest.mark.asyncio
    async def test_default_no_execution_rejects_task_metadata(self, mcp_server, initialized_server_session):
        _enable_tasks(initialized_server_session)
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.no_execution_tool", "arguments": {},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32601


class TestCapabilityFallback:
    """Tests for capability fallback: task metadata ignored when not negotiated."""

    @pytest.mark.asyncio
    async def test_2025_06_18_session_ignores_task_metadata(self, mcp_server, initialized_server_session):
        initialized_server_session.negotiated_version = "2025-06-18"
        initialized_server_session._negotiated_capabilities = {
            "tools": {"listChanged": True},
            "logging": {},
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
        }
        message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "hello"},
                              "task": {"ttl": 60000}}}
        response = await mcp_server.handle_message(message, initialized_server_session)
        assert not isinstance(response, JSONRPCError)
        assert hasattr(response.result, "content")  # CallToolResult shape
        assert not hasattr(response.result, "task")  # NOT CreateTaskResult

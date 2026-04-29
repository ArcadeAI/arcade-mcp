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
        assert response.result.structuredContent is None
        assert "Unknown tool" in response.result.content[0].text

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


class TestLoadAccessToken:
    """Tests for MCPServer._load_access_token()."""

    def test_returns_valid_token(self, tool_catalog):
        with patch("arcade_mcp_server.server.get_valid_access_token", return_value="token-123"):
            server = MCPServer(catalog=tool_catalog)
            assert server._load_access_token() == "token-123"

    def test_expired_refresh_fails(self, tool_catalog):
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=ValueError("Token expired and refresh failed"),
        ):
            server = MCPServer(catalog=tool_catalog)
            assert server._load_access_token() is None

    def test_not_logged_in(self, tool_catalog):
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=ValueError("Not logged in"),
        ):
            server = MCPServer(catalog=tool_catalog)
            assert server._load_access_token() is None

    def test_unexpected_exception(self, tool_catalog):
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=RuntimeError("unexpected"),
        ):
            server = MCPServer(catalog=tool_catalog)
            assert server._load_access_token() is None


class TestLoadConfigUserId:
    """Tests for MCPServer._load_config_user_id().

    After the move from the cached singleton to ``Config.load_from_file()``, tests
    patch ``arcade_core.config_model.Config.load_from_file`` directly.
    """

    def test_returns_email(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        mock_config = Mock()
        mock_config.user = Mock(email="a@example.com")
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            return_value=mock_config,
        ):
            assert server._load_config_user_id() == "a@example.com"

    def test_no_user_section(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        mock_config = Mock()
        mock_config.user = None
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            return_value=mock_config,
        ):
            assert server._load_config_user_id() is None

    def test_email_is_none(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        mock_config = Mock()
        mock_config.user = Mock(email=None)
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            return_value=mock_config,
        ):
            assert server._load_config_user_id() is None

    def test_config_load_raises(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            side_effect=FileNotFoundError("missing"),
        ):
            assert server._load_config_user_id() is None


class TestInitArcadeClient:
    """Tests for MCPServer Arcade client initialization.

    After the lazy-init change, ``MCPServer.__init__`` builds a client only when
    an explicit api_key is provided (constructor arg or ``ARCADE_API_KEY``).
    When neither is set, ``self.arcade`` stays ``None`` until the auth-required
    branch's retry-first path loads credentials from disk.
    """

    def test_explicit_api_key(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog, arcade_api_key="arc_key")
        assert server.arcade is not None
        assert server.arcade.api_key == "arc_key"

    def test_no_explicit_key_leaves_client_none(self, tool_catalog):
        """No explicit key → constructor leaves self.arcade = None (lazy)."""
        # Patch get_valid_access_token to raise if anyone calls it during init.
        sentinel = Mock(side_effect=AssertionError("get_valid_access_token must not be called"))
        with patch("arcade_mcp_server.server.get_valid_access_token", sentinel):
            server = MCPServer(catalog=tool_catalog)
            assert server.arcade is None
            sentinel.assert_not_called()

    def test_no_key_no_token(self, tool_catalog):
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=ValueError("Not logged in"),
        ):
            server = MCPServer(catalog=tool_catalog)
            assert server.arcade is None


class TestSelectUserId:
    """Tests for MCPServer._select_user_id() using _load_config_user_id."""

    def test_from_settings(self, tool_catalog):
        from arcade_mcp_server.settings import ArcadeSettings, MCPSettings

        settings = MCPSettings(arcade=ArcadeSettings(user_id="set-user"))
        server = MCPServer(catalog=tool_catalog, settings=settings)
        result = server._select_user_id(session=None)
        assert result == "set-user"

    def test_from_config_email(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        server._load_config_user_id = Mock(return_value="cfg@ex.com")
        session = Mock()
        session.session_id = "sess-123"
        result = server._select_user_id(session=session)
        assert result == "cfg@ex.com"

    def test_fallback_to_session(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        server._load_config_user_id = Mock(return_value=None)
        session = Mock()
        session.session_id = "sess-456"
        result = server._select_user_id(session=session)
        assert result == "sess-456"

    def test_email_survives_token_failure(self, tool_catalog):
        """Email is returned even when access token retrieval fails."""
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=ValueError("expired"),
        ):
            server = MCPServer(catalog=tool_catalog)

        mock_config = Mock()
        mock_config.user = Mock(email="user@arcade.dev")
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            return_value=mock_config,
        ):
            session = Mock()
            session.session_id = "sess-789"
            result = server._select_user_id(session=session)
            assert result == "user@arcade.dev"

    def test_no_session_returns_none(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        server._load_config_user_id = Mock(return_value=None)
        result = server._select_user_id(session=None)
        assert result is None


class TestLazyTokenRefresh:
    """Tests for lazy token refresh in _check_authorization."""

    @pytest.mark.asyncio
    async def test_refreshes_token(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog, arcade_api_key="old")
        assert server.arcade is not None
        server._load_access_token = Mock(return_value="new")

        mock_auth_response = Mock()
        mock_auth_response.status = "completed"
        mock_auth_response.context = Mock()
        mock_auth_response.context.token = "tok"
        mock_auth_response.context.user_info = {}

        tool_mock = Mock()
        tool_mock.definition.requirements.authorization = ToolAuthRequirement(
            provider_type="oauth2", provider_id="test"
        )

        with patch.object(server.arcade.auth, "authorize", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = mock_auth_response
            await server._check_authorization(tool_mock, user_id="u")

        assert server.arcade.api_key == "new"

    @pytest.mark.asyncio
    async def test_refresh_fails_keeps_existing(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog, arcade_api_key="old")
        assert server.arcade is not None
        server._load_access_token = Mock(return_value=None)

        mock_auth_response = Mock()
        mock_auth_response.status = "completed"

        tool_mock = Mock()
        tool_mock.definition.requirements.authorization = ToolAuthRequirement(
            provider_type="oauth2", provider_id="test"
        )

        with patch.object(server.arcade.auth, "authorize", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = mock_auth_response
            await server._check_authorization(tool_mock, user_id="u")

        assert server.arcade.api_key == "old"

    @pytest.mark.asyncio
    async def test_no_arcade_client_raises(self, tool_catalog):
        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_mock = Mock()
        tool_mock.definition.requirements.authorization = ToolAuthRequirement(
            provider_type="oauth2", provider_id="test"
        )

        with pytest.raises(ToolRuntimeError, match="without Arcade API key"):
            await server._check_authorization(tool_mock)


class TestTokenEmailDecoupling:
    """End-to-end regression: email is preserved when token is expired."""

    def test_tool_call_uses_email_when_token_expired(self, tool_catalog):
        with patch(
            "arcade_mcp_server.server.get_valid_access_token",
            side_effect=ValueError("expired"),
        ):
            server = MCPServer(catalog=tool_catalog, arcade_api_key="valid")

        mock_config = Mock()
        mock_config.user = Mock(email="user@arcade.dev")
        with patch(
            "arcade_core.config_model.Config.load_from_file",
            return_value=mock_config,
        ):
            session = Mock()
            session.session_id = "session-uuid"
            result = server._select_user_id(session=session)
            assert result == "user@arcade.dev"
            assert result != "session-uuid"


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


class TestNoTokenBootstrap:
    """Tests for the bootstrap-login wiring in MCPServer.

    These tests cover:
    - Lazy startup (no network I/O when no explicit api_key).
    - Direct ``Config.load_from_file()`` use in user/org loaders.
    - Bootstrap path in ``_check_tool_requirements`` (stdio + auth-required + no client).
    - No ``developer_message`` / ``reason`` / ``detail`` leak in error responses.
    """

    def _write_credentials(
        self,
        config_dir,
        *,
        email: str = "user@example.com",
        org_id: str = "org-1",
        project_id: str = "proj-1",
        access_token: str = "tok-abc",
        coordinator_url: str = "https://cloud.arcade.dev",
    ) -> None:
        """Write a minimal Arcade credentials.yaml file at ``config_dir``."""
        import time
        import yaml

        config_dir.mkdir(parents=True, exist_ok=True)
        contents = {
            "cloud": {
                "coordinator_url": coordinator_url,
                "auth": {
                    "access_token": access_token,
                    "refresh_token": "ref-abc",
                    "expires_at": int(time.time()) + 3600,
                },
                "user": {"email": email},
                "context": {
                    "org_id": org_id,
                    "org_name": "Acme",
                    "project_id": project_id,
                    "project_name": "Main",
                },
            }
        }
        (config_dir / "credentials.yaml").write_text(yaml.safe_dump(contents))

    def test_load_config_user_id_sees_freshly_written_credentials_without_cache_clear(
        self, tool_catalog, tmp_path, monkeypatch
    ):
        """``_load_config_user_id`` must use ``Config.load_from_file()`` (no cached singleton),
        so an updated email is reflected immediately on the next call."""
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))

        server = MCPServer(catalog=tool_catalog)

        self._write_credentials(tmp_path, email="first@example.com")
        assert server._load_config_user_id() == "first@example.com"

        # Overwrite without clearing any cache
        self._write_credentials(tmp_path, email="second@example.com")
        assert server._load_config_user_id() == "second@example.com"

    def test_load_org_project_context_sees_freshly_written_credentials_without_cache_clear(
        self, tool_catalog, tmp_path, monkeypatch
    ):
        """Same property for org/project context loader."""
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))

        server = MCPServer(catalog=tool_catalog)

        self._write_credentials(tmp_path, org_id="org-A", project_id="proj-A")
        assert server._load_org_project_context() == ("org-A", "proj-A")

        self._write_credentials(tmp_path, org_id="org-B", project_id="proj-B")
        assert server._load_org_project_context() == ("org-B", "proj-B")

    def test_server_init_does_no_network_io_on_stdio_when_no_explicit_key(
        self, tool_catalog, tmp_path, monkeypatch
    ):
        """``MCPServer.__init__`` must not call ``get_valid_access_token`` when no explicit
        api key is given (stdio cold-start must be I/O-free)."""
        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))
        monkeypatch.delenv("ARCADE_API_KEY", raising=False)

        sentinel = Mock(side_effect=AssertionError("get_valid_access_token must not be called"))
        with patch("arcade_mcp_server.server.get_valid_access_token", sentinel):
            server = MCPServer(catalog=tool_catalog)

        assert server.arcade is None
        sentinel.assert_not_called()

    @pytest.mark.asyncio
    async def test_server_stop_shuts_down_inflight_login_slot(self, tool_catalog):
        """``MCPServer._stop`` must close the login slot."""
        server = MCPServer(catalog=tool_catalog)

        # Force the slot to look as if it has an in-flight attempt.
        with patch.object(
            server._login_slot, "shutdown", new_callable=AsyncMock
        ) as shutdown_mock:
            await server.start()
            await server.stop()
            shutdown_mock.assert_called()

    @pytest.mark.asyncio
    async def test_service_key_short_circuits_before_bootstrap(self, tool_catalog):
        """When an explicit service key is configured, bootstrap must NOT be invoked."""
        server = MCPServer(catalog=tool_catalog, arcade_api_key="arc_abc123")
        assert server.arcade is not None
        assert server._has_service_key is True

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # Mock _check_authorization to short-circuit completion path
        completed = Mock()
        completed.status = "completed"
        completed.context = Mock(token="t", user_info={})
        server._check_authorization = AsyncMock(return_value=completed)

        bootstrap_mock = AsyncMock(side_effect=AssertionError("bootstrap_login should not be called"))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            session = Mock()
            session.init_options = {"transport_type": "stdio"}
            session.session_id = "sess"
            tool_context = ToolContext()

            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.t", "arguments": {}},
                ),
                "T.t",
                session=session,
            )

        assert result is None  # auth completed
        bootstrap_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_secrets_only_tool_does_not_bootstrap(self, tool_catalog):
        """Secrets-only tool must not trigger bootstrap; existing missing-secret path applies."""
        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            secrets=[ToolSecretRequirement(key="MY_SECRET")]
        )

        tool_context = Mock(spec=ToolContext)
        tool_context.get_secret = Mock(side_effect=ValueError("not set"))

        bootstrap_mock = AsyncMock(side_effect=AssertionError("bootstrap_login should not be called"))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            session = Mock()
            session.init_options = {"transport_type": "stdio"}
            session.session_id = "sess"

            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.s", "arguments": {}},
                ),
                "T.s",
                session=session,
            )

        bootstrap_mock.assert_not_called()
        assert isinstance(result, JSONRPCResponse)
        assert result.result.isError is True
        assert "MY_SECRET" in result.result.content[0].text

    @pytest.mark.asyncio
    async def test_http_transport_does_not_bootstrap_when_arcade_is_none(self, tool_catalog):
        """HTTP transport with no client must NOT bootstrap; existing error response is returned."""
        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        bootstrap_mock = AsyncMock(side_effect=AssertionError("bootstrap_login should not be called"))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            session = Mock()
            session.init_options = {"transport_type": "streamable-http"}
            session.session_id = "sess"

            tool_context = ToolContext()
            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        bootstrap_mock.assert_not_called()
        assert isinstance(result, JSONRPCResponse)
        assert result.result.isError is True
        assert "Missing Arcade API key" in result.result.content[0].text

    @pytest.mark.asyncio
    async def test_missing_client_retries_load_before_bootstrap(self, tool_catalog):
        """Stdio + no client + auth required: retry-first must succeed if creds appeared,
        and bootstrap must NOT be called."""
        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # Patch _load_access_token to return a token (creds appeared since startup).
        server._load_access_token = Mock(return_value="oauth-tok")
        server._load_config_user_id = Mock(return_value="user@example.com")

        # _check_authorization succeeds.
        completed = Mock()
        completed.status = "completed"
        completed.context = Mock(token="t", user_info={})
        server._check_authorization = AsyncMock(return_value=completed)

        bootstrap_mock = AsyncMock(side_effect=AssertionError("bootstrap_login should not be called"))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            session = Mock()
            session.init_options = {"transport_type": "stdio"}
            session.session_id = "sess"

            tool_context = ToolContext()
            tool_context.user_id = "stale-id"
            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        # No error returned (proceeded).
        assert result is None
        bootstrap_mock.assert_not_called()
        # Retry-first picked up the token, built the client, and refreshed user_id.
        assert server.arcade is not None
        assert tool_context.user_id == "user@example.com"
        server._load_access_token.assert_called()

    @pytest.mark.asyncio
    async def test_tool_call_with_no_token_and_elicitation_capable_client_completes_login_and_retries(
        self, tool_catalog
    ):
        """Stdio + no client + elicitation-capable client + bootstrap completes →
        tool proceeds to _check_authorization."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # _load_access_token returns None initially, then returns a token after bootstrap.
        load_calls = {"n": 0}

        def fake_load() -> str | None:
            load_calls["n"] += 1
            return "oauth-tok" if load_calls["n"] >= 2 else None

        server._load_access_token = Mock(side_effect=fake_load)
        server._load_config_user_id = Mock(return_value="user@example.com")

        # _check_authorization succeeds.
        completed = Mock()
        completed.status = "completed"
        completed.context = Mock(token="t", user_info={})
        server._check_authorization = AsyncMock(return_value=completed)

        # Real session with elicitation capability.
        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(elicitation={}),
            clientInfo={"name": "c", "version": "1"},
        )

        # Add a real check_client_capability semantics to the mock (use real method via patch).
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        bootstrap_mock = AsyncMock(return_value=BootstrapResult.completed())
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tool_context = ToolContext()
            tool_context.user_id = "stale-id"

            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        assert result is None  # proceeded to authorization
        bootstrap_mock.assert_called_once()
        # elicit kwarg should be session.elicit (not None)
        bootstrap_kwargs = bootstrap_mock.call_args.kwargs
        assert bootstrap_kwargs["elicit"] is session.elicit
        # tool_context.user_id refreshed from config
        assert tool_context.user_id == "user@example.com"

    @pytest.mark.asyncio
    async def test_tool_call_with_no_token_and_no_elicitation_returns_error_with_login_url(
        self, tool_catalog
    ):
        """Stdio + no client + no elicitation → returns error with the login URL."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        server._load_access_token = Mock(return_value=None)

        # Session with NO elicitation capability declared.
        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        login_url = "https://cloud.arcade.dev/oauth/authorize?xxx"
        bootstrap_mock = AsyncMock(return_value=BootstrapResult.url_for_fallback(login_url))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tool_context = ToolContext()
            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        # Error response with URL in content[0].text
        assert isinstance(result, JSONRPCResponse)
        assert result.result.isError is True
        first_text = result.result.content[0].text
        assert login_url in first_text

        # Second content item carries machine-readable extras
        assert len(result.result.content) >= 2
        extras = json.loads(result.result.content[1].text)
        assert extras.get("authorization_url") == login_url
        assert "llm_instructions" in extras
        # No internals leaked
        assert "developer_message" not in extras
        assert "reason" not in extras
        assert "detail" not in extras

        # bootstrap_login was called with elicit=None
        bootstrap_kwargs = bootstrap_mock.call_args.kwargs
        assert bootstrap_kwargs["elicit"] is None

    @pytest.mark.asyncio
    async def test_no_elicit_call_when_client_lacks_elicitation_capability(self, tool_catalog):
        """session.elicit must NOT be called when client lacks elicitation capability."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        server._load_access_token = Mock(return_value=None)

        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        bootstrap_mock = AsyncMock(
            return_value=BootstrapResult.url_for_fallback("https://cloud.arcade.dev/x")
        )
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tool_context = ToolContext()
            await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        session.elicit.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_call_with_no_token_bootstrap_failure_surfaces_clean_error_no_developer_message_leak(
        self, tool_catalog
    ):
        """Bootstrap failure → clean error response with no internal fields leaked."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        server._load_access_token = Mock(return_value=None)

        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        bootstrap_mock = AsyncMock(
            return_value=BootstrapResult.failed(
                reason="port_in_use", detail="9905 is already bound"
            )
        )
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tool_context = ToolContext()
            result = await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        assert isinstance(result, JSONRPCResponse)
        assert result.result.isError is True

        # Reason allowed in llm_instructions (machine-readable hint), but NOT detail/developer.
        all_text = "\n".join(c.text for c in result.result.content)
        assert "9905 is already bound" not in all_text
        # Verify no machine-readable extras leak detail/developer keys
        if len(result.result.content) >= 2:
            extras = json.loads(result.result.content[1].text)
            assert "developer_message" not in extras
            assert "detail" not in extras

    @pytest.mark.asyncio
    async def test_in_call_bootstrap_propagates_email_derived_user_id(self, tool_catalog):
        """After bootstrap succeeds, tool_context.user_id is updated from config email
        BEFORE _check_authorization is called."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # First call returns None (pre-bootstrap), second call returns token.
        load_calls = {"n": 0}

        def fake_load() -> str | None:
            load_calls["n"] += 1
            return "oauth-tok" if load_calls["n"] >= 2 else None

        server._load_access_token = Mock(side_effect=fake_load)
        server._load_config_user_id = Mock(return_value="user@example.com")

        observed_user_ids: list[str | None] = []

        async def record_user_id(tool, user_id=None):
            observed_user_ids.append(user_id)
            completed = Mock()
            completed.status = "completed"
            completed.context = Mock(token="t", user_info={})
            return completed

        server._check_authorization = AsyncMock(side_effect=record_user_id)

        # Elicit-capable session.
        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(elicitation={}),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        bootstrap_mock = AsyncMock(return_value=BootstrapResult.completed())
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tool_context = ToolContext()
            tool_context.user_id = "session_fallback_id"
            await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        # By the time _check_authorization was called, user_id had been refreshed.
        # tool_context.user_id was updated AND propagated.
        assert tool_context.user_id == "user@example.com"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls_during_bootstrap_share_one_listener(self, tool_catalog):
        """Two concurrent ``_check_tool_requirements`` calls must pass the SAME slot
        instance to ``bootstrap_login`` (i.e. share one slot/attempt)."""
        from arcade_mcp_server.auth_bootstrap import AttemptSlot, BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        server._load_access_token = Mock(return_value=None)

        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        seen_slots: list[AttemptSlot] = []

        async def fake_bootstrap(*, slot: AttemptSlot, **kwargs):  # noqa: ARG001
            seen_slots.append(slot)
            return BootstrapResult.url_for_fallback("https://cloud.arcade.dev/x")

        with patch("arcade_mcp_server.server.bootstrap_login", side_effect=fake_bootstrap):
            tc1 = ToolContext()
            tc2 = ToolContext()
            await asyncio.gather(
                server._check_tool_requirements(
                    tool_obj,
                    tc1,
                    CallToolRequest(
                        jsonrpc="2.0",
                        id=1,
                        method="tools/call",
                        params={"name": "T.a", "arguments": {}},
                    ),
                    "T.a",
                    session=session,
                ),
                server._check_tool_requirements(
                    tool_obj,
                    tc2,
                    CallToolRequest(
                        jsonrpc="2.0",
                        id=2,
                        method="tools/call",
                        params={"name": "T.a", "arguments": {}},
                    ),
                    "T.a",
                    session=session,
                ),
            )

        assert len(seen_slots) == 2
        assert seen_slots[0] is server._login_slot
        assert seen_slots[1] is server._login_slot

    @pytest.mark.asyncio
    async def test_server_level_fallback_end_to_end_simulation(self, tool_catalog, tmp_path, monkeypatch):
        """First call returns URL fallback; after credentials appear, second call
        hits retry-first and proceeds without invoking bootstrap again."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # _check_authorization succeeds whenever called.
        completed = Mock()
        completed.status = "completed"
        completed.context = Mock(token="t", user_info={})
        server._check_authorization = AsyncMock(return_value=completed)

        # No elicitation capability.
        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        # Call 1 — no creds, bootstrap returns URL.
        url = "https://cloud.arcade.dev/oauth/authorize?xxx"
        bootstrap_mock = AsyncMock(return_value=BootstrapResult.url_for_fallback(url))
        with patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock):
            tc1 = ToolContext()
            result1 = await server._check_tool_requirements(
                tool_obj,
                tc1,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )
        assert isinstance(result1, JSONRPCResponse)
        assert url in result1.result.content[0].text
        bootstrap_mock.assert_called_once()

        # Now write credentials to the working dir.
        self._write_credentials(tmp_path, email="user@example.com", access_token="real-tok")

        # Call 2 — should hit retry-first and NOT call bootstrap.
        bootstrap_mock_2 = AsyncMock(side_effect=AssertionError("bootstrap should not be called"))
        with (
            patch("arcade_mcp_server.server.bootstrap_login", bootstrap_mock_2),
            patch("arcade_mcp_server.server.get_valid_access_token", return_value="real-tok"),
        ):
            tc2 = ToolContext()
            result2 = await server._check_tool_requirements(
                tool_obj,
                tc2,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=2,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        assert result2 is None  # proceeded to authorization
        bootstrap_mock_2.assert_not_called()
        assert server.arcade is not None

    @pytest.mark.asyncio
    async def test_no_stdout_or_stderr_during_bootstrap_path_in_stdio_transport(
        self, tool_catalog, capfd
    ):
        """capfd silence over a successful bootstrap path AND a failure path."""
        from arcade_mcp_server.auth_bootstrap import BootstrapResult
        from arcade_mcp_server.types import ClientCapabilities, InitializeParams

        server = MCPServer(catalog=tool_catalog)
        server.arcade = None

        tool_obj = Mock()
        tool_obj.definition.requirements = ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2", provider_id="test-provider"
            )
        )

        # Successful path
        load_calls = {"n": 0}

        def fake_load() -> str | None:
            load_calls["n"] += 1
            return "oauth-tok" if load_calls["n"] >= 2 else None

        server._load_access_token = Mock(side_effect=fake_load)
        server._load_config_user_id = Mock(return_value="user@example.com")
        completed = Mock()
        completed.status = "completed"
        completed.context = Mock(token="t", user_info={})
        server._check_authorization = AsyncMock(return_value=completed)

        session = Mock()
        session.init_options = {"transport_type": "stdio"}
        session.session_id = "sess"
        session.elicit = AsyncMock()
        session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(elicitation={}),
            clientInfo={"name": "c", "version": "1"},
        )
        from arcade_mcp_server.session import ServerSession

        session.check_client_capability = ServerSession.check_client_capability.__get__(
            session, type(session)
        )

        with patch(
            "arcade_mcp_server.server.bootstrap_login",
            AsyncMock(return_value=BootstrapResult.completed()),
        ):
            tool_context = ToolContext()
            await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=1,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=session,
            )

        # Failure path
        server._load_access_token = Mock(return_value=None)
        no_elicit_session = Mock()
        no_elicit_session.init_options = {"transport_type": "stdio"}
        no_elicit_session.session_id = "sess2"
        no_elicit_session.elicit = AsyncMock()
        no_elicit_session.client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "c", "version": "1"},
        )
        no_elicit_session.check_client_capability = ServerSession.check_client_capability.__get__(
            no_elicit_session, type(no_elicit_session)
        )
        with patch(
            "arcade_mcp_server.server.bootstrap_login",
            AsyncMock(return_value=BootstrapResult.failed(reason="port_in_use", detail="x")),
        ):
            tool_context = ToolContext()
            await server._check_tool_requirements(
                tool_obj,
                tool_context,
                CallToolRequest(
                    jsonrpc="2.0",
                    id=2,
                    method="tools/call",
                    params={"name": "T.a", "arguments": {}},
                ),
                "T.a",
                session=no_elicit_session,
            )

        captured = capfd.readouterr()
        assert captured.out == ""
        assert captured.err == ""

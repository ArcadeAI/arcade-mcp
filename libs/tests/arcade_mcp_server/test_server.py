"""Tests for MCP Server implementation."""

import asyncio
import contextlib
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_core.errors import ToolRuntimeError
from arcade_core.schema import (
    ToolAuthRequirement,
    ToolContext,
    ToolRequirements,
    ToolSecretRequirement,
)
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
            version="1.0.0",
            settings=mcp_settings,
        )

        assert server.name == "Test Server"
        assert server.version == "1.0.0"
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
        assert "authorization" in response.result.structuredContent["message"]

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
        assert (
            "requires authorization but no Arcade API key is configured"
            in response.result.structuredContent["message"]
        )
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
        assert "not allowed before initialization" in response.error["message"]

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
        assert (
            "requires authorization but no Arcade API key is configured"
            in result.result.structuredContent["message"]
        )
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
        assert "requires authorization" in result.result.structuredContent["message"]

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
        assert "authorization error" in result.result.structuredContent["message"]
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
        assert "requires the following secrets" in result.result.structuredContent["message"]
        assert "API_KEY, DATABASE_URL" in result.result.structuredContent["message"]
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

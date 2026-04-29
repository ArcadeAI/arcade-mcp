"""Tests for MCP ServerSession implementation."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_mcp_server.context import Context
from arcade_mcp_server.session import InitializationState, ServerSession
from arcade_mcp_server.types import (
    ClientCapabilities,
    InitializeParams,
    JSONRPCResponse,
    LoggingLevel,
)


class TestServerSession:
    """Test ServerSession class."""

    def test_session_initialization(self, mcp_server, mock_read_stream, mock_write_stream):
        """Test session initialization."""
        session = ServerSession(
            server=mcp_server,
            read_stream=mock_read_stream,
            write_stream=mock_write_stream,
            init_options={"test": "option"},
        )

        assert session.server == mcp_server
        assert session.read_stream == mock_read_stream
        assert session.write_stream == mock_write_stream
        assert session.init_options == {"test": "option"}
        assert session.initialization_state == InitializationState.NOT_INITIALIZED
        assert len(session.session_id) > 0  # Should have generated a session ID

    def test_initialization_state_transitions(self, server_session):
        """Test initialization state transitions."""
        # Initial state
        assert server_session.initialization_state == InitializationState.NOT_INITIALIZED

        # Set client params (happens during initialize)
        server_session.set_client_params({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test", "version": "1.0"},
        })

        assert server_session.initialization_state == InitializationState.INITIALIZING

        # Mark as initialized
        server_session.mark_initialized()

        assert server_session.initialization_state == InitializationState.INITIALIZED

    @pytest.mark.asyncio
    async def test_message_processing(self, server_session):
        """Test processing messages."""
        # Mock server handle_message
        server_session.server.handle_message = AsyncMock(
            return_value=JSONRPCResponse(jsonrpc="2.0", id=1, result={"status": "ok"})
        )

        # Process a message
        await server_session._process_message('{"jsonrpc":"2.0","id":1,"method":"ping"}')

        # Verify server was called
        server_session.server.handle_message.assert_called_once()

        # Verify response was sent
        server_session.write_stream.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_sending(self, server_session):
        """Test sending notifications."""
        # Send a tool list changed notification
        await server_session.send_tool_list_changed()

        # Verify notification was sent
        server_session.write_stream.send.assert_called_once()

        # Check the sent notification
        sent_data = server_session.write_stream.send.call_args[0][0]
        sent_json = json.loads(sent_data.strip())

        assert sent_json["jsonrpc"] == "2.0"
        assert sent_json["method"] == "notifications/tools/list_changed"
        assert "id" not in sent_json  # Notifications don't have IDs

    @pytest.mark.asyncio
    async def test_multiple_notifications(self, server_session):
        """Test sending multiple notifications."""
        # Send multiple notifications
        await server_session.send_tool_list_changed()
        await server_session.send_resource_list_changed()
        await server_session.send_prompt_list_changed()

        # All notifications should be sent immediately
        assert server_session.write_stream.send.call_count == 3

        # Check notification types
        calls = server_session.write_stream.send.call_args_list
        methods = []
        for call in calls:
            data = json.loads(call[0][0].strip())
            methods.append(data["method"])

        assert "notifications/tools/list_changed" in methods
        assert "notifications/resources/list_changed" in methods
        assert "notifications/prompts/list_changed" in methods

    @pytest.mark.asyncio
    async def test_log_message_sending(self, server_session):
        """Test sending log messages."""
        # Send log messages at different levels
        await server_session.send_log_message(
            LoggingLevel.INFO, "Test info message", logger="test.logger"
        )
        await server_session.send_log_message(LoggingLevel.ERROR, "Test error message")

        # Verify log messages were sent
        assert server_session.write_stream.send.call_count == 2

        # Check first log message
        first_call = server_session.write_stream.send.call_args_list[0]
        first_data = json.loads(first_call[0][0].strip())
        assert first_data["method"] == "notifications/message"
        assert first_data["params"]["level"] == "info"
        assert first_data["params"]["data"] == "Test info message"
        assert first_data["params"]["logger"] == "test.logger"

    @pytest.mark.asyncio
    async def test_progress_notification(self, server_session):
        """Test progress notification sending."""
        # Send progress notification
        await server_session.send_progress_notification(
            progress_token="task-123", progress=50, total=100, message="Processing..."
        )

        # Verify notification was sent
        server_session.write_stream.send.assert_called_once()

        # Check progress notification content
        sent_data = json.loads(server_session.write_stream.send.call_args[0][0].strip())
        assert sent_data["method"] == "notifications/progress"
        assert sent_data["params"]["progressToken"] == "task-123"
        assert sent_data["params"]["progress"] == 50
        assert sent_data["params"]["total"] == 100
        assert sent_data["params"]["message"] == "Processing..."

    @pytest.mark.asyncio
    async def test_request_context_management(self, server_session):
        """Test request context creation and cleanup."""
        # Create context
        context = await server_session.create_request_context()

        assert isinstance(context, Context)
        assert context._session == server_session
        assert server_session._current_context == context

        # Cleanup context
        await server_session.cleanup_request_context(context)

        # Context should be cleaned up
        assert server_session._current_context is None

    @pytest.mark.asyncio
    async def test_server_initiated_request(self, server_session):
        """Test server-initiated requests to client."""
        # Test create_message request
        messages = [{"role": "user", "content": {"type": "text", "text": "Hello"}}]

        # Mock the request manager response
        mock_result = {
            "role": "assistant",
            "content": {"type": "text", "text": "Generated response"},
            "model": "test-model",
        }
        server_session._request_manager = Mock()
        server_session._request_manager.send_request = AsyncMock(return_value=mock_result)

        # Send sampling request
        await server_session.create_message(
            messages=messages, max_tokens=100, system_prompt="Be helpful"
        )

        # Verify request was sent
        server_session._request_manager.send_request.assert_called_once_with(
            "sampling/createMessage",
            {"messages": messages, "maxTokens": 100, "systemPrompt": "Be helpful"},
            60.0,
        )

    @pytest.mark.asyncio
    async def test_list_roots_request(self, server_session):
        """Test list roots server-initiated request."""
        # Mock request manager
        mock_roots = {"roots": [{"uri": "file:///home", "name": "Home"}]}
        server_session._request_manager = Mock()
        server_session._request_manager.send_request = AsyncMock(return_value=mock_roots)

        # Send list roots request
        await server_session.list_roots(timeout=30.0)

        # Verify request was sent correctly
        server_session._request_manager.send_request.assert_called_once_with(
            "roots/list", None, 30.0
        )

    @pytest.mark.asyncio
    async def test_request_without_manager(self, server_session):
        """Test error when sending request without request manager."""
        # Clear request manager
        server_session._request_manager = None

        # Should raise SessionError
        from arcade_mcp_server.exceptions import SessionError

        with pytest.raises(SessionError, match="Cannot send requests without request manager"):
            await server_session.create_message([{"role": "user", "content": "test"}], 100)

    @pytest.mark.asyncio
    async def test_session_run_loop(self, mcp_server, mock_read_stream, mock_write_stream):
        """Test the main session run loop."""
        # Create session
        session = ServerSession(
            server=mcp_server,
            read_stream=mock_read_stream,
            write_stream=mock_write_stream,
        )

        # Mock server message handling
        mcp_server.handle_message = AsyncMock(
            return_value=JSONRPCResponse(jsonrpc="2.0", id=1, result={})
        )

        # Mock messages to read
        messages = [
            '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}',
            '{"jsonrpc": "2.0", "method": "notifications/initialized"}',
            '{"jsonrpc": "2.0", "id": 2, "method": "ping"}',
        ]

        # Simple approach: make read_stream an async generator directly
        async def async_messages():
            for msg in messages:
                yield msg

        # Replace the read_stream with our generator
        session.read_stream = async_messages()

        # Run session (it will complete when messages are exhausted)
        await session.run()

        # Verify messages were processed
        assert mcp_server.handle_message.call_count == 3
        assert session.write_stream.send.call_count >= 2  # At least 2 responses

    @pytest.mark.asyncio
    async def test_session_error_handling(self, server_session):
        """Test error handling in session."""
        # Mock server to raise error
        server_session.server.handle_message = AsyncMock(side_effect=Exception("Test error"))

        # Process message - should handle error gracefully
        await server_session._process_message('{"jsonrpc": "2.0", "id": 1, "method": "test"}')

        # Error response should be sent
        server_session.write_stream.send.assert_called()

        sent_data = server_session.write_stream.send.call_args[0][0]
        sent_json = json.loads(sent_data.strip())

        assert "error" in sent_json
        assert sent_json["error"]["code"] == -32603
        assert "Test error" in sent_json["error"]["message"]

    @pytest.mark.asyncio
    async def test_client_capability_checking(self, server_session):
        """Test client capability checking."""
        # Set client params with specific capabilities
        client_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(tools={"listChanged": True}, sampling={}),
            clientInfo={"name": "test-client", "version": "1.0"},
        )

        server_session.set_client_params(client_params)

        # Check capabilities - client has tools and sampling
        # An empty capability requirement should pass
        assert server_session.check_client_capability(ClientCapabilities())

        # Checking for tools capability should pass (client has it)
        assert server_session.check_client_capability(ClientCapabilities(tools={}))

        # Checking for sampling capability should pass (client has it)
        assert server_session.check_client_capability(ClientCapabilities(sampling={}))

        # Now test with a client that has no capabilities
        no_cap_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "test-client", "version": "1.0"},
        )

        server_session.set_client_params(no_cap_params)

        # Empty capability check should still pass (trivially true)
        assert server_session.check_client_capability(ClientCapabilities())

    @pytest.mark.asyncio
    async def test_check_client_capability_returns_false_when_client_lacks_requested_capability(
        self, server_session
    ):
        """Presence-based semantics: client without declared capabilities does not satisfy
        a request that explicitly mentions tools/sampling/etc."""
        # Client declares NO capabilities at all.
        no_cap_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(no_cap_params)

        # Requesting tools={} explicitly asks for the tools capability — client lacks it.
        assert not server_session.check_client_capability(ClientCapabilities(tools={}))
        # Same for sampling.
        assert not server_session.check_client_capability(ClientCapabilities(sampling={}))

    @pytest.mark.asyncio
    async def test_check_client_capability_returns_false_when_client_lacks_elicitation(
        self, server_session
    ):
        """Client without elicitation does not satisfy an elicitation request."""
        no_cap_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(no_cap_params)

        assert not server_session.check_client_capability(ClientCapabilities(elicitation={}))

    @pytest.mark.asyncio
    async def test_check_client_capability_returns_true_when_client_declares_elicitation_empty_dict(
        self, server_session
    ):
        """Empty dict {} on the client side counts as 'capability supported' (it's the wire form)."""
        params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(elicitation={}),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(params)

        assert server_session.check_client_capability(ClientCapabilities(elicitation={}))

    @pytest.mark.asyncio
    async def test_check_client_capability_returns_false_when_client_lacks_sampling(
        self, server_session
    ):
        """Client lacking sampling cannot satisfy a sampling request."""
        no_cap_params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(no_cap_params)

        assert not server_session.check_client_capability(ClientCapabilities(sampling={}))

    @pytest.mark.asyncio
    async def test_check_client_capability_returns_true_when_client_declares_sampling_empty_dict(
        self, server_session
    ):
        """Empty dict {} for sampling on the client side counts as supported."""
        params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(sampling={}),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(params)

        assert server_session.check_client_capability(ClientCapabilities(sampling={}))

    @pytest.mark.asyncio
    async def test_check_client_capability_handles_extras_for_tools_resources_prompts_logging(
        self, server_session
    ):
        """Extras-path capabilities (tools/resources/prompts/logging) follow the same rules."""
        # Client declares tools and resources via extras, but NOT prompts/logging.
        params = InitializeParams(
            protocolVersion="2024-11-05",
            capabilities=ClientCapabilities(tools={}, resources={}),
            clientInfo={"name": "test-client", "version": "1.0"},
        )
        server_session.set_client_params(params)

        # Requesting tools (declared) → True
        assert server_session.check_client_capability(ClientCapabilities(tools={}))
        # Requesting resources (declared) → True
        assert server_session.check_client_capability(ClientCapabilities(resources={}))
        # Requesting prompts (NOT declared) → False
        assert not server_session.check_client_capability(ClientCapabilities(prompts={}))
        # Requesting logging (NOT declared) → False
        assert not server_session.check_client_capability(ClientCapabilities(logging={}))

    @pytest.mark.asyncio
    async def test_parse_error_handling(self, server_session):
        """Test handling of JSON parse errors."""
        # Send invalid JSON
        await server_session._process_message("invalid json {")

        # Error response should be sent
        server_session.write_stream.send.assert_called_once()

        sent_data = json.loads(server_session.write_stream.send.call_args[0][0].strip())
        assert "error" in sent_data
        assert sent_data["error"]["code"] == -32700  # Parse error
        assert sent_data["id"] == "null"

    def test_client_info_extraction(self, server_session):
        """Test extracting client information."""
        client_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": True}, "sampling": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        }

        server_session.set_client_params(client_params)

        assert server_session.client_params == client_params
        assert server_session.client_params["clientInfo"]["name"] == "test-client"
        assert server_session.initialization_state == InitializationState.INITIALIZING

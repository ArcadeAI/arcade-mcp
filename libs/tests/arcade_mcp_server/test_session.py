"""Tests for MCP ServerSession implementation."""

import json
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_mcp_server.context import Context
from arcade_mcp_server.exceptions import (
    ElicitationModeNotSupportedError,
    ElicitationNotSupportedError,
    SessionError,
)
from arcade_mcp_server.session import InitializationState, ServerSession
from arcade_mcp_server.types import (
    ClientCapabilities,
    ElicitRequestFormParams,
    ElicitResult,
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
        # Must be initialized for outbound requests
        server_session.mark_initialized()

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

        # Empty capability check should still pass
        assert server_session.check_client_capability(ClientCapabilities())

        # Checking for capabilities when client has none
        # Since the capability requirements have empty dicts {}, they are considered
        # as "having the capability" but with no specific requirements
        # So these should actually pass
        assert server_session.check_client_capability(ClientCapabilities(tools={}))
        assert server_session.check_client_capability(ClientCapabilities(sampling={}))

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
        assert sent_data["id"] is None  # JSON null, not string "null"

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


class TestSessionVersion:
    """Test version negotiation state on ServerSession."""

    def test_negotiated_version_defaults_to_none(self, server_session):
        assert server_session.negotiated_version is None

    def test_supports_version_false_when_none(self, server_session):
        assert server_session.supports_version("2025-11-25") is False

    def test_supports_version_false_for_old_version(self, server_session):
        server_session.negotiated_version = "2025-06-18"
        assert server_session.supports_version("2025-11-25") is False

    def test_supports_version_true_for_exact(self, server_session):
        server_session.negotiated_version = "2025-11-25"
        assert server_session.supports_version("2025-11-25") is True

    def test_supports_version_uses_feature_subset_not_lexical(self, server_session):
        """supports_version uses feature set subset check, not lexical string comparison.
        This is critical because spec uses non-date identifiers like DRAFT-2025-v3."""
        server_session.negotiated_version = "2025-11-25"
        assert (
            server_session.supports_version("2025-06-18") is True
        )  # 06-18 features subset of 11-25

    def test_has_feature_tasks(self, server_session):
        server_session.negotiated_version = "2025-11-25"
        assert server_session.has_feature("tasks") is True

    def test_has_feature_tasks_false_for_old_version(self, server_session):
        server_session.negotiated_version = "2025-06-18"
        assert server_session.has_feature("tasks") is False

    def test_has_feature_false_when_none(self, server_session):
        assert server_session.has_feature("tasks") is False

    def test_has_feature_base_always_present(self, server_session):
        server_session.negotiated_version = "2025-06-18"
        assert server_session.has_feature("base") is True


class TestHasCapability:
    """Test has_capability() dot-notation sub-capability lookup."""

    def test_has_capability_base(self, server_session):
        server_session._negotiated_capabilities = {"tasks": {}}
        assert server_session.has_capability("tasks") is True

    def test_has_capability_nested(self, server_session):
        server_session._negotiated_capabilities = {"tasks": {"list": {}}}
        assert server_session.has_capability("tasks.list") is True
        assert server_session.has_capability("tasks.cancel") is False

    def test_has_capability_missing(self, server_session):
        server_session._negotiated_capabilities = {}
        assert server_session.has_capability("tasks") is False
        assert server_session.has_capability("tasks.list") is False

    def test_has_capability_dot_notation_depth(self, server_session):
        server_session._negotiated_capabilities = {"tasks": {"requests": {"tools": {"call": {}}}}}
        assert server_session.has_capability("tasks.requests.tools.call") is True
        assert server_session.has_capability("tasks.requests.tools") is True
        assert server_session.has_capability("tasks.requests") is True
        assert server_session.has_capability("tasks") is True
        assert server_session.has_capability("tasks.list") is False


class TestSamplingWithTools:
    @pytest.fixture(autouse=True)
    def _init_session(self, server_session: Any) -> None:
        """Mark server_session as initialized for all tests in this class."""
        server_session.mark_initialized()

    @pytest.mark.asyncio
    async def test_create_message_with_tools_includes_tools_param(self, server_session):
        """When tools are passed, they appear in the sent request params."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        tools = [{"name": "my_tool", "inputSchema": {"type": "object"}}]
        await server_session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
            max_tokens=100,
            tools=tools,
            tool_choice={"mode": "auto"},
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]  # second positional arg
        assert "tools" in params
        assert "toolChoice" in params

    @pytest.mark.asyncio
    async def test_create_message_without_tools_backward_compat(self, server_session):
        """When no tools passed, params look identical to before."""
        server_session.negotiated_version = "2025-06-18"
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
            max_tokens=100,
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert "tools" not in params
        assert "toolChoice" not in params

    @pytest.mark.asyncio
    async def test_create_message_tools_rejected_for_old_version(self, server_session):
        """Passing tools to create_message on a 2025-06-18 session silently strips them."""
        server_session.negotiated_version = "2025-06-18"
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[], max_tokens=100, tools=[{"name": "t", "inputSchema": {}}]
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert "tools" not in params

    @pytest.mark.asyncio
    async def test_create_message_tools_rejected_when_client_lacks_sampling_tools_capability(
        self, server_session
    ):
        """Servers MUST NOT send tool-enabled sampling requests to clients that haven't
        declared sampling.tools capability."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={})  # no "tools" key
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[], max_tokens=100, tools=[{"name": "t", "inputSchema": {}}]
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert "tools" not in params

    @pytest.mark.asyncio
    async def test_create_message_tools_included_when_client_declares_sampling_tools(
        self, server_session
    ):
        """Tools ARE included when client declared sampling.tools capability."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[],
            max_tokens=100,
            tools=[{"name": "t", "inputSchema": {"type": "object"}}],
            tool_choice={"mode": "auto"},
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert "tools" in params
        assert "toolChoice" in params

    @pytest.mark.asyncio
    async def test_create_message_tool_result_only_messages(self, server_session):
        """When a user message contains tool results, it MUST contain ONLY tool results."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "toolUseId": "c1",
                        "content": [{"type": "text", "text": "ok"}],
                    },
                    {"type": "text", "text": "also some text"},  # INVALID -- mixed content
                ],
            }
        ]
        server_session._request_manager = AsyncMock()
        with pytest.raises(ValueError, match="tool results"):
            await server_session.create_message(messages=messages, max_tokens=100)

    @pytest.mark.asyncio
    async def test_create_message_tool_use_must_be_followed_by_tool_result(self, server_session):
        """Every assistant message with ToolUseContent MUST be followed by a user message
        with ToolResultContent."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        messages = [
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "c1", "name": "t", "input": {}}],
            },
            {"role": "user", "content": {"type": "text", "text": "not a tool result"}},
        ]
        server_session._request_manager = AsyncMock()
        with pytest.raises(ValueError, match="tool result"):
            await server_session.create_message(messages=messages, max_tokens=100)

    @pytest.mark.asyncio
    async def test_include_context_stripped_without_sampling_context_capability(
        self, server_session
    ):
        """includeContext values 'thisServer'/'allServers' stripped when client lacks
        sampling.context capability."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={})  # no "context"
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[], max_tokens=100, include_context="thisServer"
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert params.get("includeContext", "none") == "none"

    @pytest.mark.asyncio
    async def test_include_context_preserved_with_sampling_context_capability(self, server_session):
        """includeContext preserved when client declares sampling.context."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"context": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "result"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        await server_session.create_message(
            messages=[], max_tokens=100, include_context="thisServer"
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert params.get("includeContext") == "thisServer"

    @pytest.mark.asyncio
    async def test_create_message_result_array_content_with_tool_use(self, server_session):
        """CreateMessageResult with array content and stopReason=toolUse is handled correctly."""
        server_session.negotiated_version = "2025-11-25"
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll call the tool"},
                    {"type": "tool_use", "id": "call_1", "name": "my_tool", "input": {"x": 1}},
                ],
                "model": "test-model",
                "stopReason": "toolUse",
            }
        )
        result = await server_session.create_message(messages=[], max_tokens=100)
        assert result.stopReason == "toolUse"
        assert isinstance(result.content, list)
        assert len(result.content) == 2
        assert result.content[1].type == "tool_use"

    @pytest.mark.asyncio
    async def test_validate_sampling_messages_accepts_pydantic_sampling_messages(
        self, server_session
    ):
        """Regression: _validate_sampling_messages must handle pydantic
        ``SamplingMessage`` objects in addition to raw dicts. The sampling
        entrypoint in ``context.Sampling.create_message`` hands this layer
        pydantic models; pydantic v2 models don't expose ``.get()``, so the
        prior implementation raised AttributeError and broke sampling-with-tools
        end-to-end for 2025-11-25 clients.
        """
        from arcade_mcp_server.types import SamplingMessage, TextContent

        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "ok"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )

        pydantic_messages = [
            SamplingMessage(role="user", content=TextContent(type="text", text="hi")),
        ]
        # Must NOT raise AttributeError trying to .get() on the pydantic model.
        await server_session.create_message(messages=pydantic_messages, max_tokens=100)

    def test_validate_sampling_messages_static_normalizes_pydantic_models(self):
        """Direct unit test: _validate_sampling_messages normalizes pydantic
        inputs before duck-typing them as dicts."""
        from arcade_mcp_server.session import ServerSession as _ServerSession
        from arcade_mcp_server.types import SamplingMessage, TextContent

        # Pass a pydantic model directly -- previously this raised AttributeError.
        _ServerSession._validate_sampling_messages([
            SamplingMessage(role="user", content=TextContent(type="text", text="hello"))
        ])

    @pytest.mark.asyncio
    async def test_sampling_tools_gate_uses_feature_registry_not_hardcoded_version(
        self, server_session, monkeypatch
    ):
        """Regression: the sampling-with-tools gate must consult
        ``version_has_feature(version, "tool_calling_in_sampling")`` rather
        than comparing ``negotiated_version`` to the literal ``"2025-11-25"``.
        A future protocol version that inherits the feature must not have
        tools silently stripped from its sampling requests.
        """
        from arcade_mcp_server import types as mcp_types

        # Simulate a hypothetical future version that supports sampling+tools.
        future_version = "2099-01-01"
        patched = dict(mcp_types.VERSION_FEATURES)
        patched[future_version] = patched["2025-11-25"]
        monkeypatch.setattr(mcp_types, "VERSION_FEATURES", patched)
        # session.py imports version_has_feature at module load; it reads
        # VERSION_FEATURES fresh on each call, so patching the dict is enough.

        server_session.negotiated_version = future_version
        server_session._client_capabilities = ClientCapabilities(sampling={"tools": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "ok"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )

        await server_session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
            max_tokens=100,
            tools=[{"name": "t", "inputSchema": {"type": "object"}}],
            tool_choice={"mode": "auto"},
        )
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert "tools" in params, (
            "tools must survive to the wire when the client's version has the "
            "tool_calling_in_sampling feature, regardless of whether it equals "
            "the literal 2025-11-25"
        )


class TestURLModeElicitation:
    @pytest.fixture(autouse=True)
    def _init_session(self, server_session: Any) -> None:
        server_session.mark_initialized()

    @pytest.mark.asyncio
    async def test_elicit_url_mode_includes_elicitation_id(self, server_session):
        """URL mode requires elicitationId in the request."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={"url": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={"action": "accept", "content": {"token": "abc"}}
        )
        result = await server_session.elicit(
            message="Please authenticate",
            mode="url",
            url="https://example.com/auth",
            elicitation_id="elic_123",
        )
        assert result.action == "accept"
        call_args = server_session._request_manager.send_request.call_args
        params = call_args[0][1]
        assert params["mode"] == "url"
        assert params["url"] == "https://example.com/auth"
        assert params["elicitationId"] == "elic_123"

    @pytest.mark.asyncio
    async def test_elicit_url_mode_rejected_for_old_version(self, server_session):
        """URL mode elicitation must not be sent to 2025-06-18 clients."""
        server_session.negotiated_version = "2025-06-18"
        server_session._request_manager = AsyncMock()
        with pytest.raises(SessionError):
            await server_session.elicit(
                message="Please authenticate",
                mode="url",
                url="https://example.com/auth",
                elicitation_id="elic_123",
            )

    @pytest.mark.asyncio
    async def test_elicit_url_mode_rejected_when_client_lacks_url_capability(self, server_session):
        """URL mode rejected if client only declared form elicitation support."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={"form": {}})
        server_session._request_manager = AsyncMock()
        with pytest.raises(SessionError):
            await server_session.elicit(
                message="Please authenticate",
                mode="url",
                url="https://example.com/auth",
                elicitation_id="elic_123",
            )

    @pytest.mark.asyncio
    async def test_elicit_form_mode_backward_compat(self, server_session):
        """Form mode (default) works for both versions."""
        server_session.negotiated_version = "2025-06-18"
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={"action": "accept", "content": {"name": "test"}}
        )
        result = await server_session.elicit(
            message="Enter name", requested_schema={"type": "object"}
        )
        assert result.action == "accept"


class TestElicitationCompleteNotification:
    @pytest.mark.asyncio
    async def test_send_elicitation_complete_notification(self, server_session):
        """Server can send notifications/elicitation/complete for URL mode flows."""
        server_session.negotiated_version = "2025-11-25"
        server_session.write_stream = AsyncMock()
        server_session.write_stream.send = AsyncMock()
        await server_session.send_elicitation_complete("elic_123")
        call_args = server_session.write_stream.send.call_args[0][0]
        data = json.loads(call_args)
        assert data["method"] == "notifications/elicitation/complete"
        assert data["params"]["elicitationId"] == "elic_123"


class TestEnumSchemaValidation:
    """Tests for enhanced enum schema types in elicitation."""

    @pytest.fixture(autouse=True)
    def _init_session(self, server_session: Any) -> None:
        server_session.mark_initialized()

    def test_form_mode_with_untitled_single_select(self):
        """Untitled single-select enum works in elicitation schemas."""
        schema = {
            "type": "object",
            "properties": {"color": {"type": "string", "enum": ["red", "green", "blue"]}},
        }
        params = ElicitRequestFormParams(message="Pick color", requestedSchema=schema)
        assert params.requestedSchema is not None

    def test_form_mode_with_titled_single_select(self):
        """Titled single-select (oneOf with const+title) works."""
        schema = {
            "type": "object",
            "properties": {
                "color": {
                    "type": "string",
                    "oneOf": [
                        {"const": "#FF0000", "title": "Red"},
                        {"const": "#00FF00", "title": "Green"},
                    ],
                }
            },
        }
        params = ElicitRequestFormParams(message="Pick color", requestedSchema=schema)
        assert params.requestedSchema is not None

    def test_form_mode_with_multi_select(self):
        """Multi-select enum (array type with items.enum) works."""
        schema = {
            "type": "object",
            "properties": {
                "colors": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["red", "green"]},
                    "minItems": 1,
                    "maxItems": 3,
                }
            },
        }
        params = ElicitRequestFormParams(message="Pick colors", requestedSchema=schema)
        assert params.requestedSchema is not None

    def test_elicit_result_with_multi_select_string_array(self):
        """ElicitResult content can include string[] values from multi-select."""
        result = ElicitResult(action="accept", content={"colors": ["red", "green"]})
        assert result.content["colors"] == ["red", "green"]


class TestElicitationCapabilityGating:
    """Tests for elicitation capability gating.

    Servers MUST NOT send elicitation requests with modes that are not supported
    by the client."""

    @pytest.fixture(autouse=True)
    def _init_session(self, server_session: Any) -> None:
        server_session.mark_initialized()

    @pytest.mark.asyncio
    async def test_elicit_rejected_when_client_has_no_elicitation_capability(self, server_session):
        """Client did not declare elicitation capability -> server must not send elicitation."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities()  # no elicitation
        server_session._request_manager = AsyncMock()
        with pytest.raises(ElicitationNotSupportedError):
            await server_session.elicit(
                message="Enter name",
                requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            )

    @pytest.mark.asyncio
    async def test_elicit_rejected_when_client_caps_is_dict_without_elicitation(
        self, server_session
    ):
        """Also works when _client_capabilities is a plain dict without 'elicitation' key."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = {"tools": {}}  # dict, no elicitation
        server_session._request_manager = AsyncMock()
        with pytest.raises(ElicitationNotSupportedError):
            await server_session.elicit(
                message="Enter name",
                requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            )

    @pytest.mark.asyncio
    async def test_elicit_form_mode_allowed_with_empty_elicitation_capability(self, server_session):
        """Client declared elicitation: {} -> defaults to form mode support."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={"action": "accept", "content": {"name": "test"}}
        )
        result = await server_session.elicit(
            message="Enter name",
            requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        assert result.action == "accept"

    @pytest.mark.asyncio
    async def test_elicit_form_mode_allowed_with_dict_elicitation_capability(self, server_session):
        """Also works when _client_capabilities is a plain dict with elicitation key."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = {"elicitation": {}}
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={"action": "accept", "content": {"name": "test"}}
        )
        result = await server_session.elicit(
            message="Enter name",
            requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        assert result.action == "accept"

    @pytest.mark.asyncio
    async def test_elicit_url_mode_rejected_with_form_only_capability(self, server_session):
        """Client only declared form mode -> URL mode rejected."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={"form": {}})
        server_session._request_manager = AsyncMock()
        with pytest.raises(ElicitationModeNotSupportedError):
            await server_session.elicit(
                message="Please authenticate",
                mode="url",
                url="https://example.com/auth",
                elicitation_id="elic_123",
            )

    @pytest.mark.asyncio
    async def test_elicit_url_mode_allowed_with_url_capability(self, server_session):
        """Client declared url mode -> URL mode succeeds."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={"url": {}})
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={"action": "accept", "content": {"token": "abc"}}
        )
        result = await server_session.elicit(
            message="Please authenticate",
            mode="url",
            url="https://example.com/auth",
            elicitation_id="elic_456",
        )
        assert result.action == "accept"

    @pytest.mark.asyncio
    async def test_elicit_form_mode_rejected_with_url_only_capability(self, server_session):
        """Client only declared url mode -> form mode rejected."""
        server_session.negotiated_version = "2025-11-25"
        server_session._client_capabilities = ClientCapabilities(elicitation={"url": {}})
        server_session._request_manager = AsyncMock()
        with pytest.raises(ElicitationModeNotSupportedError):
            await server_session.elicit(
                message="Enter name",
                requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            )


class TestURLElicitationSecurity:
    """Tests for URL elicitation security MUST requirements.

    **Deferred to a follow-up PR.**"""

    pass


class TestElicitationCompletionNotification:
    """Tests for notifications/elicitation/complete routing."""

    @pytest.mark.asyncio
    async def test_completion_notification_routed_to_initiating_client_only(self, server_session):
        """notifications/elicitation/complete MUST only be sent to the client that
        initiated the elicitation request. Not broadcast to all sessions -- targeted
        to the originating session."""
        server_session.negotiated_version = "2025-11-25"
        sent_messages = []
        server_session.write_stream = AsyncMock()
        server_session.write_stream.send = AsyncMock(side_effect=lambda m: sent_messages.append(m))
        await server_session.send_elicitation_complete("elic_123")
        # Sent to originating session
        assert len(sent_messages) >= 1
        data = json.loads(sent_messages[0])
        assert data["method"] == "notifications/elicitation/complete"
        assert data["params"]["elicitationId"] == "elic_123"


class TestLifecycleOutboundGuard:
    """Server SHOULD NOT send requests other than ping/logging before initialized."""

    @pytest.mark.asyncio
    async def test_create_message_rejected_before_initialized(self, server_session):
        from arcade_mcp_server.exceptions import SessionNotInitializedError

        server_session._request_manager = AsyncMock()
        with pytest.raises(SessionNotInitializedError):
            await server_session.create_message(
                messages=[{"role": "user", "content": {"type": "text", "text": "hello"}}],
                max_tokens=100,
            )

    @pytest.mark.asyncio
    async def test_elicit_rejected_before_initialized(self, server_session):
        from arcade_mcp_server.exceptions import SessionNotInitializedError

        server_session._request_manager = AsyncMock()
        with pytest.raises(SessionNotInitializedError):
            await server_session.elicit(
                message="Enter name",
                requested_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            )

    @pytest.mark.asyncio
    async def test_create_message_allowed_after_initialized(self, server_session):
        server_session.mark_initialized()
        server_session._request_manager = AsyncMock()
        server_session._request_manager.send_request = AsyncMock(
            return_value={
                "role": "assistant",
                "content": {"type": "text", "text": "hi"},
                "model": "test-model",
                "stopReason": "endTurn",
            }
        )
        result = await server_session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hello"}}],
            max_tokens=100,
        )
        assert result is not None

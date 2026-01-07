from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_mcp_server.transports.http_streamable import (
    MCP_SESSION_ID_HEADER,
    HTTPStreamableTransport,
)


class TestHTTPStreamableTransport:
    """Test HTTPStreamableTransport request handling."""

    @pytest.mark.asyncio
    async def test_handle_request_method_routing(self, mcp_server):
        """Test that handle_request routes to correct method handlers."""
        transport = HTTPStreamableTransport(
            mcp_session_id="test-session", is_json_response_enabled=True
        )

        # Test POST routing
        scope = {"type": "http", "method": "POST"}
        receive = AsyncMock()
        send = AsyncMock()

        with patch.object(transport, "_handle_post_request") as mock_post:
            await transport.handle_request(scope, receive, send)
            mock_post.assert_called_once()

        # Test GET routing
        scope = {"type": "http", "method": "GET"}
        with patch.object(transport, "_handle_get_request") as mock_get:
            await transport.handle_request(scope, receive, send)
            mock_get.assert_called_once()

        # Test DELETE routing
        scope = {"type": "http", "method": "DELETE"}
        with patch.object(transport, "_handle_delete_request") as mock_delete:
            await transport.handle_request(scope, receive, send)
            mock_delete.assert_called_once()

        # Test unsupported method
        scope = {"type": "http", "method": "PUT"}
        with patch.object(transport, "_handle_unsupported_request") as mock_unsupported:
            await transport.handle_request(scope, receive, send)
            mock_unsupported.assert_called_once()


class TestHTTPStreamableTransportPost:
    """Test POST request handling."""

    # @pytest.mark.asyncio
    # async def test_handle_post_request_valid_json_mode(self, mcp_server):
    #     """Test successful POST request handling in JSON response mode."""
    #     transport = HTTPStreamableTransport(
    #         mcp_session_id="test-session", is_json_response_enabled=True
    #     )

    #     # Mock the read stream writer
    #     mock_writer = AsyncMock()
    #     transport._read_stream_writer = mock_writer

    #     # Create valid JSON-RPC request
    #     json_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    #     body = json.dumps(json_request).encode()

    #     scope = {
    #         "type": "http",
    #         "method": "POST",
    #         "headers": [
    #             (b"content-type", b"application/json"),
    #             (b"accept", b"application/json"),
    #             (MCP_SESSION_ID_HEADER.lower().encode(), b"test-session"),
    #         ],
    #     }

    #     # Mock request body
    #     receive = AsyncMock()
    #     receive.return_value = {"type": "http.request", "body": body}
    #     send = AsyncMock()

    #     # Mock request streams for JSON mode
    #     transport._request_streams = {}

    #     # Create a mock stream that will return a response
    #     mock_stream_writer, mock_stream_reader = AsyncMock(), AsyncMock()

    #     # Mock the response message
    #     from arcade_mcp_server.types import JSONRPCResponse

    #     response_message = JSONRPCResponse(jsonrpc="2.0", id=1, result={"tools": []})

    #     # Mock EventMessage
    #     from arcade_mcp_server.transports.http_streamable import EventMessage

    #     event_msg = EventMessage(message=response_message)

    #     # Configure the stream reader to return our response
    #     mock_stream_reader.__aiter__ = AsyncMock(return_value=iter([event_msg]))

    #     with patch("anyio.create_memory_object_stream") as mock_create_stream:
    #         mock_create_stream.return_value = (mock_stream_writer, mock_stream_reader)

    #         # Mock the Request object
    #         with patch("starlette.requests.Request") as mock_request_class:
    #             mock_request = MagicMock()
    #             mock_request.body = AsyncMock(return_value=body)
    #             mock_request_class.return_value = mock_request

    #             await transport._handle_post_request(scope, mock_request, receive, send)

    #     # Verify message was sent to read stream
    #     mock_writer.send.assert_called_once()

    #     # Verify HTTP response was sent
    #     send.assert_called()

    @pytest.mark.asyncio
    async def test_handle_post_request_invalid_json(self, mcp_server):
        """Test POST request handling with invalid JSON."""
        transport = HTTPStreamableTransport(
            mcp_session_id="test-session", is_json_response_enabled=True
        )

        # Mock the read stream writer
        mock_writer = AsyncMock()
        transport._read_stream_writer = mock_writer

        # Invalid JSON body
        body = b'{"invalid": json}'

        scope = {
            "type": "http",
            "method": "POST",
            "headers": [
                (b"content-type", b"application/json"),
                (b"accept", b"application/json"),  # This should pass Accept header check
                (MCP_SESSION_ID_HEADER.lower().encode(), b"test-session"),
            ],
        }

        receive = AsyncMock()
        receive.return_value = {"type": "http.request", "body": body}
        send = AsyncMock()

        # Mock the Request object properly
        with patch("starlette.requests.Request") as mock_request_class:
            mock_request = MagicMock()
            mock_request.body = AsyncMock(return_value=body)
            # Mock headers.get method properly
            mock_request.headers.get.side_effect = lambda key, default="": {
                "accept": "application/json",
                "content-type": "application/json",
                MCP_SESSION_ID_HEADER: "test-session",
            }.get(key, default)
            mock_request_class.return_value = mock_request

            await transport._handle_post_request(scope, mock_request, receive, send)

            # Verify error response was sent
            send.assert_called()

            # Check the ASGI response message for status code 400 (Bad Request)
            response_calls = send.call_args_list
            assert len(response_calls) > 0

            # Find the HTTP response start message
            for call in response_calls:
                message = call[0][0]  # First argument of call
                if message.get("type") == "http.response.start":
                    assert message["status"] == 400
                    break
            else:
                pytest.fail("No http.response.start message found")


class TestHTTPStreamableTransportGet:
    """Test GET request handling."""

    #     @pytest.mark.asyncio
    #     async def test_handle_get_request_valid_sse(self, mcp_server):
    #         """Test successful GET request for SSE stream."""
    #         transport = HTTPStreamableTransport(
    #             mcp_session_id="test-session", is_json_response_enabled=False
    #         )

    #         # Mock the read stream writer
    #         mock_writer = AsyncMock()
    #         transport._read_stream_writer = mock_writer

    #         # Mock request with SSE accept header
    #         mock_request = MagicMock()
    #         mock_request.headers = {
    #             "accept": "text/event-stream",
    #             MCP_SESSION_ID_HEADER: "test-session",
    #         }
    #         mock_request.headers.get = lambda key, default=None: {
    #             "accept": "text/event-stream",
    #             MCP_SESSION_ID_HEADER: "test-session",
    #         }.get(key, default)

    #         send = AsyncMock()

    #         # Mock validation methods
    #         with patch.object(transport, "_validate_request_headers", return_value=True):
    #             with patch("anyio.create_memory_object_stream") as mock_create_stream:
    #                 mock_stream_writer, mock_stream_reader = AsyncMock(), AsyncMock()
    #                 mock_create_stream.return_value = (mock_stream_writer, mock_stream_reader)

    #                 # Mock EventSourceResponse
    #                 with patch("sse_starlette.EventSourceResponse") as mock_sse_response:
    #                     mock_response = AsyncMock()
    #                     mock_sse_response.return_value = mock_response

    #                     await transport._handle_get_request(mock_request, send)

    #                     # Verify SSE response was created and called
    #                     mock_sse_response.assert_called_once()
    #                     mock_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_get_request_invalid_accept_header(self, mcp_server):
        """Test GET request with invalid Accept header."""
        transport = HTTPStreamableTransport(
            mcp_session_id="test-session", is_json_response_enabled=False
        )

        # Mock the read stream writer (required by _handle_get_request)
        mock_writer = AsyncMock()
        transport._read_stream_writer = mock_writer

        # Mock request without SSE accept header
        mock_request = MagicMock()
        # Mock headers.get method properly instead of overriding the dict
        mock_request.headers.get.side_effect = lambda key, default="": {
            "accept": "application/json",  # Wrong accept header for SSE
            MCP_SESSION_ID_HEADER: "test-session",
        }.get(key, default)
        mock_request.scope = {"type": "http", "method": "GET"}
        mock_request.receive = AsyncMock()

        send = AsyncMock()

        await transport._handle_get_request(mock_request, send)

        # Verify error response was sent
        send.assert_called()

        # Check the ASGI response message for status code 406 (Not Acceptable)
        response_calls = send.call_args_list
        assert len(response_calls) > 0

        # Find the HTTP response start message
        for call in response_calls:
            message = call[0][0]  # First argument of call
            if message.get("type") == "http.response.start":
                assert message["status"] == 406
                break
        else:
            pytest.fail("No http.response.start message found")


class TestHTTPStreamableTransportDelete:
    """Test DELETE request handling."""

    #     @pytest.mark.asyncio
    #     async def test_handle_delete_request_valid_session(self, mcp_server):
    #         """Test successful DELETE request for session termination."""
    #         transport = HTTPStreamableTransport(
    #             mcp_session_id="test-session", is_json_response_enabled=True
    #         )

    #         # Mock request with valid session ID
    #         mock_request = MagicMock()
    #         mock_request.headers = {MCP_SESSION_ID_HEADER: "test-session"}
    #         mock_request.headers.get = lambda key, default=None: {
    #             MCP_SESSION_ID_HEADER: "test-session"
    #         }.get(key, default)
    #         mock_request.scope = {"type": "http", "method": "DELETE"}
    #         mock_request.receive = AsyncMock()

    #         send = AsyncMock()

    #         # Mock validation and termination
    #         with patch.object(transport, "_validate_request_headers", return_value=True):
    #             with patch.object(transport, "terminate") as mock_terminate:
    #                 await transport._handle_delete_request(mock_request, send)

    #                 # Verify termination was called
    #                 mock_terminate.assert_called_once()

    #                 # Verify success response was sent
    #                 send.assert_called()

    @pytest.mark.asyncio
    async def test_handle_delete_request_no_session_id(self, mcp_server):
        """Test DELETE request without session ID support (should not be allowed)."""
        transport = HTTPStreamableTransport(
            mcp_session_id=None,  # No session ID
            is_json_response_enabled=True,
        )

        mock_request = MagicMock()
        mock_request.scope = {"type": "http", "method": "DELETE"}
        mock_request.receive = AsyncMock()

        send = AsyncMock()

        await transport._handle_delete_request(mock_request, send)

        # Verify error response was sent
        send.assert_called()

        # Check the ASGI response message for status code
        response_calls = send.call_args_list
        assert len(response_calls) > 0

        # The first call should be the HTTP response start with status 405
        first_call = response_calls[0]
        message = first_call[0][0]  # First argument of first call
        if message.get("type") == "http.response.start":
            assert message["status"] == 405

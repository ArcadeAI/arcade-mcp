from unittest.mock import AsyncMock, patch

import pytest
from arcade_mcp_server.transports.http_session_manager import (
    MCP_SESSION_ID_HEADER,
    HTTPSessionManager,
)


class TestHTTPSessionManager:
    """Test HTTPSessionManager initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_run_cannot_be_reused(self, mcp_server):
        """Test that run() can only be called once per instance."""
        manager = HTTPSessionManager(server=mcp_server)

        # First call should work
        async with manager.run():
            pass

        # Second call should raise error
        with pytest.raises(RuntimeError):
            async with manager.run():
                pass

    @pytest.mark.asyncio
    async def test_handle_request_without_run_raises_error(self, mcp_server):
        """Test that handle_request raises error if run() not called."""
        manager = HTTPSessionManager(server=mcp_server)

        scope = {"type": "http", "method": "POST"}
        receive = AsyncMock()
        send = AsyncMock()

        with pytest.raises(RuntimeError):
            await manager.handle_request(scope, receive, send)

    @pytest.mark.asyncio
    async def test_stateless_mode_routing(self, mcp_server):
        """Test that stateless mode routes to _handle_stateless_request."""
        manager = HTTPSessionManager(server=mcp_server, stateless=True)

        scope = {"type": "http", "method": "POST"}
        receive = AsyncMock()
        send = AsyncMock()

        with patch.object(manager, "_handle_stateless_request") as mock_stateless:
            async with manager.run():
                await manager.handle_request(scope, receive, send)

            mock_stateless.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_stateful_mode_routing(self, mcp_server):
        """Test that stateful mode routes to _handle_stateful_request."""
        manager = HTTPSessionManager(server=mcp_server, stateless=False)

        scope = {"type": "http", "method": "POST"}
        receive = AsyncMock()
        send = AsyncMock()

        with patch.object(manager, "_handle_stateful_request") as mock_stateful:
            async with manager.run():
                await manager.handle_request(scope, receive, send)

            mock_stateful.assert_called_once_with(scope, receive, send)


# class TestHTTPSessionManagerStateless:
#     """Test stateless request handling."""

#     @pytest.mark.asyncio
#     async def test_stateless_creates_new_transport(self, mcp_server):
#         """Test that stateless mode creates a new transport for each request."""
#         manager = HTTPSessionManager(server=mcp_server, stateless=True, json_response=True)

#         scope = {"type": "http", "method": "POST"}
#         receive = AsyncMock()
#         send = AsyncMock()

#         with patch(
#             "arcade_mcp_server.transports.http_session_manager.HTTPStreamableTransport"
#         ) as mock_transport_class:
#             mock_transport = AsyncMock()
#             mock_transport_class.return_value = mock_transport
#             mock_transport.connect.return_value.__aenter__ = AsyncMock(
#                 return_value=(AsyncMock(), AsyncMock())
#             )
#             mock_transport.connect.return_value.__aexit__ = AsyncMock(return_value=None)

#             async with manager.run():
#                 await manager.handle_request(scope, receive, send)

#             # Verify transport was created with correct parameters
#             mock_transport_class.assert_called_once_with(
#                 mcp_session_id=None,
#                 is_json_response_enabled=True,
#                 event_store=None,
#             )

#             # Verify transport methods were called
#             mock_transport.handle_request.assert_called_once_with(scope, receive, send)
#             mock_transport.terminate.assert_called_once()

#     @pytest.mark.asyncio
#     async def test_stateless_handles_transport_errors(self, mcp_server):
#         """Test that stateless mode handles transport creation errors gracefully."""
#         manager = HTTPSessionManager(server=mcp_server, stateless=True)

#         scope = {"type": "http", "method": "POST"}
#         receive = AsyncMock()
#         send = AsyncMock()

#         with patch(
#             "arcade_mcp_server.transports.http_session_manager.HTTPStreamableTransport"
#         ) as mock_transport_class:
#             mock_transport_class.side_effect = Exception("Transport creation failed")

#             async with manager.run():
#                 # Should not raise exception, error handling is internal
#                 with pytest.raises(Exception, match="Transport creation failed"):
#                     await manager.handle_request(scope, receive, send)


class TestHTTPSessionManagerStateful:
    """Test stateful request handling."""

    @pytest.mark.asyncio
    async def test_existing_session_routing(self, mcp_server):
        """Test routing to existing session when session ID provided."""
        manager = HTTPSessionManager(server=mcp_server, stateless=False)

        # Pre-populate with an existing transport
        existing_transport = AsyncMock()
        existing_session_id = "existing-session-456"
        manager._server_instances[existing_session_id] = existing_transport

        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(MCP_SESSION_ID_HEADER.lower().encode(), existing_session_id.encode())],
        }
        receive = AsyncMock()
        send = AsyncMock()

        async with manager.run():
            await manager.handle_request(scope, receive, send)

            # Verify existing transport was used
            existing_transport.handle_request.assert_called_once_with(scope, receive, send)

            # Verify no new transport was created
            assert len(manager._server_instances) == 1

    @pytest.mark.asyncio
    async def test_invalid_session_id_error(self, mcp_server):
        """Test error response for invalid session ID."""
        manager = HTTPSessionManager(server=mcp_server, stateless=False)

        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(MCP_SESSION_ID_HEADER.lower().encode(), b"invalid-session-id")],
        }
        receive = AsyncMock()
        send = AsyncMock()

        async with manager.run():
            await manager.handle_request(scope, receive, send)

            # Verify error response was sent
            send.assert_called()
            # Check that a response was sent (the Response.__call__ method)
            call_args = send.call_args_list
            assert len(call_args) > 0

    @pytest.mark.asyncio
    async def test_session_cleanup_on_manager_shutdown(self, mcp_server):
        """Test that sessions are cleaned up when manager shuts down."""
        manager = HTTPSessionManager(server=mcp_server, stateless=False)

        # Add some mock sessions
        manager._server_instances["session-1"] = AsyncMock()
        manager._server_instances["session-2"] = AsyncMock()

        async with manager.run():
            assert len(manager._server_instances) == 2

        # After context exit, sessions should be cleared
        assert len(manager._server_instances) == 0

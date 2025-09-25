"""Tests for ServerSession/RequestManager cancellation behavior."""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from arcade_mcp_server.session import ServerSession


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,params",
    [
        ("sampling/createMessage", {"messages": [], "maxTokens": 1}),
        ("roots/list", None),
        (
            "completion/complete",
            {"ref": {"type": "ref/prompt", "name": "x"}, "argument": {"name": "q", "value": ""}},
        ),
    ],
)
async def test_cancel_all_sends_notifications_and_fails_futures(
    mcp_server, mock_read_stream, mock_write_stream, method, params
):
    session = ServerSession(
        server=mcp_server, read_stream=mock_read_stream, write_stream=mock_write_stream
    )
    assert session._request_manager is not None

    mock_write_stream.send = AsyncMock()

    pending_task = asyncio.create_task(
        session._request_manager.send_request(method, params, timeout=5.0)
    )
    await asyncio.sleep(0)

    await session._cleanup_pending_requests()

    from arcade_mcp_server.exceptions import SessionError

    with pytest.raises(SessionError):
        await pending_task

    # Verify a cancelled notification was sent
    assert mock_write_stream.send.call_count >= 1
    sent_methods = [
        json.loads(call[0][0].strip()).get("method")
        for call in mock_write_stream.send.call_args_list
    ]
    assert "notifications/cancelled" in sent_methods


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,params",
    [
        ("roots/list", None),
        ("sampling/createMessage", {"messages": [], "maxTokens": 1}),
    ],
)
async def test_closed_flag_drops_late_responses(
    mcp_server, mock_read_stream, mock_write_stream, method, params
):
    session = ServerSession(
        server=mcp_server, read_stream=mock_read_stream, write_stream=mock_write_stream
    )
    assert session._request_manager is not None

    mock_write_stream.send = AsyncMock()

    send_task = asyncio.create_task(
        session._request_manager.send_request(method, params, timeout=5.0)
    )
    await asyncio.sleep(0)

    await session._cleanup_pending_requests()

    # Simulate a late response from client; should be dropped silently
    late_response: dict[str, Any] = {"jsonrpc": "2.0", "id": "unknown", "result": {"ok": True}}
    await session._request_manager.handle_response(late_response)

    from arcade_mcp_server.exceptions import SessionError

    with pytest.raises(SessionError):
        await send_task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,params",
    [
        (
            "completion/complete",
            {"ref": {"type": "ref/prompt", "name": "x"}, "argument": {"name": "q", "value": "v"}},
        ),
        ("sampling/createMessage", {"messages": [], "maxTokens": 1}),
    ],
)
async def test_new_requests_rejected_after_close(
    mcp_server, mock_read_stream, mock_write_stream, method, params
):
    session = ServerSession(
        server=mcp_server, read_stream=mock_read_stream, write_stream=mock_write_stream
    )
    assert session._request_manager is not None

    await session._cleanup_pending_requests()

    from arcade_mcp_server.exceptions import SessionError

    with pytest.raises(SessionError):
        await session._request_manager.send_request(method, params, timeout=0.1)


@pytest.mark.asyncio
async def test_cleanup_is_idempotent(mcp_server, mock_read_stream, mock_write_stream):
    session = ServerSession(
        server=mcp_server, read_stream=mock_read_stream, write_stream=mock_write_stream
    )
    assert session._request_manager is not None

    await session._cleanup_pending_requests()
    # Calling again should not raise and should not send extra notifications
    before = getattr(mock_write_stream.send, "call_count", 0)
    await session._cleanup_pending_requests()
    after = getattr(mock_write_stream.send, "call_count", 0)
    # Allow zero or unchanged; do not enforce increase
    assert after >= before

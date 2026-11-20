"""Normal HTTP transport teardown must not log errors.

``HTTPStreamableTransport.terminate()`` closes the receive ends of its memory
streams while ``ServerSession.run`` and the transport's ``message_router`` are
still reading from them. anyio raises ``ClosedResourceError`` in those readers.
That is the expected shutdown path, so it must be logged at DEBUG, not ERROR.

A stateless request terminates its transport at the end of every request, and a
stateful DELETE terminates the session's transport, so both cover this path.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
import httpx
import pytest
from arcade_mcp_server.exceptions import SessionError
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

MODERN_VERSION = "2026-07-28"
MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "teardown-test", "version": "1"},
}
BASE_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


@asynccontextmanager
async def _client(mcp_server: MCPServer, *, stateless: bool) -> AsyncIterator[httpx.AsyncClient]:
    mcp_server.allowed_origins = ["*"]
    manager = HTTPSessionManager(server=mcp_server, json_response=True, stateless=stateless)

    async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        await manager.handle_request(scope, receive, send)

    app = Starlette(routes=[Mount("/mcp", app=endpoint)])
    async with (
        manager.run(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client,
    ):
        yield client


def _error_records(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        f"{r.name}: {r.getMessage()}" for r in caplog.records if r.levelno >= logging.ERROR
    ]


def _tool_call(request_id: int, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"name": "TestToolkit_test_tool", "arguments": {"text": "hi"}}
    if meta is not None:
        params["_meta"] = meta
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": params}


@pytest.mark.asyncio
@pytest.mark.parametrize("configured_stateless", [False, True])
async def test_modern_stateless_request_logs_no_errors(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture, configured_stateless: bool
) -> None:
    """A request with the 2026-07-28 header is served statelessly in either mode."""
    caplog.set_level(logging.DEBUG)
    async with _client(mcp_server, stateless=configured_stateless) as client:
        resp = await client.post(
            "/mcp/",
            headers={**BASE_HEADERS, "MCP-Protocol-Version": MODERN_VERSION},
            json=_tool_call(1, MODERN_META),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["content"] == [{"type": "text", "text": "Echo: hi"}]

    assert _error_records(caplog) == []


@pytest.mark.asyncio
async def test_legacy_stateless_request_logs_no_errors(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
) -> None:
    """A legacy request to a stateless manager also tears its transport down per request."""
    caplog.set_level(logging.DEBUG)
    async with _client(mcp_server, stateless=True) as client:
        resp = await client.post(
            "/mcp/",
            headers={**BASE_HEADERS, "MCP-Protocol-Version": "2025-11-25"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        assert resp.status_code == 200, resp.text
        assert "tools" in resp.json()["result"]

    assert _error_records(caplog) == []


@pytest.mark.asyncio
async def test_stateful_delete_logs_no_errors(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    async with _client(mcp_server, stateless=False) as client:
        init = await client.post(
            "/mcp/",
            headers=BASE_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            },
        )
        assert init.status_code == 200, init.text
        session_id = init.headers["Mcp-Session-Id"]
        session_headers = {
            **BASE_HEADERS,
            "Mcp-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-11-25",
        }
        await client.post(
            "/mcp/",
            headers=session_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

        delete = await client.delete("/mcp/", headers=session_headers)
        assert delete.status_code == 200, delete.text
        # Let the session's background tasks observe the closed streams.
        await anyio.sleep(0.1)

    assert _error_records(caplog) == []


class _FailingStream:
    """A read stream whose iteration fails with an unexpected error."""

    def __aiter__(self) -> _FailingStream:
        return self

    async def __anext__(self) -> Any:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_session_loop_error_is_logged_and_raised_as_session_error(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
) -> None:
    """An unexpected read error is logged as "Session error" and surfaces as SessionError,
    not as an AttributeError from the error handler itself."""
    caplog.set_level(logging.DEBUG)
    session = ServerSession(server=mcp_server, read_stream=_FailingStream(), write_stream=None)

    with pytest.raises(BaseException) as excinfo:
        await session.run()

    # anyio's task group may wrap the error in an ExceptionGroup. Unwrap by duck
    # typing because BaseExceptionGroup is not a builtin on Python 3.10.
    raised: BaseException = excinfo.value
    while len(getattr(raised, "exceptions", ())) == 1:
        raised = raised.exceptions[0]  # type: ignore[attr-defined]
    assert isinstance(raised, SessionError), repr(raised)
    assert "boom" in str(raised)

    session_errors = [
        r for r in caplog.records if r.levelno >= logging.ERROR and r.getMessage() == "Session error"
    ]
    assert len(session_errors) == 1
    assert session_errors[0].exc_info is not None
    assert isinstance(session_errors[0].exc_info[1], RuntimeError)

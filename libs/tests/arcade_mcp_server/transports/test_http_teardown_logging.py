"""Normal HTTP transport teardown must not log warnings or errors.

``HTTPStreamableTransport.terminate()`` closes the memory streams that
``ServerSession.run``, the transport's ``message_router`` and the standalone GET
stream writer are still reading from. anyio raises ``ClosedResourceError`` in those
readers. That is the expected shutdown path, so it is logged at DEBUG.

A stateless request terminates its transport at the end of every request, and a
stateful DELETE terminates the session's transport, so both cover this path.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

import anyio
import httpx
import pytest
from arcade_mcp_server.exceptions import SessionError
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from arcade_mcp_server.transports.http_streamable import GET_STREAM_KEY, HTTPStreamableTransport
from arcade_mcp_server.types import JSONRPCRequest, SessionMessage
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

# From anyio 4.16, closing a memory stream wakes a waiting reader with
# ClosedResourceError. Earlier versions end the reader's loop with EndOfStream.
ANYIO_WAKES_CLOSED_READERS = tuple(int(p) for p in version("anyio").split(".")[:2]) >= (4, 16)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


@pytest.fixture
def closed_transports(monkeypatch: pytest.MonkeyPatch) -> list[HTTPStreamableTransport]:
    """Record each transport whose connect() context has fully exited.

    By then the session loop and the message router have finished and logged
    whatever they were going to log, so tests can wait for it instead of sleeping.
    """
    closed: list[HTTPStreamableTransport] = []
    original_connect = HTTPStreamableTransport.connect

    @asynccontextmanager
    async def connect(self: HTTPStreamableTransport) -> AsyncIterator[Any]:
        try:
            async with original_connect(self) as streams:
                yield streams
        finally:
            closed.append(self)

    monkeypatch.setattr(HTTPStreamableTransport, "connect", connect)
    return closed


async def _wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    with anyio.fail_after(timeout):
        while not condition():
            await anyio.sleep(0.01)


@asynccontextmanager
async def _client(
    mcp_server: MCPServer, *, stateless: bool, json_response: bool = True
) -> AsyncIterator[httpx.AsyncClient]:
    mcp_server.allowed_origins = ["*"]
    manager = HTTPSessionManager(
        server=mcp_server, json_response=json_response, stateless=stateless
    )

    async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        await manager.handle_request(scope, receive, send)

    app = Starlette(routes=[Mount("/mcp", app=endpoint)])
    async with (
        manager.run(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client,
    ):
        yield client


def _noisy_records(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        f"{r.levelname} {r.name}: {r.getMessage()}"
        for r in caplog.records
        if r.levelno >= logging.WARNING
    ]


def _error_records(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [f"{r.name}: {r.getMessage()}" for r in caplog.records if r.levelno >= logging.ERROR]


def _tool_call(request_id: int, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"name": "TestToolkit_test_tool", "arguments": {"text": "hi"}}
    if meta is not None:
        params["_meta"] = meta
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": params}


def _sse_result(resp: httpx.Response) -> dict[str, Any]:
    if resp.headers["content-type"].startswith("application/json"):
        return resp.json()  # type: ignore[no-any-return]
    data = [line[len("data:") :] for line in resp.text.splitlines() if line.startswith("data:")]
    return json.loads(data[-1])  # type: ignore[no-any-return]


# -----------------------------------------------------------------------------
# End to end through HTTPSessionManager
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("json_response", [True, False], ids=["json", "sse"])
@pytest.mark.parametrize("configured_stateless", [False, True])
async def test_modern_stateless_request_logs_no_warnings(
    mcp_server: MCPServer,
    caplog: pytest.LogCaptureFixture,
    closed_transports: list[HTTPStreamableTransport],
    configured_stateless: bool,
    json_response: bool,
) -> None:
    """A request with the 2026-07-28 header is served statelessly in either mode."""
    caplog.set_level(logging.DEBUG)
    async with _client(
        mcp_server, stateless=configured_stateless, json_response=json_response
    ) as client:
        resp = await client.post(
            "/mcp/",
            headers={**BASE_HEADERS, "MCP-Protocol-Version": MODERN_VERSION},
            json=_tool_call(1, MODERN_META),
        )
        assert resp.status_code == 200, resp.text
        assert _sse_result(resp)["result"]["content"] == [{"type": "text", "text": "Echo: hi"}]

        await _wait_until(lambda: len(closed_transports) == 1)
        assert _noisy_records(caplog) == []


@pytest.mark.asyncio
async def test_legacy_stateless_request_logs_no_warnings(
    mcp_server: MCPServer,
    caplog: pytest.LogCaptureFixture,
    closed_transports: list[HTTPStreamableTransport],
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

        await _wait_until(lambda: len(closed_transports) == 1)
        assert _noisy_records(caplog) == []


@pytest.mark.asyncio
async def test_stateful_delete_logs_no_warnings(
    mcp_server: MCPServer,
    caplog: pytest.LogCaptureFixture,
    closed_transports: list[HTTPStreamableTransport],
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
        session_headers = {
            **BASE_HEADERS,
            "Mcp-Session-Id": init.headers["Mcp-Session-Id"],
            "MCP-Protocol-Version": "2025-11-25",
        }
        await client.post(
            "/mcp/",
            headers=session_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

        delete = await client.delete("/mcp/", headers=session_headers)
        assert delete.status_code == 200, delete.text

        await _wait_until(lambda: len(closed_transports) == 1)
        assert _noisy_records(caplog) == []


# -----------------------------------------------------------------------------
# Session loop
# -----------------------------------------------------------------------------


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
        r
        for r in caplog.records
        if r.levelno >= logging.ERROR and r.getMessage() == "Session error"
    ]
    assert len(session_errors) == 1
    assert session_errors[0].exc_info is not None
    assert isinstance(session_errors[0].exc_info[1], RuntimeError)


@asynccontextmanager
async def _running_session(
    server: Any, transport: HTTPStreamableTransport
) -> AsyncIterator[tuple[ServerSession, anyio.Event]]:
    """Run a ServerSession over a real transport.connect(), as the session manager does.

    Yields the session and an event set when session.run() returns.
    """
    run_returned = anyio.Event()
    async with anyio.create_task_group() as tg:

        async def run_session(*, task_status: Any = anyio.TASK_STATUS_IGNORED) -> None:
            async with transport.connect() as (read_stream, write_stream):
                session = ServerSession(
                    server=server, read_stream=read_stream, write_stream=write_stream
                )
                task_status.started(session)
                try:
                    await session.run()
                finally:
                    run_returned.set()

        session = await tg.start(run_session)
        yield session, run_returned


class _SlowServer:
    """Stand-in for MCPServer whose request handler runs for a long time."""

    def __init__(self) -> None:
        self.started = anyio.Event()
        self.outcome: str | None = None

    async def handle_message(self, data: dict[str, Any], *_: Any, **__: Any) -> dict[str, Any]:
        self.started.set()
        try:
            await anyio.sleep(30)
        except BaseException:
            self.outcome = "cancelled"
            raise
        self.outcome = "completed"
        return {"jsonrpc": "2.0", "id": data["id"], "result": {}}


@pytest.mark.asyncio
@pytest.mark.skipif(
    not ANYIO_WAKES_CLOSED_READERS,
    reason="anyio < 4.16 ends the session loop normally, so in-flight handlers run to completion",
)
async def test_teardown_cancels_in_flight_handlers(caplog: pytest.LogCaptureFixture) -> None:
    """Once the transport is gone nobody can receive a response, so in-flight handlers
    are cancelled and the session ends instead of waiting for them."""
    caplog.set_level(logging.DEBUG)
    server = _SlowServer()
    transport = HTTPStreamableTransport(mcp_session_id="s1", is_json_response_enabled=True)

    async with _running_session(server, transport) as (_session, run_returned):
        assert transport._read_stream_writer is not None
        await transport._read_stream_writer.send(
            SessionMessage(message=JSONRPCRequest(id=1, method="tools/call", params={}))
        )
        with anyio.fail_after(2):
            await server.started.wait()

        await transport.terminate()

        with anyio.fail_after(2):
            await run_returned.wait()

    assert server.outcome == "cancelled"
    assert _noisy_records(caplog) == []


@pytest.mark.asyncio
async def test_teardown_releases_pending_server_to_client_requests(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
) -> None:
    """A request the server sent to the client (elicitation, sampling, roots) fails with
    SessionError as soon as the transport is torn down, instead of waiting for its timeout.

    The waiter runs outside the session's task group, as task-augmented tools do.
    """
    caplog.set_level(logging.DEBUG)
    transport = HTTPStreamableTransport(mcp_session_id="s1", is_json_response_enabled=True)
    outcome: list[BaseException] = []

    async with (
        anyio.create_task_group() as outer,
        _running_session(mcp_server, transport) as (session, _run_returned),
    ):
        request_manager = session._request_manager
        assert request_manager is not None

        async def wait_for_client() -> None:
            try:
                await request_manager.send_request("elicitation/create", {}, timeout=2.0)
            except Exception as e:
                outcome.append(e)

        outer.start_soon(wait_for_client)
        await _wait_until(lambda: bool(request_manager._pending_requests))

        await transport.terminate()

        await _wait_until(lambda: bool(outcome), timeout=1.0)

    assert isinstance(outcome[0], SessionError), repr(outcome[0])
    assert _noisy_records(caplog) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("closed_end", ["send", "receive"])
async def test_response_after_transport_close_is_dropped_quietly(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture, closed_end: str
) -> None:
    """A handler that finishes after teardown can't deliver its response. That must not
    crash the session. On anyio < 4.16 closing a stream does not wake its reader with an
    error, so in-flight handlers run to completion and reach this send."""
    caplog.set_level(logging.DEBUG)
    send_stream, receive_stream = anyio.create_memory_object_stream[Any](1)
    # terminate() closes both ends; either one alone must be handled.
    await (send_stream if closed_end == "send" else receive_stream).aclose()
    session = ServerSession(server=mcp_server, read_stream=None, write_stream=send_stream)

    await session._process_message('{"jsonrpc": "2.0", "id": 1, "method": "ping"}')

    assert _noisy_records(caplog) == []


# -----------------------------------------------------------------------------
# Transport readers
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_with_open_get_stream_logs_no_warnings(
    mcp_server: MCPServer, caplog: pytest.LogCaptureFixture
) -> None:
    """Clients usually keep a standalone GET stream open, so DELETE commonly ends one."""
    caplog.set_level(logging.DEBUG)
    transport = HTTPStreamableTransport(mcp_session_id="s1", is_json_response_enabled=True)
    disconnected = anyio.Event()
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    get_scope = {
        "type": "http",
        "method": "GET",
        "path": "/mcp",
        "query_string": b"",
        "headers": [(b"accept", b"text/event-stream"), (b"mcp-session-id", b"s1")],
    }

    def response_finished() -> bool:
        return any(m["type"] == "http.response.body" and not m.get("more_body") for m in sent)

    async with _running_session(mcp_server, transport), anyio.create_task_group() as tg:
        tg.start_soon(transport.handle_request, get_scope, receive, send)
        await _wait_until(lambda: GET_STREAM_KEY in transport._request_streams)

        await transport.terminate()

        await _wait_until(response_finished)
        disconnected.set()

    assert sent[0]["status"] == 200
    assert _noisy_records(caplog) == []


class _FailingEventStore:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def store_event(self, stream_id: str, message: Any) -> str:
        raise self.error

    async def replay_events_after(self, last_event_id: str, send_callback: Any) -> str | None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [anyio.ClosedResourceError(), RuntimeError("boom")], ids=["closed", "other"]
)
async def test_message_router_failure_before_terminate_is_an_error(
    caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    """Only a closure caused by terminate() is routine. Like the official SDK, anything
    else that stops the router is logged at ERROR."""
    caplog.set_level(logging.DEBUG)
    transport = HTTPStreamableTransport(
        mcp_session_id="s1",
        is_json_response_enabled=True,
        event_store=_FailingEventStore(error),  # type: ignore[arg-type]
    )

    async with transport.connect() as (_read_stream, write_stream):
        await write_stream.send('{"jsonrpc": "2.0", "method": "notifications/message"}')
        await _wait_until(lambda: bool(_error_records(caplog)))
        await transport.terminate()

    assert len(_error_records(caplog)) == 1
    assert "message router" in _error_records(caplog)[0]

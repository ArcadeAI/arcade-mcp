"""Request teardown through the actual ASGI manager and session streams."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
import pytest
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.transports import http_session_manager
from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport
from starlette.types import Message, Receive, Scope


class ObservedTransport(HTTPStreamableTransport):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.finished = anyio.Event()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[Any]:
        try:
            async with super().connect() as streams:
                yield streams
        finally:
            self.finished.set()


def request(version: str) -> tuple[Scope, Receive]:
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp/",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"content-type", b"application/json"),
            (b"accept", b"application/json, text/event-stream"),
            (b"mcp-protocol-version", version.encode("ascii")),
        ],
    }
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode("utf-8")
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await anyio.sleep_forever()
        raise AssertionError("unreachable")

    return scope, receive


async def assert_closed(transport: ObservedTransport) -> None:
    assert transport.is_terminated
    assert not transport._request_streams
    for stream in (transport._read_stream, transport._write_stream_reader):
        assert stream is not None
        statistics = stream.statistics()
        assert statistics.open_send_streams == 0
        assert statistics.open_receive_streams == 0
    # Check before manager.run() exits: app shutdown must not be what releases
    # a per-request stateless session.
    with anyio.fail_after(5):
        await transport.finished.wait()


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["2025-06-18", "2025-11-25"])
@pytest.mark.parametrize("outcome", ["normal", "send-error", "cancel"])
async def test_stateless_request_always_closes_its_transport(
    mcp_server: MCPServer,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    outcome: str,
) -> None:
    created: list[ObservedTransport] = []

    def make_transport(**kwargs: Any) -> ObservedTransport:
        transport = ObservedTransport(**kwargs)
        created.append(transport)
        return transport

    monkeypatch.setattr(http_session_manager, "HTTPStreamableTransport", make_transport)
    manager = HTTPSessionManager(mcp_server, stateless=True, json_response=True)
    messages: list[Message] = []
    started = anyio.Event()
    failure = ConnectionError("ASGI client disconnected while sending")

    async def send(message: Message) -> None:
        if outcome == "send-error":
            raise failure
        if outcome == "cancel":
            started.set()
            await anyio.sleep_forever()
        messages.append(message)

    async with manager.run():
        scope, receive = request(version)
        if outcome == "send-error":
            with pytest.raises(ConnectionError) as caught:
                await manager.handle_request(scope, receive, send)
            assert caught.value is failure
        elif outcome == "cancel":
            with anyio.CancelScope() as request_scope:
                async def disconnect() -> None:
                    await started.wait()
                    request_scope.cancel()

                async with anyio.create_task_group() as clients:
                    clients.start_soon(disconnect)
                    await manager.handle_request(scope, receive, send)
            assert request_scope.cancel_called
        else:
            await manager.handle_request(scope, receive, send)
            body = b"".join(message.get("body", b"") for message in messages)
            assert json.loads(body) == {"jsonrpc": "2.0", "id": 1, "result": {}}

        assert len(created) == 1
        await assert_closed(created[0])

        # A failed/cancelled request must not tear down the application-wide
        # manager or prevent a following healthy request.
        healthy_messages: list[Message] = []

        async def healthy_send(message: Message) -> None:
            healthy_messages.append(message)

        scope, receive = request(version)
        await manager.handle_request(scope, receive, healthy_send)
        assert len(created) == 2
        await assert_closed(created[1])
        body = b"".join(message.get("body", b"") for message in healthy_messages)
        assert json.loads(body)["result"] == {}

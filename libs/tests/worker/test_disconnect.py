import asyncio
import json
from typing import Annotated

import pytest
from arcade_core.schema import ToolCallRequest, ToolContext, ToolReference
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import tool
from fastapi import FastAPI

# Created per test: an asyncio.Event belongs to the loop that first waits on it.
signals: dict[str, asyncio.Event] = {}


@pytest.fixture(autouse=True)
def _fresh_signals():
    signals["started"] = asyncio.Event()
    signals["cancelled"] = asyncio.Event()


@tool()
async def long_running_tool(context: ToolContext, pages: Annotated[int, "pages"]) -> str:
    """Pages through results until it is stopped."""
    signals["started"].set()
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        signals["cancelled"].set()
        raise
    return "done"


@tool()
def quick_tool(context: ToolContext, pages: Annotated[int, "pages"]) -> str:
    """Answers at once."""
    return f"{pages} pages"


def _app() -> FastAPI:
    app = FastAPI()

    # A function middleware, like the task tracker the MCP server installs, which
    # never passes a disconnect on to the route.
    @app.middleware("http")
    async def passthrough(request, call_next):
        return await call_next(request)

    worker = FastAPIWorker(app=app, disable_auth=True)
    worker.register_tool(long_running_tool, toolkit_name="kit")
    worker.register_tool(quick_tool, toolkit_name="kit")
    return app


def _invoke_body(tool_name: str) -> bytes:
    request = ToolCallRequest(
        execution_id="exec-1",
        tool=ToolReference(toolkit="Kit", name=tool_name),
        inputs={"pages": 3},
    )
    return json.dumps(request.model_dump(mode="json")).encode()


async def _call(app, body: bytes, hang_up: asyncio.Event, *, hang_up_once_answered=False):
    sent: list[dict] = []
    pending = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        if pending:
            return pending.pop(0)
        await hang_up.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if hang_up_once_answered and message["type"] == "http.response.body":
            hang_up.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/worker/tools/invoke",
        "raw_path": b"/worker/tools/invoke",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("127.0.0.1", 8002),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=5)
    return sent


@pytest.mark.asyncio
async def test_a_tool_call_whose_caller_hangs_up_is_cancelled():
    hang_up = asyncio.Event()
    call = asyncio.ensure_future(_call(_app(), _invoke_body("LongRunningTool"), hang_up))
    await asyncio.wait_for(signals["started"].wait(), timeout=5)

    hang_up.set()
    sent = await call

    assert signals["cancelled"].is_set()
    assert not [m for m in sent if m["type"] == "http.response.start"]


@pytest.mark.asyncio
async def test_a_tool_call_answered_before_its_caller_leaves_is_answered_in_full():
    sent = await _call(
        _app(), _invoke_body("QuickTool"), asyncio.Event(), hang_up_once_answered=True
    )

    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 200
    body = json.loads(b"".join(m.get("body", b"") for m in sent))
    assert body["output"]["value"] == "3 pages"


@pytest.mark.asyncio
async def test_a_tool_call_cancelled_for_another_reason_stays_cancelled():
    call = asyncio.ensure_future(_call(_app(), _invoke_body("LongRunningTool"), asyncio.Event()))
    await asyncio.wait_for(signals["started"].wait(), timeout=5)
    call.cancel()

    with pytest.raises(asyncio.CancelledError):
        await call

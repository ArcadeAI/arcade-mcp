import asyncio
import json
from typing import Annotated

import pytest
from arcade_core.schema import ToolCallRequest, ToolContext, ToolReference
from arcade_serve.fastapi.disconnect import CancelOnDisconnectMiddleware
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import tool
from fastapi import FastAPI
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

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


@pytest.mark.asyncio
async def test_a_request_refused_before_its_body_is_read_is_not_buffered():
    reads = 0

    async def receive():
        nonlocal reads
        reads += 1
        return {"type": "http.request", "body": b"x" * 65536, "more_body": True}

    async def refuse(scope, receive, send):
        await send({"type": "http.response.start", "status": 401, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    sent: list[dict] = []

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "path": "/worker/tools/invoke", "headers": []}
    await asyncio.wait_for(CancelOnDisconnectMiddleware(refuse)(scope, receive, send), timeout=5)

    assert sent[0]["status"] == 401
    assert reads == 0


@pytest.mark.asyncio
async def test_work_after_the_answer_is_not_cancelled_when_the_caller_leaves():
    finished = asyncio.Event()

    async def after_answer():
        await asyncio.sleep(0.05)
        finished.set()

    app = FastAPI()

    @app.post("/worker/tools/invoke")
    async def invoke():
        return JSONResponse({"ok": True}, background=BackgroundTask(after_answer))

    app.add_middleware(CancelOnDisconnectMiddleware)
    await _call(app, b"{}", asyncio.Event(), hang_up_once_answered=True)

    assert finished.is_set()


@pytest.mark.parametrize(
    ("path", "root_path", "applies"),
    [
        ("/worker/tools/invoke", "", True),
        ("/worker", "", True),
        ("/api/worker/tools/invoke", "/api", True),
        ("/workers/list", "", False),
        ("/mcp", "", False),
    ],
)
def test_only_worker_routes_are_watched(path, root_path, applies):
    middleware = CancelOnDisconnectMiddleware(lambda *_: None)

    assert middleware._applies({"type": "http", "path": path, "root_path": root_path}) is applies


@pytest.mark.asyncio
async def test_a_worker_added_to_a_running_app_still_serves(caplog):
    app = FastAPI()
    app.middleware_stack = app.build_middleware_stack()

    with caplog.at_level("WARNING"):
        worker = FastAPIWorker(app=app, disable_auth=True)

    assert worker.app is app
    assert "not cancelled" in caplog.text

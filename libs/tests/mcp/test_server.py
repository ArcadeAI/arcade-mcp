import sys
import types
from typing import Annotated, Any

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_serve.mcp import server as mcp_server
from arcade_serve.mcp.types import (
    CallToolRequest,
    CancelRequest,
    InitializeRequest,
    ListToolsRequest,
    PingRequest,
)
from arcade_tdk import tool

# ---------------------------------------------------------------------------
# Test helpers / stubs
# ---------------------------------------------------------------------------


class _FakeAuth:
    async def authorize(self, auth_requirement: Any, user_id: str):
        """Return an object that mimics AuthorizationResponse with completed status."""

        class _Ctx:  # minimal stub
            token = "dummy-token"  # noqa: S105

        class _Resp:  # pylint: disable=too-few-public-methods
            status = "completed"
            url = ""
            context = _Ctx()

        return _Resp()


class _FakeArcade:  # pylint: disable=too-few-public-methods
    def __init__(self, **_: Any):
        self.auth = _FakeAuth()


# Ensure that the AsyncArcade & ArcadeError symbols inside server.py point to our stubs.
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _patch_arcadepy(monkeypatch):
    """Patch the external `arcadepy` dependency used by mcp.server."""

    # Patch the imported symbols on the already-imported server module
    monkeypatch.setattr(mcp_server, "AsyncArcade", _FakeArcade, raising=True)
    monkeypatch.setattr(mcp_server, "ArcadeError", Exception, raising=True)

    # Provide a dummy `arcadepy` module in sys.modules for any other importers
    fake_arcadepy = types.ModuleType("arcadepy")
    fake_arcadepy.AsyncArcade = _FakeArcade  # type: ignore[attr-defined]
    fake_arcadepy.ArcadeError = Exception  # type: ignore[attr-defined]
    sys.modules["arcadepy"] = fake_arcadepy

    yield

    # Cleanup
    sys.modules.pop("arcadepy", None)


# ---------------------------------------------------------------------------
# Fixtures for a sample tool / catalog / server
# ---------------------------------------------------------------------------


@tool
def multiply(a: Annotated[int, "a"], b: Annotated[int, "b"]) -> Annotated[int, "result"]:
    """Return the product of *a* and *b*."""

    return a * b


@pytest.fixture(scope="module")
def sample_catalog():
    catalog = ToolCatalog()
    catalog.add_tool(multiply, "test_toolkit")
    return catalog


@pytest.fixture()
def server(sample_catalog):
    # MCPServer constructor is synchronous, so fixture need not be async
    return mcp_server.MCPServer(sample_catalog, enable_logging=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_handle_ping(server):
    req = PingRequest(id=123)
    resp = await server._handle_ping(req)  # pylint: disable=protected-access
    assert resp.id == 123
    assert resp.result == {"pong": True}


async def test_handle_initialize(server):
    req = InitializeRequest(id=1)
    resp = await server._handle_initialize(req)  # pylint: disable=protected-access
    assert resp.id == 1
    assert resp.result.protocolVersion == mcp_server.MCP_PROTOCOL_VERSION
    assert resp.result.serverInfo.name.startswith("Arcade")


async def test_handle_list_tools(server):
    req = ListToolsRequest(id=99)
    resp = await server._handle_list_tools(req)  # pylint: disable=protected-access
    assert resp.id == 99
    # Should list our sample tool only
    tool_names = [t.name for t in resp.result.tools]
    assert "TestToolkit_Multiply" in tool_names  # toolkit + "_" + tool


async def test_handle_call_tool_success(server):
    req = CallToolRequest(
        id="call-1",
        params={
            "name": "TestToolkit_Multiply",
            "input": {"a": 6, "b": 7},
        },
    )
    resp = await server._handle_call_tool(req, user_id="tester@example.com")  # pylint: disable=protected-access

    assert resp.id == "call-1"
    # convert_to_mcp_content wraps primitives in list-of-dicts
    assert resp.result.content == [{"type": "text", "text": "42"}]


async def test_send_response_dict(server, monkeypatch):
    """_send_response should JSON-serialize plain dictionaries."""

    sent: list[str] = []

    class _Write:
        async def send(self, msg):
            sent.append(msg)

    await server._send_response(_Write(), {"foo": "bar"})  # pylint: disable=protected-access

    assert sent and sent[0].strip() == '{"foo": "bar"}'


async def test_handle_cancel(server):
    req = CancelRequest(id=77, params={"id": "abc"})
    resp = await server._handle_cancel(req)  # pylint: disable=protected-access
    assert resp.result == {"ok": True}

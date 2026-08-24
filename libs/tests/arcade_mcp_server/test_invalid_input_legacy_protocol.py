"""Tests for invalid-input errors on the MCP 2025-06-18 (legacy) tool-call path.

Input validation failures are version-gated: 2025-11-25 clients get a
``CallToolResult(isError=True)``, 2025-06-18 clients get a JSON-RPC
``-32602``. The legacy branch used to serialize the whole ``ToolCallError``
pydantic model with ``str(error)``, which dumps every field -- including
``developer_message`` and ``stacktrace``.

That matters beyond cosmetics. Pydantic's traceback embeds ``input_value=``,
so the rejected argument was echoed back to the caller verbatim. The executor
deliberately keeps rejected values out of ``message``/``developer_message``
because they may hold secrets or PII, and ``_debug_exposure`` exists so that
stacktraces reach a client only behind an explicit opt-in env flag. The legacy
branch bypassed both.
"""

from typing import Annotated

import pytest
import pytest_asyncio
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server import _debug_exposure as debug_exposure
from arcade_mcp_server import tool
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.types import CallToolRequest, CallToolResult, JSONRPCError, JSONRPCResponse

# Read the flag names and the activation acknowledgement from the module that
# defines them rather than restating them. ``scripts/check_debug_leak_flags_off.py``
# fails the build if the ack string appears in any tracked file outside its
# allowlist, and that guard is worth keeping narrow -- so this file must not
# contain a copy of it.
_LEAK_MAGIC = debug_exposure._DEBUG_LEAK_MAGIC
_ENV_STACKTRACE = debug_exposure._ENV_EXPOSE_STACKTRACE
_ENV_DEV_MSG = debug_exposure._ENV_EXPOSE_DEVELOPER_MESSAGE

SENTINEL_ARG = "SENTINEL_ARG_VALUE_DO_NOT_LEAK_42"


@pytest.fixture(autouse=True)
def _reset_leak_state(monkeypatch):
    monkeypatch.delenv(_ENV_DEV_MSG, raising=False)
    monkeypatch.delenv(_ENV_STACKTRACE, raising=False)
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()
    yield
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()


@tool
def needs_a_list(
    tags: Annotated[list[str], "A list of tags"],
) -> Annotated[str, "Result"]:
    """Tool whose argument fails validation when given a bare string."""
    return ",".join(tags)


class _FakeSession:
    """Minimal stand-in for ServerSession with controllable protocol features."""

    def __init__(self, features: set[str]) -> None:
        self._features = features
        self.session_id = "test-session"
        # stdio keeps _check_transport_restrictions from short-circuiting the
        # call before input validation runs.
        self.init_options = {"transport_type": "stdio"}

    def has_feature(self, feature: str) -> bool:
        return feature in self._features

    def has_capability(self, capability: str) -> bool:
        return False


# Arcade derives the tool name from the function (``needs_a_list`` ->
# ``NeedsAList``), so resolve it from the catalog rather than hardcoding it --
# a wrong literal here makes the server answer "Unknown tool" and every
# absence-based assertion below would pass vacuously.
_CATALOG = ToolCatalog()
_CATALOG.add_tool(needs_a_list, "LegacyToolkit")
TOOL_FQN = str(_CATALOG.find_tool_by_func(needs_a_list).get_fully_qualified_name())


@pytest_asyncio.fixture
async def server():
    srv = MCPServer(
        catalog=_CATALOG,
        name="Legacy Input Server",
        version="0.0.0",
        settings=MCPSettings(),
    )
    await srv.start()
    try:
        yield srv
    finally:
        await srv.stop()


async def _call_with_bad_input(srv, session):
    return await srv._handle_call_tool(
        CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": TOOL_FQN, "arguments": {"tags": SENTINEL_ARG}},
        ),
        session=session,
    )


def _legacy_error_text(response) -> str:
    assert isinstance(response, JSONRPCError), f"expected JSONRPCError, got {type(response)}"
    error = response.error
    text = error["message"] if isinstance(error, dict) else error.message
    # Anchor: if the call never reached input validation (e.g. "Unknown tool"),
    # the absence assertions in this module would pass for the wrong reason.
    assert "Invalid input" in text, f"did not reach input validation; got: {text!r}"
    return text


class TestLegacyPathDoesNotLeakInternals:
    @pytest.mark.asyncio
    async def test_rejected_argument_value_is_not_echoed(self, server):
        """The reported class of bug: the rejected value must not reach the client."""
        response = await _call_with_bad_input(server, _FakeSession(set()))
        assert SENTINEL_ARG not in _legacy_error_text(response)

    @pytest.mark.asyncio
    async def test_stacktrace_is_not_exposed_without_the_flag(self, server):
        text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))
        assert "Traceback" not in text
        assert "stacktrace=" not in text

    @pytest.mark.asyncio
    async def test_model_repr_fields_are_not_dumped(self, server):
        """``str(ToolCallError)`` renders ``field=value`` pairs; the client must
        receive a message, not a model dump."""
        text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))
        for leaked_field in ("kind=", "developer_message=", "can_retry=", "status_code="):
            assert leaked_field not in text, f"{leaked_field!r} leaked into the client message"

    @pytest.mark.asyncio
    async def test_message_is_still_actionable(self, server):
        """Suppressing internals must not strip the useful part."""
        text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))
        assert "Invalid input" in text
        assert "tags" in text


class TestLegacyPathHonorsDebugFlags:
    @pytest.mark.asyncio
    async def test_stacktrace_appears_only_when_flag_is_set(self, server, monkeypatch):
        """The escape hatch must still work on the legacy path -- the fix routes
        through ``augment_error_message_for_debug`` rather than dropping it."""
        monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
        text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))
        assert "[DEBUG] stacktrace:" in text

    @pytest.mark.asyncio
    async def test_developer_message_appears_only_when_flag_is_set(self, server, monkeypatch):
        monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
        text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))
        assert "[DEBUG] developer_message:" in text


class TestModernPathUnchanged:
    @pytest.mark.asyncio
    async def test_modern_session_still_gets_call_tool_result(self, server):
        """2025-11-25 clients keep the CallToolResult shape, and stay leak-free."""
        response = await _call_with_bad_input(server, _FakeSession({"tool_execution"}))
        assert isinstance(response, JSONRPCResponse)
        assert isinstance(response.result, CallToolResult)
        assert response.result.isError is True
        text = response.result.content[0].text
        assert "Invalid input" in text
        assert SENTINEL_ARG not in text


class TestLegacyPathKeepsRetryGuidance:
    @pytest.mark.asyncio
    async def test_additional_prompt_content_reaches_the_client(self, server):
        """``additional_prompt_content`` is guidance authored for the caller, not
        an internal — so suppressing internals must not drop it. The 2025-11-25
        branch appends it, and this branch has to match; a bad-input error does
        not carry it today, so drive it through a crafted executor result."""
        from unittest.mock import patch

        from arcade_core.errors import ErrorKind
        from arcade_core.schema import ToolCallError, ToolCallOutput

        crafted = ToolCallOutput(
            error=ToolCallError(
                message="Invalid input: tags: Input should be a valid list",
                kind=ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE,
                developer_message="internal detail that must stay hidden",
                additional_prompt_content="Pass tags as a JSON array, e.g. [\"a\", \"b\"].",
                stacktrace="Traceback (most recent call last): ...",
                status_code=400,
            )
        )

        with patch(
            "arcade_mcp_server.server.ToolExecutor.run",
            return_value=crafted,
        ):
            text = _legacy_error_text(await _call_with_bad_input(server, _FakeSession(set())))

        assert 'Pass tags as a JSON array, e.g. ["a", "b"].' in text
        # ...while the internals stay gated behind the debug flags.
        assert "internal detail that must stay hidden" not in text
        assert "Traceback" not in text

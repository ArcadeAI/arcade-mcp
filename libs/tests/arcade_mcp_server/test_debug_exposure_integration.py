"""End-to-end integration tests for the MCP debug-exposure escape hatch.

These complement the pure-function unit tests in ``test_debug_exposure.py`` by
exercising the full MCP tool-call path:

    tool raises -> ToolExecutor.run -> ToolOutputFactory.fail ->
    MCPServer._call_tool -> augment_error_message_for_debug ->
    CallToolResult.content[0].text

This is the path every real MCP client hits, so it's where regressions in the
wire-up (wrong call site, wrong argument order, missing import, etc.) would
actually surface. The unit tests can't catch those because they call the pure
function directly.
"""

from typing import Annotated

import pytest
import pytest_asyncio
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.errors import FatalToolError
from arcade_core.schema import (
    InputParameter,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)
from arcade_mcp_server import _debug_exposure as debug_exposure
from arcade_mcp_server import tool
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.types import CallToolRequest, CallToolResult, JSONRPCResponse

_LEAK_MAGIC = "yes-i-accept-leaking-internals-to-the-agent"
_ENV_DEV_MSG = "ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES"
_ENV_STACKTRACE = "ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES"


@pytest.fixture(autouse=True)
def _reset_leak_state(monkeypatch):
    monkeypatch.delenv(_ENV_DEV_MSG, raising=False)
    monkeypatch.delenv(_ENV_STACKTRACE, raising=False)
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()
    yield
    debug_exposure._warned_rejected.clear()
    debug_exposure._warned_activated.clear()


# ---- Tool definitions used by the integration tests -------------------------


@tool
def raises_fatal_tool_error(
    query: Annotated[str, "A query"],
) -> Annotated[str, "Result"]:
    """Simulates a toolkit author's tool failing with a rich error."""
    raise FatalToolError(
        message="Failed to fetch results",
        developer_message=f"HTTP 503 on upstream endpoint for query={query!r}",
    )


@tool
def raises_unhandled_exception(
    query: Annotated[str, "A query"],
) -> Annotated[str, "Result"]:
    """Simulates a toolkit author's tool crashing with an unexpected exception.

    The executor's generic `except Exception` branch populates the stacktrace
    via `traceback.format_exc()`, which is what the stacktrace flag leaks.
    """
    raise ValueError(f"unexpected crash for query={query!r}")


def _materialized(func, name: str) -> MaterializedTool:
    definition = ToolDefinition(
        name=name,
        fully_qualified_name=f"TestToolkit.{name}",
        description=f"{name} integration fixture",
        toolkit=ToolkitDefinition(name="TestToolkit", description="", version="1.0.0"),
        input=ToolInput(
            parameters=[
                InputParameter(
                    name="query",
                    required=True,
                    description="A query",
                    value_schema=ValueSchema(val_type="string"),
                ),
            ]
        ),
        output=ToolOutput(
            description="Result",
            value_schema=ValueSchema(val_type="string"),
        ),
        requirements=ToolRequirements(),
    )
    input_model, output_model = create_func_models(func)
    return MaterializedTool(
        tool=func,
        definition=definition,
        meta=ToolMeta(module=func.__module__, toolkit="TestToolkit"),
        input_model=input_model,
        output_model=output_model,
    )


@pytest.fixture
def erroring_catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    mt1 = _materialized(raises_fatal_tool_error, "raises_fatal_tool_error")
    mt2 = _materialized(raises_unhandled_exception, "raises_unhandled_exception")
    catalog._tools[mt1.definition.get_fully_qualified_name()] = mt1
    catalog._tools[mt2.definition.get_fully_qualified_name()] = mt2
    return catalog


@pytest_asyncio.fixture
async def erroring_server(erroring_catalog) -> MCPServer:
    settings = MCPSettings()
    settings.middleware.mask_error_details = False
    server = MCPServer(
        catalog=erroring_catalog,
        name="Integration Debug Exposure Server",
        version="0.0.0",
        settings=settings,
    )
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


async def _call(erroring_server: MCPServer, tool_name: str) -> CallToolResult:
    message = CallToolRequest(
        jsonrpc="2.0",
        id=1,
        method="tools/call",
        params={"name": f"TestToolkit.{tool_name}", "arguments": {"query": "ping"}},
    )
    response = await erroring_server._handle_call_tool(message)
    assert isinstance(response, JSONRPCResponse)
    assert isinstance(response.result, CallToolResult)
    assert response.result.isError is True
    assert response.result.structuredContent is None
    return response.result


# ---- Integration tests ------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_baseline_no_leak(erroring_server):
    """Default state: the agent sees ONLY the sanitized message."""
    result = await _call(erroring_server, "raises_fatal_tool_error")
    text = result.content[0].text
    assert "Failed to fetch results" in text
    assert "[DEBUG]" not in text
    assert "HTTP 503" not in text
    assert "query='ping'" not in text


@pytest.mark.asyncio
async def test_integration_boolean_rejected_no_leak(erroring_server, monkeypatch, caplog):
    """Boolean-looking values are rejected by the MCP boundary too."""
    monkeypatch.setenv(_ENV_DEV_MSG, "true")
    import logging

    with caplog.at_level(logging.WARNING, logger="arcade_mcp_server._debug_exposure"):
        result = await _call(erroring_server, "raises_fatal_tool_error")
    text = result.content[0].text
    assert "Failed to fetch results" in text
    assert "[DEBUG]" not in text
    assert "HTTP 503" not in text
    assert any(
        "set to a truthy value but not to the required" in r.message for r in caplog.records
    )


@pytest.mark.asyncio
async def test_integration_developer_message_flag_leaks_through_mcp(
    erroring_server, monkeypatch
):
    """When the flag is set to the magic value, the MCP response `content`
    carries `developer_message` alongside the sanitized message."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    result = await _call(erroring_server, "raises_fatal_tool_error")
    text = result.content[0].text
    assert "Failed to fetch results" in text
    assert "[DEBUG] developer_message:" in text
    assert "HTTP 503 on upstream endpoint for query='ping'" in text
    # Stacktrace flag is off — stacktrace must NOT leak.
    assert "[DEBUG] stacktrace:" not in text


@pytest.mark.asyncio
async def test_integration_stacktrace_flag_leaks_traceback_through_mcp(
    erroring_server, monkeypatch
):
    """Unhandled exceptions go through the executor's generic except branch,
    which populates a real stacktrace. With the flag on, that stacktrace must
    appear in the MCP response content."""
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    result = await _call(erroring_server, "raises_unhandled_exception")
    text = result.content[0].text
    # The generic-exception branch wraps the message with the tool name.
    assert "raises_unhandled_exception" in text
    assert "[DEBUG] stacktrace:" in text
    assert "Traceback" in text
    assert "ValueError" in text
    assert "unexpected crash for query='ping'" in text


@pytest.mark.asyncio
async def test_integration_both_flags_leak_through_mcp(erroring_server, monkeypatch):
    """Both flags together on an unhandled exception: developer_message (from
    `str(e)` in the executor) AND the stacktrace both reach the MCP content."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    result = await _call(erroring_server, "raises_unhandled_exception")
    text = result.content[0].text
    assert "[DEBUG] developer_message:" in text
    assert "unexpected crash for query='ping'" in text
    assert "[DEBUG] stacktrace:" in text
    assert "Traceback" in text


@pytest.mark.asyncio
async def test_integration_success_path_unaffected_by_flags(
    tool_catalog, mcp_settings, monkeypatch
):
    """Sanity check: even with both flags on, SUCCESSFUL tool responses are
    not touched. The augmentation only runs on the error branch."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    server = MCPServer(
        catalog=tool_catalog,
        name="Success Path Server",
        version="0.0.0",
        settings=mcp_settings,
    )
    await server.start()
    try:
        response = await server._handle_call_tool(
            CallToolRequest(
                jsonrpc="2.0",
                id=1,
                method="tools/call",
                params={"name": "TestToolkit.test_tool", "arguments": {"text": "hi"}},
            )
        )
    finally:
        await server.stop()
    assert isinstance(response, JSONRPCResponse)
    assert isinstance(response.result, CallToolResult)
    assert response.result.isError is False
    assert response.result.structuredContent is not None
    for item in response.result.content:
        assert "[DEBUG]" not in getattr(item, "text", "")

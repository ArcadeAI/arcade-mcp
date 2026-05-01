from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool

catalog = ToolCatalog()


@tool
def keyerror_tool() -> Annotated[str, "output"]:
    """Tool that raises a bare KeyError"""
    raise KeyError("x")


@tool
def empty_exception_tool() -> Annotated[str, "output"]:
    """Tool that raises an exception with no message"""
    raise Exception()


@tool
def fallback_with_secret_in_exception_tool() -> Annotated[str, "output"]:
    """Tool that raises an exception whose ``str()`` contains a fake secret.

    Used to verify the strict data-leak policy: the secret must NEVER appear
    in the agent-facing ``message``. It is allowed in ``developer_message``,
    which is server-side only (Datadog facet, never returned to the MCP client).
    """
    raise RuntimeError("Bad credentials for alice: password=hunter2_SECRET_PII")


catalog.add_tool(keyerror_tool, "ErrorFallbackToolkit")
catalog.add_tool(empty_exception_tool, "ErrorFallbackToolkit")
catalog.add_tool(fallback_with_secret_in_exception_tool, "ErrorFallbackToolkit")


@pytest.mark.asyncio
async def test_fallback_message_contains_type_but_not_exception_string():
    """The agent-facing ``message`` must include the exception **type**
    (so agents know what class of failure occurred) but must NOT include
    ``str(exception)`` content — that's what the data-leak policy reserves
    for ``developer_message``."""
    tool_definition = catalog.find_tool_by_func(keyerror_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())

    output = await ToolExecutor.run(
        func=keyerror_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=ToolContext(),
    )

    assert output.error is not None
    # Type IS present (safe: class names are source-defined).
    assert "KeyError" in output.error.message
    # The hint to use FatalToolError is present.
    assert "FatalToolError" in output.error.message
    # The exception string content (``str(KeyError('x'))`` == ``"'x'"``) is NOT.
    # Stricter: no quoted argument representation should appear.
    assert "'x'" not in output.error.message


@pytest.mark.asyncio
async def test_fallback_message_never_leaks_exception_str_content():
    """Strict data-leak policy: even if the tool author embeds secrets in
    ``str(exception)``, the agent-facing ``message`` MUST NOT contain them.
    The full content is preserved in ``developer_message`` (server-side
    logs only) so on-call engineers retain debugging context."""
    tool_definition = catalog.find_tool_by_func(fallback_with_secret_in_exception_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())

    output = await ToolExecutor.run(
        func=fallback_with_secret_in_exception_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=ToolContext(),
    )

    assert output.error is not None

    # ── Agent-facing channel: nothing from str(exception) leaks ──
    assert "hunter2_SECRET_PII" not in output.error.message
    assert "alice" not in output.error.message
    assert "password=" not in output.error.message
    assert "Bad credentials" not in output.error.message
    # Type still present so the agent knows what failed.
    assert "RuntimeError" in output.error.message

    # ── Server-side log channel: full content preserved for debugging ──
    assert output.error.developer_message is not None
    assert "hunter2_SECRET_PII" in output.error.developer_message
    assert "RuntimeError" in output.error.developer_message


@pytest.mark.asyncio
async def test_fallback_developer_message_carries_full_exception_content():
    """``developer_message`` (server-side log only) is where verbose exception
    content lives — type + str(exception) — so engineers can debug."""
    tool_definition = catalog.find_tool_by_func(keyerror_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())

    output = await ToolExecutor.run(
        func=keyerror_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=ToolContext(),
    )

    assert output.error is not None
    assert output.error.developer_message is not None
    assert "KeyError" in output.error.developer_message
    # The KeyError argument IS present in developer_message (vs absent in message).
    assert "'x'" in output.error.developer_message


@pytest.mark.asyncio
async def test_fallback_empty_exception_developer_message_marks_no_details():
    """Empty exceptions (``raise Exception()``) get a ``(no exception message)``
    marker in ``developer_message`` so on-call engineers can distinguish
    'nothing to log' from 'log was lost'."""
    tool_definition = catalog.find_tool_by_func(empty_exception_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())

    output = await ToolExecutor.run(
        func=empty_exception_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=ToolContext(),
    )

    assert output.error is not None
    assert output.error.developer_message is not None
    assert "Exception (no exception message)" in output.error.developer_message

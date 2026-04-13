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


catalog.add_tool(keyerror_tool, "ErrorFallbackToolkit")
catalog.add_tool(empty_exception_tool, "ErrorFallbackToolkit")


@pytest.mark.asyncio
async def test_fallback_keyerror_includes_type():
    tool_definition = catalog.find_tool_by_func(keyerror_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    dummy_context = ToolContext()

    output = await ToolExecutor.run(
        func=keyerror_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
    )

    assert output.error is not None
    assert "KeyError" in output.error.message


@pytest.mark.asyncio
async def test_fallback_empty_exception_shows_type():
    tool_definition = catalog.find_tool_by_func(empty_exception_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    dummy_context = ToolContext()

    output = await ToolExecutor.run(
        func=empty_exception_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
    )

    assert output.error is not None
    assert "Exception (no details)" in output.error.message


@pytest.mark.asyncio
async def test_fallback_developer_message_is_static_sentinel():
    """The fallback path sets a static developer_message sentinel rather than
    repr(exception), which would just near-duplicate ``message`` (e.g.
    ``"KeyError: 'x'"`` vs ``"KeyError('x')"``) and waste a Datadog facet."""
    tool_definition = catalog.find_tool_by_func(keyerror_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    dummy_context = ToolContext()

    output = await ToolExecutor.run(
        func=keyerror_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
    )

    assert output.error is not None
    assert output.error.developer_message is not None
    # The sentinel string is preserved (with prefix prepended by with_context).
    assert "No additional context available" in output.error.developer_message
    # Crucially, repr-style content is NOT in developer_message (no near-duplication
    # of the ``message`` content).
    assert "KeyError('x')" not in output.error.developer_message


@pytest.mark.asyncio
async def test_fallback_empty_exception_has_sentinel_developer_message():
    """Empty exceptions also get the static sentinel — same uniform contract."""
    tool_definition = catalog.find_tool_by_func(empty_exception_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    dummy_context = ToolContext()

    output = await ToolExecutor.run(
        func=empty_exception_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
    )

    assert output.error is not None
    assert output.error.developer_message is not None
    assert "No additional context available" in output.error.developer_message


@tool
def fallback_with_str_exception_tool() -> Annotated[str, "output"]:
    """Tool that raises with a deterministic exception string."""
    raise RuntimeError("CONNECTION_REFUSED_TO_HOST_X")


catalog.add_tool(fallback_with_str_exception_tool, "ErrorFallbackToolkit")


@pytest.mark.asyncio
async def test_fallback_message_only_contains_exception_type_and_str():
    """The framework's fallback path must surface ONLY ``{ExceptionType}:
    {str(exception)}`` plus the prefix from with_context — it must never
    inject any extra context (call args, environment, etc.). This locks the
    data-leak boundary documented on _raise_as_arcade_error: tool authors
    own what's in their exception message; the framework adds no more."""
    tool_definition = catalog.find_tool_by_func(fallback_with_str_exception_tool)
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    dummy_context = ToolContext()

    output = await ToolExecutor.run(
        func=fallback_with_str_exception_tool,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
    )

    assert output.error is not None
    msg = output.error.message
    # The message must end with exactly ``{ExceptionType}: {str(exception)}``,
    # no trailing extra context.
    assert msg.endswith("RuntimeError: CONNECTION_REFUSED_TO_HOST_X")
    # The prefix must come from create_message_prefix (known shape) — nothing
    # between the prefix and the exception summary.
    assert msg == (
        "[TOOL_RUNTIME_FATAL] FatalToolError during execution of tool "
        "'fallback_with_str_exception_tool': RuntimeError: CONNECTION_REFUSED_TO_HOST_X"
    )

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
async def test_fallback_developer_message_is_repr():
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
    # developer_message has the prefix from with_context, but ends with repr(exception)
    assert "KeyError('x')" in output.error.developer_message

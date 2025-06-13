from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolCallError, ToolCallLog, ToolCallOutput, ToolContext
from arcade_tdk import tool
from arcade_tdk.errors import RetryableToolError, ToolExecutionError


@tool
def simple_tool(inp: Annotated[str, "input"]) -> Annotated[str, "output"]:
    """Simple tool"""
    return inp


@tool.deprecated("Use simple_tool instead")
@tool
def simple_deprecated_tool(inp: Annotated[str, "input"]) -> Annotated[str, "output"]:
    """Simple tool that is deprecated"""
    return inp


@tool
def retryable_error_tool() -> Annotated[str, "output"]:
    """Tool that raises a retryable error"""
    raise RetryableToolError("test", "test", "test", 1000)


@tool
def exec_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an error"""
    raise ToolExecutionError("test", "test")


@tool
def unexpected_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an unexpected error"""
    raise RuntimeError("test")


@tool
def bad_output_error_tool() -> Annotated[str, "output"]:
    """tool that returns a bad output type"""
    return {"output": "test"}


# ---- Test Driver ----

catalog = ToolCatalog()
catalog.add_tool(simple_tool, "simple_toolkit")
catalog.add_tool(simple_deprecated_tool, "simple_toolkit")
catalog.add_tool(retryable_error_tool, "simple_toolkit")
catalog.add_tool(exec_error_tool, "simple_toolkit")
catalog.add_tool(unexpected_error_tool, "simple_toolkit")
catalog.add_tool(bad_output_error_tool, "simple_toolkit")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_func, inputs, expected_output",
    [
        (simple_tool, {"inp": "test"}, ToolCallOutput(value="test")),
        (
            simple_deprecated_tool,
            {"inp": "test"},
            ToolCallOutput(
                value="test",
                logs=[
                    ToolCallLog(
                        message="Use simple_tool instead",
                        level="warning",
                        subtype="deprecation",
                    )
                ],
            ),
        ),
        (
            retryable_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="test",
                    developer_message="test",
                    additional_prompt_content="test",
                    retry_after_ms=1000,
                    can_retry=True,
                )
            ),
        ),
        (
            exec_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="test",
                    developer_message="test",
                )
            ),
        ),
        (
            unexpected_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="Error in execution of UnexpectedErrorTool",
                    developer_message="Error in unexpected_error_tool: test",
                )
            ),
        ),
        (
            simple_tool,
            {"inp": {"test": "test"}},  # takes in a string not a dict
            ToolCallOutput(
                error=ToolCallError(
                    message="Error in tool input deserialization",
                    developer_message=None,  # can't gaurantee this will be the same
                )
            ),
        ),
        (
            bad_output_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="Failed to serialize tool output",
                    developer_message=None,  # can't gaurantee this will be the same
                )
            ),
        ),
    ],
    ids=[
        "simple_tool",
        "simple_deprecated_tool",
        "retryable_error_tool",
        "exec_error_tool",
        "unexpected_error_tool",
        "invalid_input_type",
        "bad_output_type",
    ],
)
async def test_tool_executor(tool_func, inputs, expected_output):
    tool_definition = catalog.find_tool_by_func(tool_func)

    dummy_context = ToolContext()
    full_tool = catalog.get_tool(tool_definition.get_fully_qualified_name())
    output = await ToolExecutor.run(
        func=tool_func,
        definition=tool_definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=dummy_context,
        **inputs,
    )

    check_output(output, expected_output)


def check_output(output: ToolCallOutput, expected_output: ToolCallOutput):
    # execution error in tool
    if output.error:
        assert output.error.message == expected_output.error.message
        if expected_output.error.developer_message:
            assert output.error.developer_message == expected_output.error.developer_message
        if expected_output.error.traceback_info:
            assert output.error.traceback_info == expected_output.error.traceback_info
        assert output.error.can_retry == expected_output.error.can_retry
        assert (
            output.error.additional_prompt_content
            == expected_output.error.additional_prompt_content
        )
        assert output.error.retry_after_ms == expected_output.error.retry_after_ms

    # normal tool execution
    else:
        assert output.value == expected_output.value

        # check logs
        output_logs = output.logs or []
        expected_logs = expected_output.logs or []
        assert len(output_logs) == len(expected_logs)
        for output_log, expected_log in zip(output_logs, expected_logs):
            assert output_log.message == expected_log.message
            assert output_log.level == expected_log.level
            assert output_log.subtype == expected_log.subtype

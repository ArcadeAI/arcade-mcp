from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import (
    ContextRequiredToolError,
    ErrorCode,
    ErrorOrigin,
    ErrorPhase,
    UpstreamError,
    UpstreamRateLimitError,
)
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolCallError, ToolCallLog, ToolCallOutput, ToolContext
from arcade_tdk import tool
from arcade_tdk.errors import (
    RetryableToolError,
    ToolExecutionError,
)


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
    raise RetryableToolError("test", "test", "additional prompt content", 1000)


@tool
def tool_execution_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an error"""
    raise ToolExecutionError("test", "test")


@tool
def unexpected_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an unexpected error"""
    raise RuntimeError("test")


@tool
def context_required_error_tool() -> Annotated[str, "output"]:
    """Tool that raises a context required error"""
    raise ContextRequiredToolError(
        "test", additional_prompt_content="need the user to clarify something"
    )


@tool
def upstream_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an upstream error"""
    # TODO: or test raising a httpx error? Do these types of tests belong in adapter tests?
    raise UpstreamError("test", status_code=400)


@tool
def upstream_ratelimit_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an upstream error"""
    # TODO: or test raising a httpx error? Do these types of tests belong in adapter tests?
    raise UpstreamRateLimitError("test", 1000)


@tool
def bad_output_error_tool() -> Annotated[str, "output"]:
    """tool that returns a bad output type"""
    return {"output": "test"}


# ---- Test Driver ----

catalog = ToolCatalog()
catalog.add_tool(simple_tool, "simple_toolkit")
catalog.add_tool(simple_deprecated_tool, "simple_toolkit")
catalog.add_tool(retryable_error_tool, "simple_toolkit")
catalog.add_tool(tool_execution_error_tool, "simple_toolkit")
catalog.add_tool(unexpected_error_tool, "simple_toolkit")
catalog.add_tool(context_required_error_tool, "simple_toolkit")
catalog.add_tool(upstream_error_tool, "simple_toolkit")
catalog.add_tool(upstream_ratelimit_error_tool, "simple_toolkit")
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
                    message="[TOOL_RUNTIME_RETRY_TOOL] RetryableToolError in execution of tool 'retryable_error_tool': test",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.RETRY_TOOL,
                    developer_message="[TOOL_RUNTIME_RETRY_TOOL] RetryableToolError in execution of tool 'retryable_error_tool': test",
                    additional_prompt_content="additional prompt content",
                    retry_after_ms=1000,
                    can_retry=True,
                )
            ),
        ),
        (
            tool_execution_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_FATAL] ToolExecutionError in execution of tool 'tool_execution_error_tool': test",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.FATAL,
                    developer_message="[TOOL_RUNTIME_FATAL] ToolExecutionError in execution of tool 'tool_execution_error_tool': test",
                    can_retry=False,
                )
            ),
        ),
        (
            unexpected_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_FATAL] FatalToolError in execution of tool 'unexpected_error_tool': test",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.FATAL,
                    developer_message="[TOOL_RUNTIME_FATAL] FatalToolError in execution of tool 'unexpected_error_tool': test",
                    can_retry=False,
                )
            ),
        ),
        (
            simple_tool,
            {"inp": {"test": "test"}},  # takes in a string not a dict
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError in execution of tool 'simple_tool': Error in tool input deserialization",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.BAD_INPUT_VALUE,
                    status_code=400,
                    developer_message=None,  # can't gaurantee this will be the same
                )
            ),
        ),
        (
            context_required_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_CONTEXT_REQUIRED] ContextRequiredToolError in execution of tool 'context_required_error_tool': test",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.CONTEXT_REQUIRED,
                    developer_message=None,
                    additional_prompt_content="need the user to clarify something",
                )
            ),
        ),
        (
            upstream_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[UPSTREAM_RUNTIME_BAD_REQUEST] UpstreamError in execution of tool 'upstream_error_tool': test",
                    origin=ErrorOrigin.UPSTREAM,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.BAD_REQUEST,
                    status_code=400,
                    developer_message=None,
                )
            ),
        ),
        (
            upstream_ratelimit_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[UPSTREAM_RUNTIME_RATE_LIMIT] UpstreamRateLimitError in execution of tool 'upstream_ratelimit_error_tool': test",
                    origin=ErrorOrigin.UPSTREAM,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.RATE_LIMIT,
                    status_code=429,
                    developer_message=None,
                    retry_after_ms=1000,
                    can_retry=True,
                )
            ),
        ),
        (
            bad_output_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_BAD_OUTPUT_VALUE] ToolOutputError in execution of tool 'bad_output_error_tool': Failed to serialize tool output",
                    origin=ErrorOrigin.TOOL,
                    phase=ErrorPhase.RUNTIME,
                    code=ErrorCode.BAD_OUTPUT_VALUE,
                    status_code=500,
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
        "context_required_error_tool",
        "upstream_error_tool",
        "upstream_ratelimit_error_tool",
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
        assert output.error.message == expected_output.error.message, "message mismatch"
        if expected_output.error.developer_message:
            assert (
                output.error.developer_message == expected_output.error.developer_message
            ), "developer message mismatch"
        if expected_output.error.stacktrace:
            assert (
                output.error.stacktrace == expected_output.error.stacktrace
            ), "stacktrace mismatch"
        assert output.error.can_retry == expected_output.error.can_retry, "can retry mismatch"
        assert (
            output.error.additional_prompt_content
            == expected_output.error.additional_prompt_content
        ), "additional prompt content mismatch"
        assert (
            output.error.retry_after_ms == expected_output.error.retry_after_ms
        ), "retry after ms mismatch"

    # normal tool execution
    else:
        assert output.value == expected_output.value

        # check logs
        output_logs = output.logs or []
        expected_logs = expected_output.logs or []
        assert len(output_logs) == len(expected_logs)
        for output_log, expected_log in zip(output_logs, expected_logs, strict=False):
            assert output_log.message == expected_log.message
            assert output_log.level == expected_log.level
            assert output_log.subtype == expected_log.subtype

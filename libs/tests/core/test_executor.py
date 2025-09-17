from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import (
    ContextRequiredToolError,
    ErrorKind,
    ToolRuntimeError,
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
from typing_extensions import TypedDict


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
    raise RetryableToolError("test", "test developer message", "additional prompt content", 1000)


@tool
def tool_execution_error_tool() -> Annotated[str, "output"]:
    """Tool that raises an error"""
    raise ToolExecutionError("test", "test developer message")


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
def tool_runtime_error_tool() -> Annotated[str, "output"]:
    """Tool that raises a tool runtime error"""
    raise ToolRuntimeError("test", "test developer message")


@tool
def bad_output_error_tool() -> Annotated[str, "output"]:
    """tool that returns a bad output type"""
    return {"output": "test"}


# TypedDict output tools
class ResultDict(TypedDict):
    """Result dictionary."""

    status: str
    count: int
    items: list[str]


@tool
def typeddict_output_tool() -> Annotated[ResultDict, "Returns a TypedDict"]:
    """Tool that returns a TypedDict."""
    return ResultDict(status="success", count=3, items=["a", "b", "c"])


@tool
def list_typeddict_output_tool() -> Annotated[list[ResultDict], "Returns list of TypedDict"]:
    """Tool that returns a list of TypedDict."""
    return [
        ResultDict(status="first", count=1, items=["x"]),
        ResultDict(status="second", count=2, items=["y", "z"]),
    ]


@tool
def dict_output_tool() -> Annotated[dict, "Returns a plain dict"]:
    """Tool that returns a plain dict."""
    return {"key": "value", "number": 42, "nested": {"inner": "data"}}


# ---- Test Driver ----
tools = [
    simple_tool,
    simple_deprecated_tool,
    retryable_error_tool,
    tool_execution_error_tool,
    unexpected_error_tool,
    context_required_error_tool,
    upstream_error_tool,
    upstream_ratelimit_error_tool,
    tool_runtime_error_tool,
    bad_output_error_tool,
    typeddict_output_tool,
    list_typeddict_output_tool,
    dict_output_tool,
]
catalog = ToolCatalog()
for tool_func in tools:
    catalog.add_tool(tool_func, "simple_toolkit")


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
                    message="[TOOL_RUNTIME_RETRY] RetryableToolError during execution of tool 'retryable_error_tool': test",
                    kind=ErrorKind.TOOL_RUNTIME_RETRY,
                    developer_message="[TOOL_RUNTIME_RETRY] RetryableToolError during execution of tool 'retryable_error_tool': test developer message",
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
                    message="[TOOL_RUNTIME_FATAL] ToolExecutionError during execution of tool 'tool_execution_error_tool': test",
                    kind=ErrorKind.TOOL_RUNTIME_FATAL,
                    developer_message="[TOOL_RUNTIME_FATAL] ToolExecutionError during execution of tool 'tool_execution_error_tool': test developer message",
                    can_retry=False,
                )
            ),
        ),
        (
            unexpected_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_FATAL] FatalToolError during execution of tool 'unexpected_error_tool': test",
                    kind=ErrorKind.TOOL_RUNTIME_FATAL,
                    developer_message="[TOOL_RUNTIME_FATAL] FatalToolError during execution of tool 'unexpected_error_tool': test",
                    can_retry=False,
                    status_code=500,
                )
            ),
        ),
        (
            simple_tool,
            {"inp": {"test": "test"}},  # takes in a string not a dict
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError during execution of tool 'simple_tool': Error in tool input deserialization",
                    kind=ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE,
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
                    message="[TOOL_RUNTIME_CONTEXT_REQUIRED] ContextRequiredToolError during execution of tool 'context_required_error_tool': test",
                    kind=ErrorKind.TOOL_RUNTIME_CONTEXT_REQUIRED,
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
                    message="[UPSTREAM_RUNTIME_BAD_REQUEST] UpstreamError during execution of tool 'upstream_error_tool': test",
                    kind=ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST,
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
                    message="[UPSTREAM_RUNTIME_RATE_LIMIT] UpstreamRateLimitError during execution of tool 'upstream_ratelimit_error_tool': test",
                    kind=ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT,
                    status_code=429,
                    developer_message=None,
                    retry_after_ms=1000,
                    can_retry=True,
                )
            ),
        ),
        (
            tool_runtime_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_FATAL] ToolRuntimeError during execution of tool 'tool_runtime_error_tool': test",
                    kind=ErrorKind.TOOL_RUNTIME_FATAL,
                    developer_message="[TOOL_RUNTIME_FATAL] ToolRuntimeError during execution of tool 'tool_runtime_error_tool': test developer message",
                    can_retry=False,
                )
            ),
        ),
        (
            bad_output_error_tool,
            {},
            ToolCallOutput(
                error=ToolCallError(
                    message="[TOOL_RUNTIME_BAD_OUTPUT_VALUE] ToolOutputError during execution of tool 'bad_output_error_tool': Failed to serialize tool output",
                    kind=ErrorKind.TOOL_RUNTIME_BAD_OUTPUT_VALUE,
                    status_code=500,
                    developer_message=None,  # can't gaurantee this will be the same
                )
            ),
        ),
        (
            typeddict_output_tool,
            {},
            ToolCallOutput(value={"status": "success", "count": 3, "items": ["a", "b", "c"]}),
        ),
        (
            list_typeddict_output_tool,
            {},
            ToolCallOutput(
                value=[
                    {"status": "first", "count": 1, "items": ["x"]},
                    {"status": "second", "count": 2, "items": ["y", "z"]},
                ]
            ),
        ),
        (
            dict_output_tool,
            {},
            ToolCallOutput(value={"key": "value", "number": 42, "nested": {"inner": "data"}}),
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
        "tool_runtime_error_tool",
        "bad_output_type",
        "typeddict_output",
        "list_typeddict_output",
        "dict_output",
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


def check_output_error(output_error: ToolCallError, expected_error: ToolCallError):
    assert output_error.message == expected_error.message, "message mismatch"
    assert output_error.kind == expected_error.kind, "kind mismatch"
    if expected_error.developer_message:
        assert (
            output_error.developer_message == expected_error.developer_message
        ), "developer message mismatch"
    assert output_error.can_retry == expected_error.can_retry, "can retry mismatch"
    assert (
        output_error.additional_prompt_content == expected_error.additional_prompt_content
    ), "additional prompt content mismatch"
    assert output_error.retry_after_ms == expected_error.retry_after_ms, "retry after ms mismatch"
    if expected_error.stacktrace:
        assert output_error.stacktrace == expected_error.stacktrace, "stacktrace mismatch"
    assert output_error.status_code == expected_error.status_code, "status code mismatch"
    assert output_error.extra == expected_error.extra, "extra mismatch"


def check_output(output: ToolCallOutput, expected_output: ToolCallOutput):
    # error in ToolCallOutput
    if output.error:
        check_output_error(output.error, expected_output.error)

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

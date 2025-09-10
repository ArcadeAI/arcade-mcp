from typing import Any, TypeVar

from pydantic import BaseModel

from arcade_core.errors import ErrorKind
from arcade_core.schema import ToolCallError, ToolCallLog, ToolCallOutput
from arcade_core.utils import coerce_empty_list_to_none

T = TypeVar("T")


class ToolOutputFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    def success(
        self,
        *,
        data: T | None = None,
        logs: list[ToolCallLog] | None = None,
    ) -> ToolCallOutput:
        # Extract the result value
        """
        Extracts the result value for the tool output.

        The executor guarantees that `data` is either a string, a dict, or None.
        """
        value: str | int | float | bool | dict | list | None
        if data is None:
            value = ""
        elif hasattr(data, "result"):
            result = getattr(data, "result", "")
            # Handle None result the same way as None data
            if result is None:
                value = ""
            # If the result is a BaseModel (e.g., from TypedDict conversion), convert to dict
            elif isinstance(result, BaseModel):
                value = result.model_dump()
            # If the result is a list, check if it contains BaseModel objects
            elif isinstance(result, list):
                value = [
                    item.model_dump() if isinstance(item, BaseModel) else item for item in result
                ]
            else:
                value = result
        elif isinstance(data, BaseModel):
            value = data.model_dump()
        elif isinstance(data, (str, int, float, bool, list, dict)):
            value = data
        else:
            raise ValueError(f"Unsupported data output type: {type(data)}")

        logs = coerce_empty_list_to_none(logs)
        return ToolCallOutput(
            value=value,
            logs=logs,
        )

    def fail(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        stacktrace: str | None = None,
        logs: list[ToolCallLog] | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        kind: ErrorKind = ErrorKind.UNKNOWN,
        can_retry: bool = False,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=can_retry,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
                stacktrace=stacktrace,
                kind=kind,
                status_code=status_code,
                extra=extra,
            ),
            logs=coerce_empty_list_to_none(logs),
        )

    def fail_retry(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        stacktrace: str | None = None,
        logs: list[ToolCallLog] | None = None,
        kind: ErrorKind = ErrorKind.TOOL_RUNTIME_RETRY,
        status_code: int = 500,
        extra: dict[str, Any] | None = None,
    ) -> ToolCallOutput:
        """
        DEPRECATED: Use ToolOutputFactory.fail instead.
        This method will be removed in version 3.0.0
        """

        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=True,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
                stacktrace=stacktrace,
                kind=kind,
                status_code=status_code,
                extra=extra,
            ),
            logs=coerce_empty_list_to_none(logs),
        )


output_factory = ToolOutputFactory()

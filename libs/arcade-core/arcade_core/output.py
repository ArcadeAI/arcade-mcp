from typing import Any, TypeVar

from pydantic import BaseModel

from arcade_core.errors import ErrorCode, ErrorOrigin, ErrorPhase
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
        value: str | int | float | bool | dict | list[str] | None
        if data is None:
            value = ""
        elif hasattr(data, "result"):
            value = getattr(data, "result", "")
        elif isinstance(data, BaseModel):
            value = data.model_dump()
        elif isinstance(data, (str, int, float, bool, list)):
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
        origin: ErrorOrigin = ErrorOrigin.TOOL,
        phase: ErrorPhase = ErrorPhase.RUNTIME,
        can_retry: bool = False,
        code: ErrorCode = ErrorCode.FATAL,
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
                origin=origin,
                phase=phase,
                code=code,
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
        origin: ErrorOrigin = ErrorOrigin.TOOL,
        phase: ErrorPhase = ErrorPhase.RUNTIME,
        code: ErrorCode = ErrorCode.RETRY_TOOL,
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
                origin=origin,
                phase=phase,
                code=code,
                status_code=status_code,
                extra=extra,
            ),
            logs=coerce_empty_list_to_none(logs),
        )


output_factory = ToolOutputFactory()

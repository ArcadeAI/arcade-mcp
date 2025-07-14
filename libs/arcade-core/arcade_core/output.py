from typing import TypeVar

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
        if data is None:
            value = None
        elif hasattr(data, "result"):
            # For Pydantic models with a result field
            result_value = data.result
            # If the result is also a Pydantic model, convert to dict
            if hasattr(result_value, "model_dump"):
                value = result_value.model_dump()
            else:
                value = result_value
        elif hasattr(data, "model_dump"):
            # For other Pydantic models, get the dict representation
            value = data.model_dump()
        else:
            # For plain values
            value = data

        logs = coerce_empty_list_to_none(logs)
        return ToolCallOutput(value=value, logs=logs)

    def fail(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        traceback_info: str | None = None,
        logs: list[ToolCallLog] | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=False,
                traceback_info=traceback_info,
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
        traceback_info: str | None = None,
        logs: list[ToolCallLog] | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=True,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
            ),
            logs=coerce_empty_list_to_none(logs),
        )


output_factory = ToolOutputFactory()

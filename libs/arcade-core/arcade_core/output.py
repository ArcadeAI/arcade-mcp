from typing import TypeVar

from pydantic import BaseModel

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
                traceback_info=traceback_info,
            ),
            logs=coerce_empty_list_to_none(logs),
        )


output_factory = ToolOutputFactory()

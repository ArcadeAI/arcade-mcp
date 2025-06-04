from typing import TypeVar

from arcade.core.schema import ToolCallError, ToolCallLog, ToolCallOutput
from arcade.core.utils import coerce_empty_list_to_none
from arcade.sdk.errors import ToolRuntimeError

T = TypeVar("T")


class ToolOutputFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    @staticmethod
    def success(
        *,
        data: T | None = None,
        logs: list[ToolCallLog] | None = None,
    ) -> ToolCallOutput:
        value = getattr(data, "result", "") if data else ""
        logs = coerce_empty_list_to_none(logs)
        return ToolCallOutput(value=value, logs=logs)

    @staticmethod
    def fail(
        *,
        error: ToolRuntimeError,
        logs: list[ToolCallLog] | None = None,
        return_remote_api_error_response: bool = False,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                name=error.__class__.__name__,
                message=error.message,
                developer_message=error.developer_message,
                can_retry=error.can_retry,
                additional_prompt_content=error.additional_prompt_content,
                retry_after_ms=error.retry_after_ms,
                traceback_info=error.traceback_info,
                http_response=(
                    getattr(error, "http_response", None)
                    if return_remote_api_error_response
                    else None
                ),
            ),
            logs=coerce_empty_list_to_none(logs),
        )

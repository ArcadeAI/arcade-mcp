from typing import TypeVar

from arcade.core.schema import ToolCallError, ToolCallOutput

T = TypeVar("T")


class ToolOutputFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    def success(
        self,
        *,
        data: T | None = None,
    ) -> ToolCallOutput:
        value = getattr(data, "result", "") if data else ""
        return ToolCallOutput(value=value)

    def fail(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        traceback_info: str | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=False,
                traceback_info=traceback_info,
            )
        )

    def fail_retry(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        traceback_info: str | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=True,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
            )
        )


output_factory = ToolOutputFactory()

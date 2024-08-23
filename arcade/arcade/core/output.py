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
        value = data.result if data and hasattr(data, "result") and data.result else "OK"

        return ToolCallOutput(value=value)

    def fail(self, *, message: str, developer_message: str | None = None) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message, developer_message=developer_message, can_retry=False
            )
        )

    def fail_retry(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        wait_ms: int | None = None,
    ) -> ToolCallOutput:
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=True,
                additional_prompt_content=additional_prompt_content,
                wait_ms=wait_ms,
            )
        )


output_factory = ToolOutputFactory()

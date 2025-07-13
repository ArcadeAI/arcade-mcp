import json
from typing import Any

from arcade_tdk.errors import RetryableToolError, ToolExecutionError


class TeamsToolExecutionError(ToolExecutionError):
    pass


class PaginationTimeoutError(TeamsToolExecutionError):
    """Raised when a timeout occurs during pagination."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        message = f"The pagination process timed out after {timeout_seconds} seconds."
        super().__init__(message=message, developer_message=message)


class RetryableTeamsToolExecutionError(RetryableToolError):
    pass


class UniqueItemError(RetryableTeamsToolExecutionError):
    base_message = "Failed to determine a unique {item}."

    def __init__(
        self,
        item: str,
        available_options: list[Any] | None = None,
        search_term: str | None = None,
    ) -> None:
        self.item = item
        self.available_options = available_options
        message = self.base_message.format(item=item)
        additional_prompt: str | None = None

        if search_term:
            message += f" Search term: '{search_term}'."

        if available_options:
            additional_prompt = f"Available {item}: {json.dumps(self.available_options)}"

        super().__init__(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )


class MultipleItemsFoundError(UniqueItemError):
    base_message = "Multiple {item} found. Please provide a unique identifier."


class NoItemsFoundError(UniqueItemError):
    base_message = "No {item} found."

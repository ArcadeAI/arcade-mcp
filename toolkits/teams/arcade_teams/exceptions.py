import json
from typing import Any

from arcade_tdk.errors import ToolExecutionError


class TeamsToolExecutionError(ToolExecutionError):
    pass


class UniqueItemError(TeamsToolExecutionError):
    base_message = "Failed to determine a unique {item}."

    def __init__(self, item: str, available_options: list[Any] | None = None) -> None:
        self.item = item
        self.available_options = available_options
        super().__init__(
            message=self.base_message.format(item=item),
            developer_message=None if not available_options else json.dumps(available_options),
        )


class MultipleItemsFoundError(UniqueItemError):
    base_message = "Multiple {item} found. Please provide a unique identifier."


class NoItemsFoundError(UniqueItemError):
    base_message = "No {item} found."

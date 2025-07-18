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


class MatchHumansByNameRetryableError(RetryableTeamsToolExecutionError):
    def __init__(self, match_errors: list[dict]):
        # Avoid circular import
        from arcade_teams.tools.people import search_people
        from arcade_teams.tools.users import list_users, search_users

        self.match_errors = match_errors
        names = "'" + "', '".join([error["name"] for error in match_errors]) + "'"
        tool_names = ", ".join([
            search_people.__tool_name__,
            search_users.__tool_name__,
            list_users.__tool_name__,
        ])
        message = f"Multiple matches found for the following names: {names}."
        additional_prompt = (
            "Next is a list of names and corresponding matches. Ask the requester whether they "
            f"meant to reference any of these options:\n```json\n{json.dumps(match_errors)}```\n"
            f"The following tools can retrieve more users and people, if needed: {tool_names}."
        )
        super().__init__(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )

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
        try:
            names = []
            potential_matches = []

            # Avoid circular import
            from arcade_teams.serializers import short_human

            for error in match_errors:
                names.append(error["name"])
                if error["matches"]:
                    potential_matches.append({
                        "name": error["name"],
                        "matches": [
                            short_human(match, with_email=True) for match in error["matches"]
                        ],
                    })

            if potential_matches:
                match_errors_json = json.dumps(potential_matches)
                additional_prompt = (
                    "Next is a list of names and corresponding matches. Ask the requester if they "
                    f"meant to reference any of these options:\n```json\n{match_errors_json}```"
                )
            else:
                additional_prompt = None

            message = f"Failed to find a unique match for the following names: {', '.join(names)}."

        except Exception:
            message = "Failed to find a unique match for the names searched."
            additional_prompt = str(match_errors)

        super().__init__(
            message=message,
            developer_message=message,
            additional_prompt_content=additional_prompt,
        )

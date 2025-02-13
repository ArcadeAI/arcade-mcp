class SlackToolkitError(Exception):
    """Base class for all Slack toolkit errors."""


class PaginationTimeoutError(SlackToolkitError):
    """Raised when a timeout occurs during pagination."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        super().__init__(f"The pagination process timed out after {timeout_seconds} seconds.")


class ItemNotFoundError(SlackToolkitError):
    """Raised when an item is not found."""


class UsernameNotFoundError(SlackToolkitError):
    """Raised when a user is not found by the username searched"""

    def __init__(self, usernames_found: list[str]) -> None:
        self.usernames_found = usernames_found


class ConversationNotFoundError(SlackToolkitError):
    """Raised when a conversation is not found"""


class DirectMessageConversationNotFoundError(ConversationNotFoundError):
    """Raised when a direct message conversation searched is not found"""

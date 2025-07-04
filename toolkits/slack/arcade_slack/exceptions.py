class SlackToolkitError(Exception):
    """Base class for all Slack toolkit errors."""


class PaginationTimeoutError(SlackToolkitError):
    """Raised when a timeout occurs during pagination."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        super().__init__(f"The pagination process timed out after {timeout_seconds} seconds.")

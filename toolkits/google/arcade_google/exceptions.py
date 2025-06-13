from zoneinfo import available_timezones

from arcade_tdk.errors import RetryableToolError


class GoogleToolError(Exception):
    """Base exception for Google tool errors."""

    def __init__(self, message: str, developer_message: str | None = None):
        self.message = message
        self.developer_message = developer_message
        super().__init__(self.message)

    def __str__(self) -> str:
        base_message = self.message
        if self.developer_message:
            return f"{base_message} (Developer: {self.developer_message})"
        return base_message


class RetryableGoogleToolError(RetryableToolError):
    """Raised when there's an error in a Google tool that can be retried."""

    pass


class GoogleServiceError(GoogleToolError):
    """Raised when there's an error building or using the Google service."""

    pass


class GmailToolError(GoogleToolError):
    """Raised when there's an error in the Gmail tools."""

    pass


class GoogleCalendarToolError(GoogleToolError):
    """Raised when there's an error in the Google Calendar tools."""

    pass


class InvalidTimezoneError(RetryableGoogleToolError):
    """Raised when a timezone is provided that is not supported by Python's zoneinfo."""

    def __init__(self, timezone_str: str):
        self.timezone_str = timezone_str
        available_timezones_msg = (
            "Here is a list of valid timezones (from Python's zoneinfo.available_timezones()): "
            f"{available_timezones()}"
        )
        super().__init__(
            f"Invalid timezone: '{timezone_str}'",
            developer_message=available_timezones_msg,
            additional_prompt_content=available_timezones_msg,
        )


class GoogleDriveToolError(GoogleToolError):
    """Raised when there's an error in the Google Drive tools."""

    pass


class GoogleDocsToolError(GoogleToolError):
    """Raised when there's an error in the Google Docs tools."""

    pass

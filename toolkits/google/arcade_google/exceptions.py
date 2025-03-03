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


class GoogleServiceError(GoogleToolError):
    """Raised when there's an error building or using the Google service."""

    pass


class GmailToolError(GoogleToolError):
    """Raised when there's an error in the Gmail tools."""

    pass


class GoogleCalendarToolError(GoogleToolError):
    """Raised when there's an error in the Google Calendar tools."""

    pass


class GoogleDriveToolError(GoogleToolError):
    """Raised when there's an error in the Google Drive tools."""

    pass


class GoogleDocsToolError(GoogleToolError):
    """Raised when there's an error in the Google Docs tools."""

    pass

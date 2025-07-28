import json
from typing import Any

from arcade_tdk.errors import RetryableToolError, ToolExecutionError


class SharePointToolExecutionError(ToolExecutionError):
    pass


class PaginationTimeoutError(SharePointToolExecutionError):
    """Raised when a timeout occurs during pagination."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        message = f"The pagination process timed out after {timeout_seconds} seconds."
        super().__init__(message=message, developer_message=message)


class RetryableSharePointToolExecutionError(RetryableToolError):
    pass


class UniqueItemError(RetryableSharePointToolExecutionError):
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


class InvalidSharePointUrlError(SharePointToolExecutionError):
    """Raised when an invalid SharePoint URL is provided."""

    def __init__(self, url: str):
        self.url = url
        message = f"Invalid SharePoint URL provided: {url}"
        super().__init__(message=message, developer_message=message)


class DriveAccessError(SharePointToolExecutionError):
    """Raised when there's an issue accessing a SharePoint drive."""

    def __init__(self, drive_id: str, operation: str):
        self.drive_id = drive_id
        self.operation = operation
        message = f"Failed to {operation} drive {drive_id}. Check permissions and drive ID."
        super().__init__(message=message, developer_message=message)


class SiteAccessError(SharePointToolExecutionError):
    """Raised when there's an issue accessing a SharePoint site."""

    def __init__(self, site_identifier: str, operation: str):
        self.site_identifier = site_identifier
        self.operation = operation
        message = f"Failed to {operation} site {site_identifier}. Check permissions and site identifier."
        super().__init__(message=message, developer_message=message)


class AuthenticationError(SharePointToolExecutionError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed. Check your credentials."):
        super().__init__(message=message, developer_message=message)


class AuthorizationError(SharePointToolExecutionError):
    """Raised when user lacks required permissions."""

    def __init__(self, resource: str = "resource", required_permissions: list[str] = None):
        self.resource = resource
        self.required_permissions = required_permissions or []
        message = f"Access denied to {resource}."
        if required_permissions:
            message += f" Required permissions: {', '.join(required_permissions)}"
        super().__init__(message=message, developer_message=message)


class ThrottlingError(RetryableSharePointToolExecutionError):
    """Raised when requests are being throttled."""

    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        message = "Request was throttled. Please try again later."
        if retry_after:
            message += f" Retry after {retry_after} seconds."
        super().__init__(message=message, developer_message=message)


class ItemNotFoundError(SharePointToolExecutionError):
    """Raised when a requested item is not found."""

    def __init__(self, item_type: str, identifier: str):
        self.item_type = item_type
        self.identifier = identifier
        message = f"{item_type} with identifier '{identifier}' was not found."
        super().__init__(message=message, developer_message=message)


class NetworkError(RetryableSharePointToolExecutionError):
    """Raised when network issues occur."""

    def __init__(self, message: str = "Network error occurred. Please check your connection."):
        super().__init__(message=message, developer_message=message)


class InvalidParameterError(SharePointToolExecutionError):
    """Raised when invalid parameters are provided."""

    def __init__(self, parameter: str, value: Any, expected: str = None):
        self.parameter = parameter
        self.value = value
        self.expected = expected
        message = f"Invalid parameter '{parameter}': {value}"
        if expected:
            message += f". Expected: {expected}"
        super().__init__(message=message, developer_message=message)


class SharePointUnavailableError(RetryableSharePointToolExecutionError):
    """Raised when SharePoint service is unavailable."""

    def __init__(self, message: str = "SharePoint service is currently unavailable. Please try again later."):
        super().__init__(message=message, developer_message=message)


class VersionConflictError(SharePointToolExecutionError):
    """Raised when there's a version conflict during updates."""

    def __init__(self, item_type: str, identifier: str):
        self.item_type = item_type
        self.identifier = identifier
        message = f"Version conflict for {item_type} '{identifier}'. The item was modified by another user."
        super().__init__(message=message, developer_message=message)


class QuotaExceededError(SharePointToolExecutionError):
    """Raised when storage quota is exceeded."""

    def __init__(self, quota_type: str = "storage"):
        self.quota_type = quota_type
        message = f"The {quota_type} quota has been exceeded."
        super().__init__(message=message, developer_message=message)


class FileTypeNotSupportedError(SharePointToolExecutionError):
    """Raised when file type is not supported."""

    def __init__(self, file_type: str, supported_types: list[str] = None):
        self.file_type = file_type
        self.supported_types = supported_types or []
        message = f"File type '{file_type}' is not supported."
        if supported_types:
            message += f" Supported types: {', '.join(supported_types)}"
        super().__init__(message=message, developer_message=message)


# Error code mappings for Microsoft Graph API
GRAPH_ERROR_MAPPINGS = {
    "InvalidAuthenticationToken": AuthenticationError,
    "Unauthenticated": AuthenticationError,
    "Forbidden": AuthorizationError,
    "AccessDenied": AuthorizationError,
    "InsufficientPermissions": AuthorizationError,
    "TooManyRequests": ThrottlingError,
    "ThrottledRequest": ThrottlingError,
    "ItemNotFound": ItemNotFoundError,
    "NotFound": ItemNotFoundError,
    "BadRequest": InvalidParameterError,
    "InvalidRequest": InvalidParameterError,
    "ServiceUnavailable": SharePointUnavailableError,
    "InternalServerError": SharePointUnavailableError,
    "Conflict": VersionConflictError,
    "InsufficientStorage": QuotaExceededError,
    "UnsupportedMediaType": FileTypeNotSupportedError,
}


def parse_graph_error(error: Exception, tool_name: str = None) -> SharePointToolExecutionError:
    """Parse a Microsoft Graph error and return appropriate custom exception."""
    error_message = str(error)
    error_code = None
    status_code = None
    
    # Try to extract error code from common Graph API error patterns
    if hasattr(error, 'code'):
        error_code = error.code
    elif hasattr(error, 'error') and hasattr(error.error, 'code'):
        error_code = error.error.code
    elif "InvalidAuthenticationToken" in error_message or "Unauthenticated" in error_message:
        error_code = "InvalidAuthenticationToken"
    elif "Forbidden" in error_message or "Access denied" in error_message:
        error_code = "Forbidden"
    elif "Not found" in error_message or "ItemNotFound" in error_message:
        error_code = "NotFound"
    elif "Bad request" in error_message or "BadRequest" in error_message:
        error_code = "BadRequest"
    elif "Too many requests" in error_message or "throttled" in error_message.lower():
        error_code = "TooManyRequests"
    elif "Service unavailable" in error_message or "Internal server error" in error_message:
        error_code = "ServiceUnavailable"
    elif "timeout" in error_message.lower():
        return NetworkError(f"Network timeout occurred: {error_message}")
    elif "connection" in error_message.lower():
        return NetworkError(f"Connection error: {error_message}")
    
    # Map to appropriate exception class
    if error_code and error_code in GRAPH_ERROR_MAPPINGS:
        exception_class = GRAPH_ERROR_MAPPINGS[error_code]
        
        if exception_class == AuthenticationError:
            return AuthenticationError(f"Authentication failed: {error_message}")
        elif exception_class == AuthorizationError:
            return AuthorizationError(resource="SharePoint resource")
        elif exception_class == ThrottlingError:
            return ThrottlingError()
        elif exception_class == ItemNotFoundError:
            return ItemNotFoundError("Item", "unknown")
        elif exception_class == InvalidParameterError:
            return InvalidParameterError("unknown", "unknown", "valid parameter")
        elif exception_class == SharePointUnavailableError:
            return SharePointUnavailableError()
        else:
            return exception_class(f"Graph API error: {error_message}")
    
    # Default to generic SharePoint error
    return SharePointToolExecutionError(
        message=f"SharePoint operation failed: {error_message}",
        developer_message=f"Tool: {tool_name}, Error: {error_message}"
    ) 
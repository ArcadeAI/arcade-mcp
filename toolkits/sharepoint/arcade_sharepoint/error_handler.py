"""Centralized error handling for SharePoint toolkit Microsoft Graph API calls."""

from typing import Any, Dict, Callable
from functools import wraps
import logging

from kiota_abstractions.api_error import APIError
from arcade_sharepoint.exceptions import (
    parse_graph_error,
    SharePointToolExecutionError,
    AuthenticationError,
    AuthorizationError,
    ItemNotFoundError,
    ThrottlingError,
    NetworkError,
    SharePointUnavailableError,
    InvalidParameterError
)

logger = logging.getLogger(__name__)


def handle_graph_api_errors(tool_name: str = None):
    """Decorator to handle Microsoft Graph API errors consistently across tools."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except APIError as api_error:
                # Handle Kiota API errors from Microsoft Graph SDK
                error_details = extract_api_error_details(api_error)
                custom_error = map_api_error_to_custom_exception(error_details, tool_name)
                logger.error(f"Graph API error in {tool_name}: {custom_error}")
                return create_error_response(custom_error, tool_name)
            except Exception as general_error:
                # Handle other exceptions
                custom_error = parse_graph_error(general_error, tool_name)
                logger.error(f"General error in {tool_name}: {custom_error}")
                return create_error_response(custom_error, tool_name)
        return wrapper
    return decorator


def extract_api_error_details(api_error: APIError) -> Dict[str, Any]:
    """Extract relevant details from APIError."""
    details = {
        "message": str(api_error),
        "error_code": None,
        "status_code": None,
        "inner_error": None
    }
    
    if hasattr(api_error, 'error') and api_error.error:
        error_obj = api_error.error
        details["error_code"] = getattr(error_obj, 'code', None)
        details["message"] = getattr(error_obj, 'message', str(api_error))
        details["inner_error"] = getattr(error_obj, 'inner_error', None)
    
    if hasattr(api_error, 'response_status_code'):
        details["status_code"] = api_error.response_status_code
        
    return details


def map_api_error_to_custom_exception(error_details: Dict[str, Any], tool_name: str = None) -> SharePointToolExecutionError:
    """Map API error details to appropriate custom exceptions."""
    error_code = error_details.get("error_code", "")
    message = error_details.get("message", "Unknown error")
    status_code = error_details.get("status_code")
    
    # Map based on error code
    if error_code in ["InvalidAuthenticationToken", "Unauthenticated"]:
        return AuthenticationError(f"Authentication failed: {message}")
    
    elif error_code in ["Forbidden", "AccessDenied", "InsufficientPermissions"]:
        required_permissions = extract_required_permissions(error_details)
        return AuthorizationError(
            resource="SharePoint resource",
            required_permissions=required_permissions
        )
    
    elif error_code in ["ItemNotFound", "NotFound"]:
        return ItemNotFoundError("Item", "unknown")
    
    elif error_code in ["TooManyRequests", "ThrottledRequest"]:
        retry_after = extract_retry_after(error_details)
        return ThrottlingError(retry_after=retry_after)
    
    elif error_code in ["BadRequest", "InvalidRequest"]:
        return InvalidParameterError("request", message, "valid request format")
    
    elif error_code in ["ServiceUnavailable", "InternalServerError"]:
        return SharePointUnavailableError(f"SharePoint service error: {message}")
    
    # Map based on status code if error code is not available
    elif status_code:
        if status_code == 401:
            return AuthenticationError(f"Authentication failed: {message}")
        elif status_code == 403:
            return AuthorizationError(resource="SharePoint resource")
        elif status_code == 404:
            return ItemNotFoundError("Item", "unknown")
        elif status_code == 429:
            return ThrottlingError()
        elif status_code >= 500:
            return SharePointUnavailableError(f"Server error ({status_code}): {message}")
        elif status_code >= 400:
            return InvalidParameterError("request", message)
    
    # Check for network-related errors in message
    if any(keyword in message.lower() for keyword in ["timeout", "connection", "network"]):
        return NetworkError(f"Network error: {message}")
    
    # Default to generic SharePoint error
    return SharePointToolExecutionError(
        message=f"SharePoint operation failed: {message}",
        developer_message=f"Tool: {tool_name}, Code: {error_code}, Status: {status_code}, Message: {message}"
    )


def extract_required_permissions(error_details: Dict[str, Any]) -> list[str]:
    """Extract required permissions from error details."""
    message = error_details.get("message", "").lower()
    permissions = []
    
    # Common SharePoint permission patterns
    if "sites.read" in message:
        permissions.append("Sites.Read.All")
    if "sites.write" in message:
        permissions.append("Sites.ReadWrite.All")
    if "files.read" in message:
        permissions.append("Files.Read.All")
    if "files.write" in message:
        permissions.append("Files.ReadWrite.All")
    
    return permissions


def extract_retry_after(error_details: Dict[str, Any]) -> int:
    """Extract retry-after time from error details."""
    # Look for retry-after information in the error
    inner_error = error_details.get("inner_error", {})
    if isinstance(inner_error, dict):
        return inner_error.get("retry_after", 60)  # Default to 60 seconds
    return 60


def create_error_response(error: SharePointToolExecutionError, tool_name: str = None) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    error_response = {
        "error": error.message,
        "error_type": error.__class__.__name__,
        "tool": tool_name
    }
    
    # Add specific attributes for different error types
    if isinstance(error, AuthorizationError):
        if error.required_permissions:
            error_response["required_permissions"] = error.required_permissions
        error_response["resource"] = error.resource
    
    elif isinstance(error, ThrottlingError):
        if error.retry_after:
            error_response["retry_after_seconds"] = error.retry_after
    
    elif isinstance(error, ItemNotFoundError):
        error_response["item_type"] = error.item_type
        error_response["identifier"] = error.identifier
    
    elif isinstance(error, InvalidParameterError):
        error_response["parameter"] = error.parameter
        error_response["provided_value"] = str(error.value)
        if error.expected:
            error_response["expected"] = error.expected
    
    return error_response


def validate_sharepoint_identifiers(**kwargs) -> None:
    """Validate SharePoint identifiers (site IDs, drive IDs, etc.)."""
    from arcade_sharepoint.utils import is_site_id, is_drive_id, is_sharepoint_url
    
    for param_name, param_value in kwargs.items():
        if param_name.endswith("site_id") and param_value:
            if not is_site_id(param_value):
                raise InvalidParameterError(
                    parameter=param_name,
                    value=param_value,
                    expected="Valid SharePoint site ID format"
                )
        
        elif param_name.endswith("drive_id") and param_value:
            if not is_drive_id(param_value):
                raise InvalidParameterError(
                    parameter=param_name,
                    value=param_value,
                    expected="Valid SharePoint drive ID format"
                )
        
        elif param_name.endswith("url") and param_value:
            if not is_sharepoint_url(param_value):
                raise InvalidParameterError(
                    parameter=param_name,
                    value=param_value,
                    expected="Valid SharePoint URL format"
                )


def validate_pagination_params(limit: int = None, offset: int = None) -> tuple[int, int]:
    """Validate and normalize pagination parameters."""
    if limit is not None:
        if not isinstance(limit, int) or limit < 1:
            raise InvalidParameterError("limit", limit, "Positive integer")
        limit = min(50, max(1, limit))  # Clamp between 1 and 50
    else:
        limit = 25  # Default
    
    if offset is not None:
        if not isinstance(offset, int) or offset < 0:
            raise InvalidParameterError("offset", offset, "Non-negative integer")
    else:
        offset = 0  # Default
    
    return limit, offset


def validate_search_params(search_term: str, entity_types: list[str] = None) -> tuple[str, list[str]]:
    """Validate search parameters."""
    if not search_term or not search_term.strip():
        raise InvalidParameterError("search_term", search_term, "Non-empty string")
    
    valid_entity_types = ["driveItem", "listItem", "site", "list"]
    
    if entity_types:
        invalid_types = [et for et in entity_types if et not in valid_entity_types]
        if invalid_types:
            raise InvalidParameterError(
                "entity_types",
                invalid_types,
                f"Valid entity types: {', '.join(valid_entity_types)}"
            )
    else:
        entity_types = valid_entity_types  # Default to all types
    
    return search_term.strip(), entity_types 
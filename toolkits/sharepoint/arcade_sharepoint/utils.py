import datetime
import re
from typing import Any
from urllib.parse import urlparse

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from pydantic import BaseModel

from arcade_sharepoint.client import get_client
from arcade_sharepoint.constants import ENV_VARS


def remove_none_values(kwargs: dict) -> dict:
    """Remove None values from a dictionary."""
    return {key: val for key, val in kwargs.items() if val is not None}


def load_config_param(context: ToolContext, key: str) -> Any:
    """Load configuration parameter from context metadata, secrets, or environment variables."""
    try:
        return context.get_metadata(key)
    except ValueError:
        pass

    try:
        return context.get_secret(key)
    except ValueError:
        pass

    return ENV_VARS.get(key)


def validate_datetime_string(value: str) -> str:
    """Validate datetime string format."""
    try:
        # Try ISO format first
        datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value
    except ValueError:
        try:
            # Try common format
            datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value
        except ValueError:
            try:
                # Try date only
                datetime.datetime.strptime(value, "%Y-%m-%d")
                return value
            except ValueError:
                raise


def validate_datetime_range(start: str | None, end: str | None) -> tuple[str | None, str | None]:
    """Validate datetime range."""
    invalid_datetime_msg = (
        "Invalid {field} datetime string: {value}. "
        "Provide a string in the format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' or ISO format."
    )
    start_dt = None
    end_dt = None
    if start:
        try:
            start_dt = validate_datetime_string(start)
        except ValueError as e:
            raise ToolExecutionError(
                invalid_datetime_msg.format(field="start_datetime", value=start)
            ) from e
    if end:
        try:
            end_dt = validate_datetime_string(end)
        except ValueError as e:
            raise ToolExecutionError(
                invalid_datetime_msg.format(field="end_datetime", value=end)
            ) from e
    if start_dt and end_dt and start_dt > end_dt:
        err_msg = "start_datetime must be before end_datetime."
        raise ToolExecutionError(message=err_msg, developer_message=err_msg)
    return start, end


def is_sharepoint_url(url: str) -> bool:
    """Check if URL is a valid SharePoint URL."""
    try:
        parsed = urlparse(url)
        return bool(
            parsed.scheme in ['http', 'https'] and 
            parsed.netloc and
            ('sharepoint.com' in parsed.netloc.lower() or 
             'microsoftonline.com' in parsed.netloc.lower() or
             # Allow custom domains that might host SharePoint
             any(part in parsed.netloc.lower() for part in ['.com', '.org', '.net']))
        )
    except Exception:
        return False


def is_site_id(value: str) -> bool:
    """Check if value is a SharePoint site ID (GUID format)."""
    guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return bool(re.match(guid_pattern, value))


def is_drive_id(value: str) -> bool:
    """Check if value is a SharePoint drive ID."""
    # Drive IDs can be GUIDs or have specific SharePoint formats
    return is_site_id(value) or bool(re.match(r'^[a-zA-Z0-9!_-]{20,}$', value))


def extract_site_info_from_url(url: str) -> dict[str, str]:
    """Extract site information from SharePoint URL."""
    if not is_sharepoint_url(url):
        raise ToolExecutionError(f"Invalid SharePoint URL: {url}")
    
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split('/') if part]
    
    info = {
        'host': parsed.netloc,
        'scheme': parsed.scheme,
        'full_url': url
    }
    
    # Try to extract site collection and site name
    if len(path_parts) >= 2 and path_parts[0] == 'sites':
        info['site_collection'] = path_parts[1]
        if len(path_parts) > 2:
            info['relative_path'] = '/'.join(path_parts[2:])
    
    return info


def build_offset_pagination(items: list, limit: int, offset: int, has_more: bool = False) -> dict:
    """Build pagination information for offset-based pagination."""
    return {
        "limit": limit,
        "offset": offset, 
        "has_more": has_more,
        "next_offset": offset + len(items) if has_more else None,
        "count": len(items)
    }


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for SharePoint compatibility."""
    # Remove invalid characters for SharePoint
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    return sanitized


class PaginationInfo(BaseModel):
    """Pagination information model."""
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None = None
    count: int 
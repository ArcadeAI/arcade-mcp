import re
from datetime import datetime
from typing import Any

import pytz
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection
from msgraph import GraphServiceClient
from msgraph.generated.users.item.mailbox_settings.mailbox_settings_request_builder import (
    MailboxSettingsRequestBuilder,
)

from arcade_microsoft.outlook_calendar.constants import WINDOWS_TO_IANA


def remove_timezone_offset(date_time: str) -> str:
    """Remove the timezone offset from the date_time string."""
    return re.sub(r"[+-][0-9]{2}:[0-9]{2}$|Z$", "", date_time)


def replace_timezone_offset(date_time: str, time_zone_offset: str) -> str:
    """Replace the timezone offset in the date_time string with the time_zone_offset.

    If the date_time str already contains a timezone offset, it will be replaced.
    If the date_time str does not contain a timezone offset, the time_zone_offset will be appended

    Args:
        date_time: The date_time string to replace the timezone offset in.
        time_zone_offset: The timezone offset to replace the existing timezone offset with.

    Returns:
        The date_time string with the timezone offset replaced or appended.
    """
    date_time = remove_timezone_offset(date_time)
    return f"{date_time}{time_zone_offset}"


def convert_timezone_to_offset(time_zone: str) -> str:
    """
    Convert a timezone (Windows or IANA) to ISO 8601 offset.
    First tries Windows timezone format, then IANA, then falls back to UTC if both fail.

    Args:
        time_zone: The timezone (Windows or IANA) to convert to ISO 8601 offset.

    Returns:
        The timezone offset in ISO 8601 format (e.g. '+08:00', '-07:00', or 'Z' for UTC)
    """
    # Try Windows timezone format
    iana_timezone = WINDOWS_TO_IANA.get(time_zone)
    if iana_timezone:
        try:
            tz = pytz.timezone(iana_timezone)
            now = datetime.now(tz)
            tz_offset = now.strftime("%z")

            if len(tz_offset) == 5:  # +HHMM format
                tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"  # +HH:MM format
            return tz_offset  # noqa: TRY300
        except (pytz.exceptions.UnknownTimeZoneError, ValueError):
            pass

    # Try IANA timezone format
    try:
        tz = pytz.timezone(time_zone)
        now = datetime.now(tz)
        tz_offset = now.strftime("%z")

        if len(tz_offset) == 5:  # +HHMM format
            tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"  # +HH:MM format
        return tz_offset  # noqa: TRY300
    except (pytz.exceptions.UnknownTimeZoneError, ValueError):
        # Fallback to UTC
        return "Z"


async def get_default_calendar_timezone(client: GraphServiceClient) -> str:
    """Get the authenticated user's default calendar's timezone.

    Args:
        client: The GraphServiceClient to use to get
            the authenticated user's default calendar's timezone.

    Returns:
        The timezone in "Windows timezone format" or "IANA timezone format".
    """
    query_params = MailboxSettingsRequestBuilder.MailboxSettingsRequestBuilderGetQueryParameters(
        select=["timeZone"]
    )
    request_config = RequestConfiguration(
        query_parameters=query_params,
    )
    response = await client.me.mailbox_settings.get(request_config)

    if response and response.time_zone:
        return response.time_zone
    return "UTC"


def create_timezone_headers(time_zone: str) -> HeadersCollection:
    """
    Create headers with timezone preference.

    Args:
        time_zone: The timezone to set in the headers.

    Returns:
        Headers collection with timezone preference set.
    """
    headers = HeadersCollection()
    headers.try_add("Prefer", f'outlook.timezone="{time_zone}"')
    return headers


def create_timezone_request_config(
    time_zone: str, query_parameters: Any | None = None
) -> RequestConfiguration:
    """
    Create a request configuration with timezone headers and optional query parameters.

    Args:
        time_zone: The timezone to set in the headers.
        query_parameters: Optional query parameters to include in the configuration.

    Returns:
        Request configuration with timezone headers and optional query parameters.
    """
    headers = create_timezone_headers(time_zone)
    return RequestConfiguration(
        headers=headers,
        query_parameters=query_parameters,
    )

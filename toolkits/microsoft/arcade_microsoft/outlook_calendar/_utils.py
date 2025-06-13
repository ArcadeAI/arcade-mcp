import re
from datetime import datetime
from typing import Any

import pytz
from arcade_tdk.errors import ToolExecutionError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.headers_collection import HeadersCollection
from msgraph import GraphServiceClient
from msgraph.generated.users.item.mailbox_settings.mailbox_settings_request_builder import (
    MailboxSettingsRequestBuilder,
)

from arcade_microsoft.outlook_calendar.constants import WINDOWS_TO_IANA


def validate_date_times(start_date_time: str, end_date_time: str) -> None:
    """
    Validate date times are in ISO 8601 format and
    that end time is after start time (ignoring timezone offsets).

    Args:
        start_date_time: The start date time string to validate.
        end_date_time: The end date time string to validate.

    Raises:
        ValueError: If the date times are not in ISO 8601 format
        ToolExecutionError: If end time is not after start time.

    Note:
        This function ignores timezone offsets.
    """
    # parse into offset-aware datetimes
    start_aware = datetime.fromisoformat(start_date_time)
    end_aware = datetime.fromisoformat(end_date_time)

    # drop tzinfo to treat both as naïve local times
    start_naive = start_aware.replace(tzinfo=None)
    end_naive = end_aware.replace(tzinfo=None)

    if start_naive >= end_naive:
        raise ToolExecutionError(
            message="Start time must be before end time",
            developer_message=(
                f"The start time '{start_naive}' is not before the end time '{end_naive}'"
            ),
        )


def prepare_meeting_body(
    body: str, custom_meeting_url: str | None, is_online_meeting: bool
) -> tuple[str, bool]:
    """Prepare meeting body and determine final online meeting status.

    Args:
        body: The original meeting body text
        custom_meeting_url: Custom URL for the meeting, if one exists
        is_online_meeting: Whether this should be an online meeting

    Returns:
        tuple: (Updated meeting body, final online meeting status)

    Note:
        If a custom meeting URL is provided, is_online_meeting will be set to False
        to prevent Microsoft from generating its own meeting URL. The custom meeting
        URL will then be added to the body of the meeting.
    """
    is_online_meeting = not custom_meeting_url and is_online_meeting

    if custom_meeting_url:
        body = f"""{body}\n
.........................................................................
Join online meeting
{custom_meeting_url}"""

    return body, is_online_meeting


def validate_emails(emails: list[str]) -> None:
    """Validate a list of email addresses.

    Args:
        emails: The list of email addresses to validate.

    Raises:
        ToolExecutionError: If any email address is invalid.
    """
    invalid_emails = []
    for email in emails:
        if not is_valid_email(email):
            invalid_emails.append(email)
    if invalid_emails:
        raise ToolExecutionError(message=f"Invalid email address(es): {', '.join(invalid_emails)}")


def is_valid_email(email: str) -> bool:
    """Simple check to see if an email address is valid.

    Args:
        email: The email address to check.

    Returns:
        True if the email address is valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


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

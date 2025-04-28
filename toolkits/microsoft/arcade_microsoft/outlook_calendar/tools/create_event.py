from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Microsoft

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_calendar._utils import (
    create_timezone_request_config,
    get_default_calendar_timezone,
    remove_timezone_offset,
)
from arcade_microsoft.outlook_calendar.models import (
    Attendee,
    DateTimeTimeZone,
    Event,
)


@tool(requires_auth=Microsoft(scopes=["MailboxSettings.Read", "Calendars.ReadWrite"]))
async def create_event(
    context: ToolContext,
    subject: Annotated[str, "The text of the event's subject (title) line."],
    body: Annotated[str, "The body of the event"],
    start_date_time: Annotated[
        str,
        "The datetime of the event's start, represented in "
        "ISO 8601 format. Timezone offset is ignored. For example, 2025-04-25T13:00:00",
    ],
    end_date_time: Annotated[
        str,
        "The datetime of the event's end, represented in "
        "ISO 8601 format. Timezone offset is ignored. For example, 2025-04-25T13:30:00",
    ],
    location: Annotated[str | None, "The location of the event"] = None,
    attendee_emails: Annotated[
        list[str] | None,
        "The email addresses of the attendees of the event. "
        "Must be valid email addresses e.g., username@domain.com.",
    ] = None,
    is_online_meeting: Annotated[
        bool, "Whether the event is an online meeting. Defaults to False"
    ] = False,
) -> Annotated[dict, "A dictionary containing the created event details"]:
    """Create an event in the authenticated user's default calendar.

    Ignores timezone offsets provided in the start_date_time and end_date_time parameters.
    Instead, uses the user's default calendar timezone to filter events.
    If the user has not set a timezone for their calendar, then the timezone will be UTC.
    """
    client = get_client(context.get_auth_token_or_empty())

    time_zone = await get_default_calendar_timezone(client)
    start_date_time = remove_timezone_offset(start_date_time)
    end_date_time = remove_timezone_offset(end_date_time)
    event = Event(
        subject=subject,
        body=body,
        start=DateTimeTimeZone(date_time=start_date_time, time_zone=time_zone),
        end=DateTimeTimeZone(date_time=end_date_time, time_zone=time_zone),
        location=location or "",
        attendees=[Attendee(address=attendee) for attendee in attendee_emails or []],
        is_online_meeting=is_online_meeting,
    ).to_sdk()
    request_config = create_timezone_request_config(time_zone)

    response = await client.me.events.post(body=event, request_configuration=request_config)

    return Event.from_sdk(response).to_dict()  # type: ignore[arg-type]

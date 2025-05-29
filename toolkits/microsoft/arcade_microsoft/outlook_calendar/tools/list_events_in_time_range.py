from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from msgraph.generated.users.item.calendar.calendar_view.calendar_view_request_builder import (
    CalendarViewRequestBuilder,
)

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_calendar._utils import (
    convert_timezone_to_offset,
    create_timezone_request_config,
    get_default_calendar_timezone,
    replace_timezone_offset,
    validate_date_times,
)
from arcade_microsoft.outlook_calendar.models import Event


@tool(requires_auth=Microsoft(scopes=["MailboxSettings.Read", "Calendars.ReadBasic"]))
async def list_events_in_time_range(
    context: ToolContext,
    start_date_time: Annotated[
        str,
        "The start date and time of the time range, represented in "
        "ISO 8601 format. Timezone offset is ignored. For example, 2025-04-24T19:00:00",
    ],
    end_date_time: Annotated[
        str,
        "The end date and time of the time range, represented in "
        "ISO 8601 format. Timezone offset is ignored. For example, 2025-04-24T19:30:00",
    ],
    limit: Annotated[int, "The maximum number of events to return. Max 1000. Defaults to 10"] = 10,
) -> Annotated[dict, "A dictionary containing a list of events"]:
    """List events in the user's calendar in a specific time range.

    Ignores timezone offsets provided in the start_date_time and end_date_time parameters.
    Instead, uses the user's default calendar timezone to filter events.
    If the user has not set a timezone for their calendar, then the timezone will be UTC.
    """
    # Validate inputs
    validate_date_times(start_date_time, end_date_time)

    client = get_client(context.get_auth_token_or_empty())
    time_zone = await get_default_calendar_timezone(client)
    time_zone_offset = convert_timezone_to_offset(time_zone)
    start_date_time = replace_timezone_offset(start_date_time, time_zone_offset)
    end_date_time = replace_timezone_offset(end_date_time, time_zone_offset)
    query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        top=max(1, min(limit, 1000)),
    )
    request_config = create_timezone_request_config(time_zone, query_params)

    response = await client.me.calendar.calendar_view.get(request_config)
    events = [Event.from_sdk(event).to_dict() for event in response.value]  # type: ignore[union-attr]

    return {"events": events, "num_events": len(events)}

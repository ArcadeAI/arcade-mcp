from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_calendar._utils import (
    create_timezone_request_config,
    get_default_calendar_timezone,
)
from arcade_microsoft.outlook_calendar.models import Event


@tool(requires_auth=Microsoft(scopes=["MailboxSettings.Read", "Calendars.ReadBasic"]))
async def get_event(
    context: ToolContext,
    event_id: Annotated[str, "The ID of the event to get"],
) -> Annotated[dict, "A dictionary containing the event details"]:
    """Get an event by its ID from the user's calendar."""
    client = get_client(context.get_auth_token_or_empty())

    time_zone = await get_default_calendar_timezone(client)
    request_config = create_timezone_request_config(time_zone)

    response = await client.me.events.by_event_id(event_id).get(
        request_configuration=request_config
    )

    return Event.from_sdk(response).to_dict()  # type: ignore[arg-type]

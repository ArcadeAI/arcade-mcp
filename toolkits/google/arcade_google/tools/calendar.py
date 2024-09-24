import json
from datetime import datetime
from typing import Annotated

from arcade_google.tools.models import TimeSlot, Day, DateRange, EventVisibility
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )
)
async def create_event(
    context: ToolContext,
    summary: Annotated[str, "The title of the event"],
    start_date: Annotated[Day, "The start date of the event"],
    start_time: Annotated[TimeSlot, "The start time of the event"],
    end_date: Annotated[Day, "The end date of the event"],
    end_time: Annotated[TimeSlot, "The end time of the event"],
    calendar_id: Annotated[
        str, "The ID of the calendar to create the event in, usually 'primary'"
    ] = "primary",
    description: Annotated[str | None, "The description of the event"] = None,
    location: Annotated[str | None, "The location of the event"] = None,
    visibility: Annotated[
        EventVisibility, "The visibility of the event"
    ] = EventVisibility.DEFAULT,
    attendee_emails: Annotated[
        list[str] | None,
        "The list of attendee emails. Must be valid email addresses e.g., username@domain.com",
    ] = None,
) -> Annotated[str, "A JSON string containing the created event details"]:
    """Create a new event in the specified calendar."""
    service = build(
        "calendar", "v3", credentials=Credentials(context.authorization.token)
    )

    try:
        # Get the calendar's time zone
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        time_zone = calendar["timeZone"]

        # Convert enum values to datetime objects
        start_datetime = datetime.combine(
            start_date.to_date(time_zone), start_time.to_time()
        )
        end_datetime = datetime.combine(end_date.to_date(time_zone), end_time.to_time())

        event = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_datetime.isoformat(), "timeZone": time_zone},
            "end": {"dateTime": end_datetime.isoformat(), "timeZone": time_zone},
            "visibility": visibility.value,
        }

        if attendee_emails:
            event["attendees"] = [{"email": email} for email in attendee_emails]

        created_event = (
            service.events().insert(calendarId=calendar_id, body=event).execute()
        )
        return json.dumps({"event": created_event})
    except HttpError as error:
        return json.dumps({"error": str(error)})


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/calendar.events.readonly"],
    )
)
async def list_events(
    context: ToolContext,
    calendar_id: Annotated[
        str, "The ID of the calendar to list events from"
    ] = "primary",
    date_range: Annotated[
        DateRange, "The date range for which to list events"
    ] = DateRange.TODAY,
    max_results: Annotated[int, "The maximum number of events to return"] = 10,
) -> Annotated[str, "A JSON string containing the list of events"]:
    """List events from the specified calendar within the given date range."""

    service = build(
        "calendar", "v3", credentials=Credentials(context.authorization.token)
    )

    start_date, end_date = date_range.to_datetime_range()
    # https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=2024-09-01Z&timeMax=2024-10-01Z&maxResults=10&singleEvents=true&orderBy=startTime&alt=json
    try:
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat() + "Z",
                timeMax=end_date.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        return json.dumps({"events": events})
    except HttpError as error:
        return json.dumps({"error": str(error)})

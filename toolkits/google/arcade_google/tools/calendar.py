from datetime import datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arcade.core.errors import RetryableToolError, ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google
from arcade_google.tools.models import Day, EventVisibility, SendUpdatesOptions, TimeSlot
from arcade_google.tools.utils import _update_datetime


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
    start_date: Annotated[Day, "The day that the event starts"],
    start_time: Annotated[TimeSlot, "The time of the day that the event starts"],
    end_date: Annotated[Day, "The day that the event ends"],
    end_time: Annotated[TimeSlot, "The time of the day that the event ends"],
    calendar_id: Annotated[
        str, "The ID of the calendar to create the event in, usually 'primary'"
    ] = "primary",
    description: Annotated[str | None, "The description of the event"] = None,
    location: Annotated[str | None, "The location of the event"] = None,
    visibility: Annotated[EventVisibility, "The visibility of the event"] = EventVisibility.DEFAULT,
    attendee_emails: Annotated[
        list[str] | None,
        "The list of attendee emails. Must be valid email addresses e.g., username@domain.com",
    ] = None,
) -> Annotated[dict, "A dictionary containing the created event details"]:
    """Create a new event/meeting/sync/meetup in the specified calendar."""

    service = build("calendar", "v3", credentials=Credentials(context.authorization.token))

    try:
        # Get the calendar's time zone
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        time_zone = calendar["timeZone"]

        # Convert enum values to datetime objects
        start_datetime = datetime.combine(start_date.to_date(time_zone), start_time.to_time())
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

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{create_event.__name__}' tool.", str(e)
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{create_event.__name__}' tool.",
            str(e),
        )
    else:
        return {"event": created_event}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/calendar.events.readonly"],
    )
)
async def list_events(
    context: ToolContext,
    min_day: Annotated[
        Day, "Filter by events that end on or after this day. Combined with min_time_slot"
    ],
    min_time_slot: Annotated[
        TimeSlot, "Filter by events that end after this time. Combined with min_day"
    ],
    max_day: Annotated[
        Day, "Filter by events that start on or before this day. Combined with max_time_slot"
    ],
    max_time_slot: Annotated[
        TimeSlot, "Filter by events that start before this time. Combined with max_day"
    ],
    calendar_id: Annotated[str, "The ID of the calendar to list events from"] = "primary",
    max_results: Annotated[int, "The maximum number of events to return"] = 10,
) -> Annotated[dict, "A dictionary containing the list of events"]:
    """
    List events from the specified calendar within the given date range.

    min_day and min_time_slot are combined to form the lower bound (exclusive) for an event's end time to filter by
    max_day and max_time_slot are combined to form the upper bound (exclusive) for an event's start time to filter by

    For example:
    If min_day is set to Day.TODAY and min_time_slot is set to TimeSlot._09:00,
    and max_day is set to Day.TOMORROW and max_time_slot is set to TimeSlot._17:00,
    the function will return events that:
    1. End after 09:00 today (exclusive)
    2. Start before 17:00 tomorrow (exclusive)
    This means an event starting at 08:00 today and ending at 10:00 today would be included,
    but an event starting at 17:00 tomorrow would not be included.
    """
    service = build("calendar", "v3", credentials=Credentials(context.authorization.token))

    # Get the calendar's time zone
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    time_zone = calendar["timeZone"]

    # Convert enum values to datetime with timezone offset
    start_datetime = datetime.combine(
        min_day.to_date(time_zone), min_time_slot.to_time()
    ).astimezone(ZoneInfo(time_zone))
    end_datetime = datetime.combine(max_day.to_date(time_zone), max_time_slot.to_time()).astimezone(
        ZoneInfo(time_zone)
    )

    if start_datetime > end_datetime:
        start_datetime, end_datetime = end_datetime, start_datetime

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start_datetime.isoformat(),
            timeMax=end_datetime.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    items_keys = [
        "attachments",
        "attendees",
        "creator",
        "description",
        "end",
        "eventType",
        "htmlLink",
        "id",
        "location",
        "organizer",
        "start",
        "summary",
        "visibility",
    ]

    events = [
        {key: event[key] for key in items_keys if key in event}
        for event in events_result.get("items", [])
    ]

    return {"events_count": len(events), "events": events}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
)
async def update_event(
    context: ToolContext,
    event_id: Annotated[str, "The ID of the event to update"],
    updated_start_day: Annotated[
        Day | None,
        "The updated day that the event starts. Combined with updated_start_time to form the new start time",
    ] = None,
    updated_start_time: Annotated[
        TimeSlot | None,
        "The updated time that the event starts. Combined with updated_start_day to form the new start time",
    ] = None,
    updated_end_day: Annotated[
        Day | None,
        "The updated day that the event ends. Combined with updated_end_time to form the new end time",
    ] = None,
    updated_end_time: Annotated[TimeSlot | None, "The updated time that the event ends"] = None,
    updated_calendar_id: Annotated[
        str | None, "The updated ID of the calendar containing the event"
    ] = None,
    updated_summary: Annotated[str | None, "The updated title of the event"] = None,
    updated_description: Annotated[str | None, "The updated description of the event"] = None,
    updated_location: Annotated[str | None, "The updated location of the event"] = None,
    updated_visibility: Annotated[EventVisibility | None, "The visibility of the event"] = None,
    attendee_emails_to_add: Annotated[
        list[str] | None,
        "The list of updated attendee emails to add. Must be valid email addresses e.g., username@domain.com",
    ] = None,
    attendee_emails_to_remove: Annotated[
        list[str] | None,
        "The list of attendee emails to remove. Must be valid email addresses e.g., username@domain.com",
    ] = None,
    send_updates: Annotated[
        SendUpdatesOptions, "Guests who should receive notifications about the event update"
    ] = SendUpdatesOptions.ALL,
) -> Annotated[
    str,
    "A string containing the updated event details, including the event ID, update timestamp, and a link to view the updated event",
]:
    """
    Update an existing event in the specified calendar with the provided details.
    Only the provided fields will be updated; others will remain unchanged.

    `updated_start_day` and `updated_start_time` must be provided together.
    `updated_end_day` and `updated_end_time` must be provided together.
    """
    service = build("calendar", "v3", credentials=Credentials(context.authorization.token))

    calendar = service.calendars().get(calendarId="primary").execute()
    time_zone = calendar["timeZone"]

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
    except HttpError:  # TODO: This is a first pass. We should do better.
        valid_events_with_id = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=(datetime.now() - timedelta(days=2)).isoformat(),
                timeMax=(datetime.now() - timedelta(days=2)).isoformat(),
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        raise RetryableToolError(
            f"Event with ID {event_id} not found.",
            additional_prompt_content=f"Here is list of valid events. The event_id parameter must match one of these: {valid_events_with_id}",
            retry_after_ms=1000,
            developer_message=f"Event with ID {event_id} not found. Please try again with a valid event ID.",
        )

    update_fields = {
        "start": _update_datetime(updated_start_day, updated_start_time, time_zone),
        "end": _update_datetime(updated_end_day, updated_end_time, time_zone),
        "calendarId": updated_calendar_id,
        "sendUpdates": send_updates.value if send_updates else None,
        "summary": updated_summary,
        "description": updated_description,
        "location": updated_location,
        "visibility": updated_visibility.value if updated_visibility else None,
    }

    event.update({k: v for k, v in update_fields.items() if v is not None})

    if attendee_emails_to_remove:
        event["attendees"] = [
            attendee
            for attendee in event.get("attendees", [])
            if attendee.get("email", "") not in attendee_emails_to_remove
        ]
    if attendee_emails_to_add:
        event["attendees"] = event.get("attendees", []) + [
            {"email": email} for email in attendee_emails_to_add
        ]

    updated_event = (
        service.events()
        .update(
            calendarId="primary",
            eventId=event_id,
            sendUpdates=send_updates.value,
            body=event,
        )
        .execute()
    )
    return f"Event with ID {event_id} successfully updated at {updated_event['updated']}. View updated event at {updated_event['htmlLink']}"


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
)
async def delete_event(
    context: ToolContext,
    event_id: Annotated[str, "The ID of the event to delete"],
    calendar_id: Annotated[str, "The ID of the calendar containing the event"] = "primary",
    send_updates: Annotated[
        SendUpdatesOptions, "Specifies which attendees to notify about the deletion"
    ] = SendUpdatesOptions.ALL,
) -> Annotated[str, "A string containing the deletion confirmation message"]:
    """Delete an event from Google Calendar."""
    service = build("calendar", "v3", credentials=Credentials(context.authorization.token))

    service.events().delete(
        calendarId=calendar_id, eventId=event_id, sendUpdates=send_updates.value
    ).execute()

    notification_message = ""
    if send_updates == SendUpdatesOptions.ALL:
        notification_message = "Notifications were sent to all attendees."
    elif send_updates == SendUpdatesOptions.EXTERNAL_ONLY:
        notification_message = "Notifications were sent to external attendees only."
    elif send_updates == SendUpdatesOptions.NONE:
        notification_message = "No notifications were sent to attendees."

    return f"Event with ID '{event_id}' successfully deleted from calendar '{calendar_id}'. {notification_message}"

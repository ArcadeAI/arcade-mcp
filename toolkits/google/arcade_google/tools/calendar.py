import json
from datetime import datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google
from arcade_tdk.errors import RetryableToolError
from googleapiclient.errors import HttpError

from arcade_google.models import EventVisibility, SendUpdatesOptions
from arcade_google.utils import (
    build_calendar_service,
    build_oauth_service,
    compute_free_time_intersection,
    parse_datetime,
)


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ]
    )
)
async def list_calendars(
    context: ToolContext,
    max_results: Annotated[
        int, "The maximum number of calendars to return. Up to 250 calendars, defaults to 10."
    ] = 10,
    show_deleted: Annotated[bool, "Whether to show deleted calendars. Defaults to False"] = False,
    show_hidden: Annotated[bool, "Whether to show hidden calendars. Defaults to False"] = False,
    next_page_token: Annotated[
        str | None, "The token to retrieve the next page of calendars. Optional."
    ] = None,
) -> Annotated[dict, "A dictionary containing the calendars accessible by the end user"]:
    """
    List all calendars accessible by the user.
    """
    max_results = max(1, min(max_results, 250))
    service = build_calendar_service(context.get_auth_token_or_empty())
    calendars = (
        service.calendarList()
        .list(
            pageToken=next_page_token,
            showDeleted=show_deleted,
            showHidden=show_hidden,
            maxResults=max_results,
        )
        .execute()
    )

    items = calendars.get("items", [])
    keys = ["description", "id", "summary", "timeZone"]
    relevant_items = [{k: i.get(k) for k in keys if i.get(k)} for i in items]
    return {
        "next_page_token": calendars.get("nextPageToken"),
        "num_calendars": len(relevant_items),
        "calendars": relevant_items,
    }


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
    start_datetime: Annotated[
        str,
        "The datetime when the event starts in ISO 8601 format, e.g., '2024-12-31T15:30:00'.",
    ],
    end_datetime: Annotated[
        str,
        "The datetime when the event ends in ISO 8601 format, e.g., '2024-12-31T17:30:00'.",
    ],
    calendar_id: Annotated[
        str, "The ID of the calendar to create the event in, usually 'primary'."
    ] = "primary",
    description: Annotated[str | None, "The description of the event"] = None,
    location: Annotated[str | None, "The location of the event"] = None,
    visibility: Annotated[EventVisibility, "The visibility of the event"] = EventVisibility.DEFAULT,
    attendee_emails: Annotated[
        list[str] | None,
        "The list of attendee emails. Must be valid email addresses e.g., username@domain.com.",
    ] = None,
) -> Annotated[dict, "A dictionary containing the created event details"]:
    """Create a new event/meeting/sync/meetup in the specified calendar."""

    service = build_calendar_service(context.get_auth_token_or_empty())

    # Get the calendar's time zone
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    time_zone = calendar["timeZone"]

    # Parse datetime strings
    start_dt = parse_datetime(start_datetime, time_zone)
    end_dt = parse_datetime(end_datetime, time_zone)

    event: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": time_zone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": time_zone},
        "visibility": visibility.value,
    }

    if attendee_emails:
        event["attendees"] = [{"email": email} for email in attendee_emails]

    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    return {"event": created_event}


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
    )
)
async def list_events(
    context: ToolContext,
    min_end_datetime: Annotated[
        str,
        "Filter by events that end on or after this datetime in ISO 8601 format, "
        "e.g., '2024-09-15T09:00:00'.",
    ],
    max_start_datetime: Annotated[
        str,
        "Filter by events that start before this datetime in ISO 8601 format, "
        "e.g., '2024-09-16T17:00:00'.",
    ],
    calendar_id: Annotated[str, "The ID of the calendar to list events from"] = "primary",
    max_results: Annotated[int, "The maximum number of events to return"] = 10,
) -> Annotated[dict, "A dictionary containing the list of events"]:
    """
    List events from the specified calendar within the given datetime range.

    min_end_datetime serves as the lower bound (exclusive) for an event's end time.
    max_start_datetime serves as the upper bound (exclusive) for an event's start time.

    For example:
    If min_end_datetime is set to 2024-09-15T09:00:00 and max_start_datetime
    is set to 2024-09-16T17:00:00, the function will return events that:
    1. End after 09:00 on September 15, 2024 (exclusive)
    2. Start before 17:00 on September 16, 2024 (exclusive)
    This means an event starting at 08:00 on September 15 and
    ending at 10:00 on September 15 would be included, but an
    event starting at 17:00 on September 16 would not be included.
    """
    service = build_calendar_service(context.get_auth_token_or_empty())

    # Get the calendar's time zone
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    time_zone = calendar["timeZone"]

    # Parse datetime strings
    min_end_dt = parse_datetime(min_end_datetime, time_zone)
    max_start_dt = parse_datetime(max_start_datetime, time_zone)

    if min_end_dt > max_start_dt:
        min_end_dt, max_start_dt = max_start_dt, min_end_dt

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=min_end_dt.isoformat(),
            timeMax=max_start_dt.isoformat(),
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
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
)
async def update_event(
    context: ToolContext,
    event_id: Annotated[str, "The ID of the event to update"],
    updated_start_datetime: Annotated[
        str | None,
        "The updated datetime that the event starts in ISO 8601 format, "
        "e.g., '2024-12-31T15:30:00'.",
    ] = None,
    updated_end_datetime: Annotated[
        str | None,
        "The updated datetime that the event ends in ISO 8601 format, e.g., '2024-12-31T17:30:00'.",
    ] = None,
    updated_calendar_id: Annotated[
        str | None, "The updated ID of the calendar containing the event."
    ] = None,
    updated_summary: Annotated[str | None, "The updated title of the event"] = None,
    updated_description: Annotated[str | None, "The updated description of the event"] = None,
    updated_location: Annotated[str | None, "The updated location of the event"] = None,
    updated_visibility: Annotated[EventVisibility | None, "The visibility of the event"] = None,
    attendee_emails_to_add: Annotated[
        list[str] | None,
        "The list of attendee emails to add. Must be valid email addresses "
        "e.g., username@domain.com.",
    ] = None,
    attendee_emails_to_remove: Annotated[
        list[str] | None,
        "The list of attendee emails to remove. Must be valid email addresses "
        "e.g., username@domain.com.",
    ] = None,
    send_updates: Annotated[
        SendUpdatesOptions,
        "Should attendees be notified of the update? (none, all, external_only)",
    ] = SendUpdatesOptions.ALL,
) -> Annotated[
    str,
    "A string containing the updated event details, including the event ID, update timestamp, "
    "and a link to view the updated event.",
]:
    """
    Update an existing event in the specified calendar with the provided details.
    Only the provided fields will be updated; others will remain unchanged.

    `updated_start_datetime` and `updated_end_datetime` are
    independent and can be provided separately.
    """
    service = build_calendar_service(context.get_auth_token_or_empty())

    calendar = service.calendars().get(calendarId="primary").execute()
    time_zone = calendar["timeZone"]

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
    except HttpError:
        valid_events_with_id = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=(datetime.now() - timedelta(days=2)).isoformat(),
                timeMax=(datetime.now() + timedelta(days=365)).isoformat(),
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        raise RetryableToolError(
            f"Event with ID {event_id} not found.",
            additional_prompt_content=(
                f"Here is a list of valid events. The event_id parameter must match one of these: "
                f"{valid_events_with_id}"
            ),
            retry_after_ms=1000,
            developer_message=(
                f"Event with ID {event_id} not found. Please try again with a valid event ID."
            ),
        )

    update_fields = {
        "start": {"dateTime": updated_start_datetime, "timeZone": time_zone}
        if updated_start_datetime
        else None,
        "end": {"dateTime": updated_end_datetime, "timeZone": time_zone}
        if updated_end_datetime
        else None,
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
            if attendee.get("email", "").lower()
            not in [email.lower() for email in attendee_emails_to_remove]
        ]

    if attendee_emails_to_add:
        existing_emails = {
            attendee.get("email", "").lower() for attendee in event.get("attendees", [])
        }
        new_attendees = [
            {"email": email}
            for email in attendee_emails_to_add
            if email.lower() not in existing_emails
        ]
        event["attendees"] = event.get("attendees", []) + new_attendees

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
    return (
        f"Event with ID {event_id} successfully updated at {updated_event['updated']}. "
        f"View updated event at {updated_event['htmlLink']}"
    )


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
    service = build_calendar_service(context.get_auth_token_or_empty())

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

    return (
        f"Event with ID '{event_id}' successfully deleted from calendar '{calendar_id}'. "
        f"{notification_message}"
    )


# TODO: would be nice to have a "min_slot_duration" parameter
# TODO: find a way to have "include_weekends" parameter without confusing LLMs
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    ),
)
async def find_time_slots_when_everyone_is_free(
    context: ToolContext,
    email_addresses: Annotated[
        list[str] | None,
        "The list of email addresses from people in the same organization domain (apart from the "
        "currently logged in user) to search for free time slots. Defaults to None, which will "
        "return free time slots for the current user only.",
    ] = None,
    start_date: Annotated[
        str | None,
        "The start date to search for time slots in the format 'YYYY-MM-DD'. Defaults to today's "
        "date. It will search starting from this date at the time 00:00:00.",
    ] = None,
    end_date: Annotated[
        str | None,
        "The end date to search for time slots in the format 'YYYY-MM-DD'. Defaults to seven days "
        "from the start date. It will search until this date at the time 23:59:59.",
    ] = None,
    start_time_boundary: Annotated[
        str,
        "Will return free slots in any given day starting from this time in the format 'HH:MM'. "
        "Defaults to '08:00', which is a usual business hour start time.",
    ] = "08:00",
    end_time_boundary: Annotated[
        str,
        "Will return free slots in any given day until this time in the format 'HH:MM'. "
        "Defaults to '18:00', which is a usual business hour end time.",
    ] = "18:00",
) -> Annotated[
    dict,
    "A dictionary with the free slots and the timezone in which time slots are represented.",
]:
    """
    Provides time slots when everyone is free within a given date range and time boundaries.
    """

    # Build google api services
    oauth_service = build_oauth_service(context.get_auth_token_or_empty())
    calendar_service = build_calendar_service(context.get_auth_token_or_empty())

    email_addresses = email_addresses or []

    if isinstance(email_addresses, str):
        email_addresses = [email_addresses]

    # Add the currently logged in user to the list of email addresses
    user_info = oauth_service.userinfo().get().execute()
    if user_info["email"] not in email_addresses:
        email_addresses.append(user_info["email"])

    # Get the timezone of the currently logged in user
    calendar = calendar_service.calendars().get(calendarId="primary").execute()
    timezone_name = calendar.get("timeZone")

    try:
        tz = ZoneInfo(timezone_name)
    # If the calendar timezone name is not supported by Python's zoneinfo, use UTC
    except ZoneInfoNotFoundError:
        timezone_name = "UTC"
        tz = ZoneInfo("UTC")

    # Set default start and end dates, if not provided by the caller
    start_date = start_date or datetime.now(tz=tz).date().isoformat()
    end_date = end_date or (datetime.now(tz=tz).date() + timedelta(days=7)).isoformat()

    # Parse start and end dates to datetime objects
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
    )
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=0, tzinfo=tz
    )

    # Get the busy slots from the calendars of the users
    freebusy_response = (
        calendar_service.freebusy()
        .query(
            body={
                "timeMin": start_datetime.isoformat(),
                "timeMax": end_datetime.isoformat(),
                "timeZone": timezone_name,
                "items": [{"id": email_address} for email_address in email_addresses],
            }
        )
        .execute()
    )
    busy_slots = freebusy_response["calendars"]

    response_errors = []

    for email in email_addresses:
        if "errors" not in busy_slots[email]:
            continue
        errors = busy_slots[email]["errors"]
        for error in errors:
            response_errors.append(
                f"Error retrieving free slots from calendar of '{email}': "
                f"{error.get('reason', 'not determined')}"
            )

    if response_errors:
        raise RetryableToolError(
            "Error retrieving free slots from calendars of one or more users.",
            additional_prompt_content=json.dumps(response_errors),
            retry_after_ms=1000,
            developer_message="Error retrieving free slots from calendars of one or more users.",
        )

    # Compute the free slots
    free_slots = compute_free_time_intersection(
        busy_data=busy_slots,
        global_start=start_datetime,
        global_end=end_datetime,
        start_time_boundary=datetime.strptime(start_time_boundary, "%H:%M")
        .time()
        .replace(tzinfo=tz),
        end_time_boundary=datetime.strptime(end_time_boundary, "%H:%M").time().replace(tzinfo=tz),
        include_weekends=True,
        tz=tz,
    )

    return {
        "free_slots": free_slots,
        "timezone": timezone_name,
    }

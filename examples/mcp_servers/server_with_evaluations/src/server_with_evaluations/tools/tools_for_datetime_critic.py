from datetime import datetime
from typing import Annotated

from arcade_mcp_server import tool


@tool
def get_meeting_reminder(
    event_datetime: Annotated[str, "The date and time of the event in ISO format"],
    reminder_minutes: Annotated[int, "Minutes before the event to remind"] = 15,
) -> dict[str, str]:
    """
    Calculate the reminder time for a meeting.

    Useful when you need to schedule reminders for important events.
    This tool helps manage calendar-based tasks.
    """
    event_dt = datetime.fromisoformat(event_datetime)
    reminder_dt = event_dt.replace(minute=event_dt.minute - reminder_minutes)
    return {
        "reminder_time": reminder_dt.isoformat(),
        "event_time": event_datetime,
        "reminder_minutes": reminder_minutes,
    }


@tool
def calculate_time_until_event(
    event_datetime: Annotated[str, "The date and time of the event in ISO format"],
    from_datetime: Annotated[str, "The current or reference date and time in ISO format"],
) -> dict[str, str]:
    """
    Calculate the time remaining until an event.

    Provides a time difference calculation, useful for scheduling
    and time management scenarios.
    """
    event_dt = datetime.fromisoformat(event_datetime)
    from_dt = datetime.fromisoformat(from_datetime)
    delta = event_dt - from_dt

    return {
        "time_remaining": str(delta),
        "event_datetime": event_datetime,
        "from_datetime": from_datetime,
    }

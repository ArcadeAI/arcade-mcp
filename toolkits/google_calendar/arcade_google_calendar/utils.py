import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def parse_datetime(datetime_str: str, time_zone: str) -> datetime:
    """
    Parse a datetime string in ISO 8601 format and ensure it is timezone-aware.

    Args:
        datetime_str (str): The datetime string to parse. Expected format: 'YYYY-MM-DDTHH:MM:SS'.
        time_zone (str): The timezone to apply if the datetime string is naive.

    Returns:
        datetime: A timezone-aware datetime object.

    Raises:
        ValueError: If the datetime string is not in the correct format.
    """
    datetime_str = datetime_str.upper().strip().rstrip("Z")
    try:
        dt = datetime.fromisoformat(datetime_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(time_zone))
    except ValueError as e:
        raise ValueError(
            f"Invalid datetime format: '{datetime_str}'. "
            "Expected ISO 8601 format, e.g., '2024-12-31T15:30:00'."
        ) from e
    return dt


def build_oauth_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build an OAuth2 service object.
    """
    auth_token = auth_token or ""
    return build("oauth2", "v2", credentials=Credentials(auth_token))


def build_calendar_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Calendar service object.
    """
    auth_token = auth_token or ""
    return build("calendar", "v3", credentials=Credentials(auth_token))


def weekday_to_name(weekday: int) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday]


def get_time_boundaries_for_date(
    current_date: date,
    global_start: datetime,
    global_end: datetime,
    start_time_boundary: time,
    end_time_boundary: time,
    tz: ZoneInfo,
) -> tuple[datetime, datetime]:
    """Compute the allowed start and end times for the given day, adjusting for global bounds."""
    day_start_time = datetime.combine(current_date, start_time_boundary).replace(tzinfo=tz)
    day_end_time = datetime.combine(current_date, end_time_boundary).replace(tzinfo=tz)

    if current_date == global_start.date():
        day_start_time = max(day_start_time, global_start)

    if current_date == global_end.date():
        day_end_time = min(day_end_time, global_end)

    return day_start_time, day_end_time


def gather_busy_intervals(
    busy_data: dict[str, Any],
    day_start: datetime,
    day_end: datetime,
    business_tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    """
    Collect busy intervals from all calendars that intersect with the day's business hours.
    Busy intervals are clipped to lie within [day_start, day_end].
    """
    busy_intervals = []
    for calendar in busy_data:
        for slot in busy_data[calendar].get("busy", []):
            slot_start = parse_rfc3339_datetime_str(slot["start"]).astimezone(business_tz)
            slot_end = parse_rfc3339_datetime_str(slot["end"]).astimezone(business_tz)
            if slot_end > day_start and slot_start < day_end:
                busy_intervals.append((max(slot_start, day_start), min(slot_end, day_end)))
    return busy_intervals


def subtract_busy_intervals(
    business_start: datetime,
    business_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
) -> list[dict[str, Any]]:
    """
    Subtract the merged busy intervals from the business hours and return free time slots.
    """
    free_slots = []
    merged_busy = merge_intervals(busy_intervals)

    # If there are no busy intervals, return the entire business window as free.
    if not merged_busy:
        return [
            {
                "start": {
                    "datetime": business_start.isoformat(),
                    "weekday": weekday_to_name(business_start.weekday()),
                },
                "end": {
                    "datetime": business_end.isoformat(),
                    "weekday": weekday_to_name(business_end.weekday()),
                },
            }
        ]

    current_free_start = business_start
    for busy_start, busy_end in merged_busy:
        if current_free_start < busy_start:
            free_slots.append({
                "start": {
                    "datetime": current_free_start.isoformat(),
                    "weekday": weekday_to_name(current_free_start.weekday()),
                },
                "end": {
                    "datetime": busy_start.isoformat(),
                    "weekday": weekday_to_name(busy_start.weekday()),
                },
            })
        current_free_start = max(current_free_start, busy_end)
    if current_free_start < business_end:
        free_slots.append({
            "start": {
                "datetime": current_free_start.isoformat(),
                "weekday": weekday_to_name(current_free_start.weekday()),
            },
            "end": {
                "datetime": business_end.isoformat(),
                "weekday": weekday_to_name(business_end.weekday()),
            },
        })
    return free_slots


def compute_free_time_intersection(
    busy_data: dict[str, Any],
    global_start: datetime,
    global_end: datetime,
    start_time_boundary: time,
    end_time_boundary: time,
    include_weekends: bool,
    tz: ZoneInfo,
) -> list[dict[str, Any]]:
    """
    Returns the free time slots across all calendars within the global bounds,
    ensuring that the global start is not in the past.

    Only considers business days (Monday to Friday) and business hours (08:00-19:00)
    in the provided timezone.
    """
    # Ensure global_start is never in the past relative to now.
    now = get_now(tz)

    if now > global_start:
        global_start = now

    # If after adjusting the start, there's no interval left, return empty.
    if global_start >= global_end:
        return []

    free_slots = []
    current_date = global_start.date()

    while current_date <= global_end.date():
        if not include_weekends and current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        day_start, day_end = get_time_boundaries_for_date(
            current_date=current_date,
            global_start=global_start,
            global_end=global_end,
            start_time_boundary=start_time_boundary,
            end_time_boundary=end_time_boundary,
            tz=tz,
        )

        # Skip if the day's allowed time window is empty.
        if day_start >= day_end:
            current_date += timedelta(days=1)
            continue

        busy_intervals = gather_busy_intervals(busy_data, day_start, day_end, tz)
        free_slots.extend(subtract_busy_intervals(day_start, day_end, busy_intervals))

        current_date += timedelta(days=1)

    return free_slots


def get_now(tz: ZoneInfo | None = None) -> datetime:
    if not tz:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def parse_rfc3339_datetime_str(dt_str: str, tz: timezone = timezone.utc) -> datetime:
    """
    Parse an RFC3339 datetime string into a timezone-aware datetime.
    Converts a trailing 'Z' (UTC) into +00:00.
    If the parsed datetime is naive, assume it is in the provided timezone.
    """
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """
    Given a list of (start, end) tuples, merge overlapping or adjacent intervals.
    """
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(intervals, key=lambda x: x[0]):
        if not merged:
            merged.append((start, end))
        else:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
    return merged

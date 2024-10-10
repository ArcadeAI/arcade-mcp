from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------- #
# Google Calendar Models and Enums
# ---------------------------------------------------------------------------- #
class DateRange(Enum):
    TODAY = "today"
    TOMORROW = "tomorrow"
    THIS_WEEK = "this_week"
    NEXT_WEEK = "next_week"
    THIS_MONTH = "this_month"
    NEXT_MONTH = "next_month"

    def to_date_range(self):
        today = datetime.now().date()
        if self == DateRange.TODAY:
            return today, today + timedelta(days=1)
        elif self == DateRange.TOMORROW:
            return today + timedelta(days=1), today + timedelta(days=2)
        elif self == DateRange.THIS_WEEK:
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=7)
        elif self == DateRange.NEXT_WEEK:
            start = today + timedelta(days=7 - today.weekday())
            return start, start + timedelta(days=7)
        elif self == DateRange.THIS_MONTH:
            start = today.replace(day=1)
            next_month = start + timedelta(days=32)
            end = next_month.replace(day=1)
            return start, end
        elif self == DateRange.NEXT_MONTH:
            start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            next_month = start + timedelta(days=32)
            end = next_month.replace(day=1)
            return start, end

    def to_datetime_range(self, time_zone_name: str | None = None) -> tuple[datetime, datetime]:
        start_date, end_date = self.to_date_range()
        # time_zone = ZoneInfo(time_zone_name)
        start_datetime = datetime.combine(
            start_date, datetime.min.time()
        )  # .replace(tzinfo=time_zone)
        end_datetime = datetime.combine(end_date, datetime.min.time())  # .replace(tzinfo=time_zone)
        return start_datetime, end_datetime


class Day(Enum):
    # TODO: THere are obvious limitations here. We should do better and support any date.
    YESTERDAY = "yesterday"
    TODAY = "today"
    TOMORROW = "tomorrow"
    THIS_SUNDAY = "this_sunday"
    THIS_MONDAY = "this_monday"
    THIS_TUESDAY = "this_tuesday"
    THIS_WEDNESDAY = "this_wednesday"
    THIS_THURSDAY = "this_thursday"
    THIS_FRIDAY = "this_friday"
    THIS_SATURDAY = "this_saturday"
    NEXT_SUNDAY = "next_sunday"
    NEXT_MONDAY = "next_monday"
    NEXT_TUESDAY = "next_tuesday"
    NEXT_WEDNESDAY = "next_wednesday"
    NEXT_THURSDAY = "next_thursday"
    NEXT_FRIDAY = "next_friday"
    NEXT_SATURDAY = "next_saturday"

    def to_date(self, time_zone_name: str):
        time_zone = ZoneInfo(time_zone_name)
        today = datetime.now(time_zone).date()
        weekday = today.weekday()

        if self == Day.YESTERDAY:
            return today - timedelta(days=1)
        elif self == Day.TODAY:
            return today
        elif self == Day.TOMORROW:
            return today + timedelta(days=1)

        day_offsets = {
            Day.THIS_SUNDAY: 6,
            Day.THIS_MONDAY: 0,
            Day.THIS_TUESDAY: 1,
            Day.THIS_WEDNESDAY: 2,
            Day.THIS_THURSDAY: 3,
            Day.THIS_FRIDAY: 4,
            Day.THIS_SATURDAY: 5,
        }

        if self in day_offsets:
            return today + timedelta(days=(day_offsets[self] - weekday) % 7)

        next_week_offsets = {
            Day.NEXT_SUNDAY: 6,
            Day.NEXT_MONDAY: 0,
            Day.NEXT_TUESDAY: 1,
            Day.NEXT_WEDNESDAY: 2,
            Day.NEXT_THURSDAY: 3,
            Day.NEXT_FRIDAY: 4,
            Day.NEXT_SATURDAY: 5,
        }

        if self in next_week_offsets:
            return today + timedelta(days=(next_week_offsets[self] - weekday + 7) % 7)

        raise ValueError(f"Invalid Day enum value: {self}")


class TimeSlot(Enum):
    _0000 = "00:00"
    _0015 = "00:15"
    _0030 = "00:30"
    _0045 = "00:45"
    _0100 = "01:00"
    _0115 = "01:15"
    _0130 = "01:30"
    _0145 = "01:45"
    _0200 = "02:00"
    _0215 = "02:15"
    _0230 = "02:30"
    _0245 = "02:45"
    _0300 = "03:00"
    _0315 = "03:15"
    _0330 = "03:30"
    _0345 = "03:45"
    _0400 = "04:00"
    _0415 = "04:15"
    _0430 = "04:30"
    _0445 = "04:45"
    _0500 = "05:00"
    _0515 = "05:15"
    _0530 = "05:30"
    _0545 = "05:45"
    _0600 = "06:00"
    _0615 = "06:15"
    _0630 = "06:30"
    _0645 = "06:45"
    _0700 = "07:00"
    _0715 = "07:15"
    _0730 = "07:30"
    _0745 = "07:45"
    _0800 = "08:00"
    _0815 = "08:15"
    _0830 = "08:30"
    _0845 = "08:45"
    _0900 = "09:00"
    _0915 = "09:15"
    _0930 = "09:30"
    _0945 = "09:45"
    _1000 = "10:00"
    _1015 = "10:15"
    _1030 = "10:30"
    _1045 = "10:45"
    _1100 = "11:00"
    _1115 = "11:15"
    _1130 = "11:30"
    _1145 = "11:45"
    _1200 = "12:00"
    _1215 = "12:15"
    _1230 = "12:30"
    _1245 = "12:45"
    _1300 = "13:00"
    _1315 = "13:15"
    _1330 = "13:30"
    _1345 = "13:45"
    _1400 = "14:00"
    _1415 = "14:15"
    _1430 = "14:30"
    _1445 = "14:45"
    _1500 = "15:00"
    _1515 = "15:15"
    _1530 = "15:30"
    _1545 = "15:45"
    _1600 = "16:00"
    _1615 = "16:15"
    _1630 = "16:30"
    _1645 = "16:45"
    _1700 = "17:00"
    _1715 = "17:15"
    _1730 = "17:30"
    _1745 = "17:45"
    _1800 = "18:00"
    _1815 = "18:15"
    _1830 = "18:30"
    _1845 = "18:45"
    _1900 = "19:00"
    _1915 = "19:15"
    _1930 = "19:30"
    _1945 = "19:45"
    _2000 = "20:00"
    _2015 = "20:15"
    _2030 = "20:30"
    _2045 = "20:45"
    _2100 = "21:00"
    _2115 = "21:15"
    _2130 = "21:30"
    _2145 = "21:45"
    _2200 = "22:00"
    _2215 = "22:15"
    _2230 = "22:30"
    _2245 = "22:45"
    _2300 = "23:00"
    _2315 = "23:15"
    _2330 = "23:30"
    _2345 = "23:45"

    def to_time(self):
        return datetime.strptime(self.value, "%H:%M").time()


class EventVisibility(Enum):
    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class EventType(Enum):
    BIRTHDAY = "birthday"  # Special all-day events with an annual recurrence.
    DEFAULT = "default"  # Regular events
    FOCUS_TIME = "focusTime"  # Focus time events
    FROM_GMAIL = "fromGmail"  # Events from Gmail
    OUT_OF_OFFICE = "outOfOffice"  # Out of office events
    WORKING_LOCATION = "workingLocation"  # Working location events


class SendUpdatesOptions(Enum):
    NONE = "none"  # No notifications are sent
    ALL = "all"  # Notifications are sent to all guests
    EXTERNAL_ONLY = "externalOnly"  # Notifications are sent to non-Google Calendar guests only.


# Utils for Google Drive tools
class Corpora(str, Enum):
    """
    Bodies of items (files/documents) to which the query applies.
    Prefer 'user' or 'drive' to 'allDrives' for efficiency.
    By default, corpora is set to 'user'.
    """

    USER = "user"
    DOMAIN = "domain"
    DRIVE = "drive"
    ALL_DRIVES = "allDrives"


class OrderBy(str, Enum):
    """
    Sort keys for ordering files in Google Drive.
    Each key has both ascending and descending options.
    """

    CREATED_TIME = "createdTime"  # When the file was created (ascending)
    CREATED_TIME_DESC = "createdTime desc"  # When the file was created (descending)
    FOLDER = "folder"  # The folder ID, sorted using alphabetical ordering (ascending)
    FOLDER_DESC = "folder desc"  # The folder ID, sorted using alphabetical ordering (descending)
    MODIFIED_BY_ME_TIME = (
        "modifiedByMeTime"  # The last time the file was modified by the user (ascending)
    )
    MODIFIED_BY_ME_TIME_DESC = (
        "modifiedByMeTime desc"  # The last time the file was modified by the user (descending)
    )
    MODIFIED_TIME = "modifiedTime"  # The last time the file was modified by anyone (ascending)
    MODIFIED_TIME_DESC = (
        "modifiedTime desc"  # The last time the file was modified by anyone (descending)
    )
    NAME = "name"  # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (ascending)
    NAME_DESC = "name desc"  # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (descending)
    NAME_NATURAL = "name_natural"  # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (ascending)
    NAME_NATURAL_DESC = "name_natural desc"  # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (descending)
    QUOTA_BYTES_USED = (
        "quotaBytesUsed"  # The number of storage quota bytes used by the file (ascending)
    )
    QUOTA_BYTES_USED_DESC = (
        "quotaBytesUsed desc"  # The number of storage quota bytes used by the file (descending)
    )
    RECENCY = "recency"  # The most recent timestamp from the file's date-time fields (ascending)
    RECENCY_DESC = (
        "recency desc"  # The most recent timestamp from the file's date-time fields (descending)
    )
    SHARED_WITH_ME_TIME = (
        "sharedWithMeTime"  # When the file was shared with the user, if applicable (ascending)
    )
    SHARED_WITH_ME_TIME_DESC = "sharedWithMeTime desc"  # When the file was shared with the user, if applicable (descending)
    STARRED = "starred"  # Whether the user has starred the file (ascending)
    STARRED_DESC = "starred desc"  # Whether the user has starred the file (descending)
    VIEWED_BY_ME_TIME = (
        "viewedByMeTime"  # The last time the file was viewed by the user (ascending)
    )
    VIEWED_BY_ME_TIME_DESC = (
        "viewedByMeTime desc"  # The last time the file was viewed by the user (descending)
    )

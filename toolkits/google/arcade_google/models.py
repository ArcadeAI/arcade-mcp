import json
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator, model_validator


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

    def to_datetime_range(
        self,
        start_time: time | None = None,
        end_time: time | None = None,
        time_zone: ZoneInfo | None = None,
        today: date | None = None,
    ) -> tuple[datetime, datetime]:
        """
        Convert a DateRange enum value to a tuple with two datetime objects representing the start
        and end of the date range.

        :param start_time: The start time of the date range. Defaults to the current time.
        :param end_time: The end time of the date range. Defaults to 23:59:59.
        :param time_zone: The time zone to use for the date range. Defaults to UTC.
        :param today: Today's date. Defaults to the current date provided by `datetime.now().date()`
        """
        start_time = start_time or datetime.now().time()
        end_time = end_time or time(23, 59, 59)
        today = today or datetime.now().date()

        if self == DateRange.TODAY:
            start_date, end_date = today, today
        elif self == DateRange.TOMORROW:
            start_date, end_date = today + timedelta(days=1), today + timedelta(days=1)
        elif self == DateRange.THIS_WEEK:
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif self == DateRange.NEXT_WEEK:
            start_date = today + timedelta(days=7 - today.weekday())
            end_date = start_date + timedelta(days=6)
        elif self == DateRange.THIS_MONTH:
            start_date = today.replace(day=1)
            next_month = start_date + timedelta(days=31)
            end_date = next_month.replace(day=1) - timedelta(days=1)
        elif self == DateRange.NEXT_MONTH:
            start_date = (today.replace(day=1) + timedelta(days=31)).replace(day=1)
            next_month = start_date + timedelta(days=31)
            end_date = next_month.replace(day=1) - timedelta(days=1)
        else:
            raise ValueError(
                f"DateRange enum value: {self} is not supported for date range conversion"
            )

        start_time = start_time or time(0, 0, 0)
        end_time = end_time or time(23, 59, 59)

        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)

        if time_zone:
            start_datetime = start_datetime.replace(tzinfo=time_zone)
            end_datetime = end_datetime.replace(tzinfo=time_zone)

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

    def to_date(self, time_zone_name: str) -> date:
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

    def to_time(self) -> time:
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


# ---------------------------------------------------------------------------- #
# Google Drive Models and Enums
# ---------------------------------------------------------------------------- #
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

    CREATED_TIME = (
        # When the file was created (ascending)
        "createdTime"
    )
    CREATED_TIME_DESC = (
        # When the file was created (descending)
        "createdTime desc"
    )
    FOLDER = (
        # The folder ID, sorted using alphabetical ordering (ascending)
        "folder"
    )
    FOLDER_DESC = (
        # The folder ID, sorted using alphabetical ordering (descending)
        "folder desc"
    )
    MODIFIED_BY_ME_TIME = (
        # The last time the file was modified by the user (ascending)
        "modifiedByMeTime"
    )
    MODIFIED_BY_ME_TIME_DESC = (
        # The last time the file was modified by the user (descending)
        "modifiedByMeTime desc"
    )
    MODIFIED_TIME = (
        # The last time the file was modified by anyone (ascending)
        "modifiedTime"
    )
    MODIFIED_TIME_DESC = (
        # The last time the file was modified by anyone (descending)
        "modifiedTime desc"
    )
    NAME = (
        # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (ascending)
        "name"
    )
    NAME_DESC = (
        # The name of the file, sorted using alphabetical ordering (e.g., 1, 12, 2, 22) (descending)
        "name desc"
    )
    NAME_NATURAL = (
        # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (ascending)
        "name_natural"
    )
    NAME_NATURAL_DESC = (
        # The name of the file, sorted using natural sort ordering (e.g., 1, 2, 12, 22) (descending)
        "name_natural desc"
    )
    QUOTA_BYTES_USED = (
        # The number of storage quota bytes used by the file (ascending)
        "quotaBytesUsed"
    )
    QUOTA_BYTES_USED_DESC = (
        # The number of storage quota bytes used by the file (descending)
        "quotaBytesUsed desc"
    )
    RECENCY = (
        # The most recent timestamp from the file's date-time fields (ascending)
        "recency"
    )
    RECENCY_DESC = (
        # The most recent timestamp from the file's date-time fields (descending)
        "recency desc"
    )
    SHARED_WITH_ME_TIME = (
        # When the file was shared with the user, if applicable (ascending)
        "sharedWithMeTime"
    )
    SHARED_WITH_ME_TIME_DESC = (
        # When the file was shared with the user, if applicable (descending)
        "sharedWithMeTime desc"
    )
    STARRED = (
        # Whether the user has starred the file (ascending)
        "starred"
    )
    STARRED_DESC = (
        # Whether the user has starred the file (descending)
        "starred desc"
    )
    VIEWED_BY_ME_TIME = (
        # The last time the file was viewed by the user (ascending)
        "viewedByMeTime"
    )
    VIEWED_BY_ME_TIME_DESC = (
        # The last time the file was viewed by the user (descending)
        "viewedByMeTime desc"
    )


class DocumentFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    GOOGLE_API_JSON = "google_api_json"


# ---------------------------------------------------------------------------- #
# Google Gmail Models and Enums
# ---------------------------------------------------------------------------- #
class GmailReplyToWhom(str, Enum):
    EVERY_RECIPIENT = "every_recipient"
    ONLY_THE_SENDER = "only_the_sender"


class GmailAction(str, Enum):
    SEND = "send"
    DRAFT = "draft"


# ---------------------------------------------------------------------------- #
# Google Sheets Models and Enums
# ---------------------------------------------------------------------------- #
class CellErrorType(str, Enum):
    """The type of error in a cell

    Implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ErrorType
    """

    ERROR_TYPE_UNSPECIFIED = "ERROR_TYPE_UNSPECIFIED"  # The default error type, do not use this.
    ERROR = "ERROR"  # Corresponds to the #ERROR! error.
    NULL_VALUE = "NULL_VALUE"  # Corresponds to the #NULL! error.
    DIVIDE_BY_ZERO = "DIVIDE_BY_ZERO"  # Corresponds to the #DIV/0 error.
    VALUE = "VALUE"  # Corresponds to the #VALUE! error.
    REF = "REF"  # Corresponds to the #REF! error.
    NAME = "NAME"  # Corresponds to the #NAME? error.
    NUM = "NUM"  # Corresponds to the #NUM! error.
    N_A = "N_A"  # Corresponds to the #N/A error.
    LOADING = "LOADING"  # Corresponds to the Loading... state.


class CellErrorValue(BaseModel):
    """An error in a cell

    Implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ErrorValue
    """

    type: CellErrorType
    message: str


class CellExtendedValue(BaseModel):
    """The kinds of value that a cell in a spreadsheet can have

    Implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ExtendedValue
    """

    numberValue: float | None = None
    stringValue: str | None = None
    boolValue: bool | None = None
    formulaValue: str | None = None
    errorValue: Optional["CellErrorValue"] = None

    @model_validator(mode="after")
    def check_exactly_one_value(cls, instance):  # type: ignore[no-untyped-def]
        provided = [v for v in instance.__dict__.values() if v is not None]
        if len(provided) != 1:
            raise ValueError(
                "Exactly one of numberValue, stringValue, boolValue, "
                "formulaValue, or errorValue must be set."
            )
        return instance


class NumberFormatType(str, Enum):
    NUMBER = "NUMBER"
    PERCENT = "PERCENT"
    CURRENCY = "CURRENCY"


class NumberFormat(BaseModel):
    """The format of a number

    Implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#NumberFormat
    """

    pattern: str
    type: NumberFormatType


class CellFormat(BaseModel):
    """The format of a cell

    Partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#CellFormat
    """

    numberFormat: NumberFormat


class CellData(BaseModel):
    """Data about a specific cell

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#CellData
    """

    userEnteredValue: CellExtendedValue
    userEnteredFormat: CellFormat | None = None


class RowData(BaseModel):
    """Data about each cellin a row

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#RowData
    """

    values: list[CellData]


class GridData(BaseModel):
    """Data in the grid

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#GridData
    """

    startRow: int
    startColumn: int
    rowData: list[RowData]


class GridProperties(BaseModel):
    """Properties of a grid

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#GridProperties
    """

    rowCount: int
    columnCount: int


class SheetProperties(BaseModel):
    """Properties of a Sheet

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#SheetProperties
    """

    sheetId: int
    title: str
    gridProperties: GridProperties | None = None


class Sheet(BaseModel):
    """A Sheet in a spreadsheet

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#Sheet
    """

    properties: SheetProperties
    data: list[GridData] | None = None


class SpreadsheetProperties(BaseModel):
    """Properties of a spreadsheet

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#SpreadsheetProperties
    """

    title: str


class Spreadsheet(BaseModel):
    """A spreadsheet

    A partial implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets
    """

    properties: SpreadsheetProperties
    sheets: list[Sheet]


CellValue = int | float | str | bool


class SheetDataInput(BaseModel):
    """
    SheetDataInput models the cell data of a spreadsheet in a custom format.

    It is a dictionary mapping row numbers (as ints) to dictionaries that map
    column letters (as uppercase strings) to cell values (int, float, str, or bool).

    This model enforces that:
      - The outer keys are convertible to int.
      - The inner keys are alphabetic strings (normalized to uppercase).
      - All cell values are only of type int, float, str, or bool.

    The model automatically serializes (via `json_data()`)
    and validates the inner types.
    """

    data: dict[int, dict[str, CellValue]]

    @classmethod
    def _parse_json_if_string(cls, value):  # type: ignore[no-untyped-def]
        """Parses the value if it is a JSON string, otherwise returns it.

        Helper method for when validating the `data` field.
        """
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise TypeError(f"Invalid JSON: {e}")
        return value

    @classmethod
    def _validate_row_key(cls, row_key) -> int:  # type: ignore[no-untyped-def]
        """Converts the row key to an integer, raising an error if conversion fails.

        Helper method for when validating the `data` field.
        """
        try:
            return int(row_key)
        except (ValueError, TypeError):
            raise TypeError(f"Row key '{row_key}' is not convertible to int.")

    @classmethod
    def _validate_inner_cells(cls, cells, row_int: int) -> dict:  # type: ignore[no-untyped-def]
        """Validates that 'cells' is a dict mapping column letters to valid cell values
        and normalizes the keys.

        Helper method for when validating the `data` field.
        """
        if not isinstance(cells, dict):
            raise TypeError(
                f"Value for row '{row_int}' must be a dict mapping column letters to cell values."
            )
        new_inner = {}
        for col_key, cell_value in cells.items():
            if not isinstance(col_key, str):
                raise TypeError(f"Column key '{col_key}' must be a string.")
            col_string = col_key.upper()
            if not col_string.isalpha():
                raise TypeError(f"Column key '{col_key}' is invalid. Must be alphabetic.")
            if not isinstance(cell_value, int | float | str | bool):
                raise TypeError(
                    f"Cell value for {col_string}{row_int} must be an int, float, str, or bool."
                )
            new_inner[col_string] = cell_value
        return new_inner

    @field_validator("data", mode="before")
    @classmethod
    def validate_and_convert_keys(cls, value):  # type: ignore[no-untyped-def]
        """
        Validates data when SheetDataInput is instantiated and converts it to the correct format.
        Uses private helper methods to parse JSON, validate row keys, and validate inner cell data.
        """
        if value is None:
            return {}

        value = cls._parse_json_if_string(value)
        if isinstance(value, dict):
            new_value = {}
            for row_key, cells in value.items():
                row_int = cls._validate_row_key(row_key)
                inner_cells = cls._validate_inner_cells(cells, row_int)
                new_value[row_int] = inner_cells
            return new_value

        raise TypeError("data must be a dict or a valid JSON string representing a dict")

    def json_data(self) -> str:
        """
        Serialize the sheet data to a JSON string.
        """
        return json.dumps(self.data)

    @classmethod
    def from_json(cls, json_str: str) -> "SheetDataInput":
        """
        Create a SheetData instance from a JSON string.
        """
        return cls.model_validate_json(json_str)

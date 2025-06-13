import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_microsoft.outlook_calendar._utils import (
    convert_timezone_to_offset,
    is_valid_email,
    remove_timezone_offset,
    replace_timezone_offset,
    validate_date_times,
    validate_emails,
)


@pytest.mark.parametrize(
    "start_date_time, end_date_time, error_type",
    [
        (
            "2026-01-01T10:00:00",
            "2026-01-01T17:00:00",
            None,
        ),
        # end_date_time before start_date_time
        (
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
            ToolExecutionError,
        ),
        # end_date_time before start_date_time because timezone offset is ignored
        (
            "2026-01-01T10:00:00-07:00",
            "2026-01-01T09:00:00-08:00",
            ToolExecutionError,
        ),
        # not ISO 8601 format
        (
            "20260101T10:00:00",
            "2026-01-0109:00:00",
            ValueError,
        ),
    ],
)
def test_validate_date_times(start_date_time, end_date_time, error_type):
    if error_type:
        with pytest.raises(error_type):
            validate_date_times(start_date_time, end_date_time)
    else:
        validate_date_times(start_date_time, end_date_time)


@pytest.mark.parametrize(
    "emails, expect_error",
    [
        (["test@test.com"], False),
        (["test@test.com", "test@test.com.au"], False),
        (["test@test.com", "test@test.com.au."], True),
        (["#$&*@test.com"], True),
    ],
)
def test_validate_emails(emails, expect_error):
    if expect_error:
        with pytest.raises(ToolExecutionError):
            validate_emails(emails)
    else:
        validate_emails(emails)


@pytest.mark.parametrize(
    "email, is_valid",
    [
        ("test@test.com", True),
        ("test@test", False),
        ("test@test.com.au", True),
        ("test@test.com.au.", False),
    ],
)
def test_is_valid_email(email, is_valid):
    assert is_valid_email(email) == is_valid


@pytest.mark.parametrize(
    "input_date_time, expected_date_time",
    [
        ("2021-01-01T10:00:00+07:00", "2021-01-01T10:00:00"),
        ("2021-01-01T10:00:00-07:00", "2021-01-01T10:00:00"),
        ("2021-01-01T10:00:00Z", "2021-01-01T10:00:00"),
    ],
)
def test_remove_timezone_offset(input_date_time, expected_date_time):
    assert remove_timezone_offset(input_date_time) == expected_date_time


@pytest.mark.parametrize(
    "input_date_time, time_zone_offset, expected_date_time",
    [
        # without existing offset
        ("2021-01-01T10:00:00", "+07:00", "2021-01-01T10:00:00+07:00"),
        ("2021-01-01T10:00:00", "-07:00", "2021-01-01T10:00:00-07:00"),
        ("2021-01-01T10:00:00", "Z", "2021-01-01T10:00:00Z"),
        # with existing offset
        ("2021-01-01T10:00:00+07:00", "+04:00", "2021-01-01T10:00:00+04:00"),
        ("2021-01-01T10:00:00-07:00", "-09:00", "2021-01-01T10:00:00-09:00"),
        ("2021-01-01T10:00:00-07:00", "Z", "2021-01-01T10:00:00Z"),
    ],
)
def test_replace_timezone_offset(input_date_time, time_zone_offset, expected_date_time):
    assert replace_timezone_offset(input_date_time, time_zone_offset) == expected_date_time


@pytest.mark.parametrize(
    "time_zone, expected_offset",
    [
        ("Central Asia Standard Time", "+05:00"),  # Windows timezone format
        ("America/New_York", "-04:00"),  # IANA timezone format
        ("Not a valid timezone", "Z"),  # Fallback to UTC
    ],
)
def test_convert_timezone_to_offset(time_zone, expected_offset):
    assert convert_timezone_to_offset(time_zone) == expected_offset

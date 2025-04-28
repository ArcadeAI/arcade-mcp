import pytest

from arcade_microsoft.outlook_calendar._utils import (
    convert_timezone_to_offset,
    remove_timezone_offset,
    replace_timezone_offset,
)


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

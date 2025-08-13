"""Unit tests for OpenTable toolkit utility functions."""

from datetime import datetime, timedelta

import pytest
from arcade_opentable.utils import (
    validate_coordinates,
    validate_date_format,
    validate_email_format,
    validate_limit_parameter,
    validate_non_empty_string,
    validate_party_size,
    validate_phone_format,
    validate_time_format,
    validate_time_range,
)
from arcade_tdk.errors import RetryableToolError


class TestValidateDateFormat:
    """Test cases for validate_date_format function."""

    def test_valid_future_date(self):
        """Test that valid future dates pass validation."""
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        # Should not raise any exception
        validate_date_format(future_date)

    def test_valid_today_date(self):
        """Test that today's date passes validation."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Should not raise any exception
        validate_date_format(today)

    def test_past_date_not_allowed(self):
        """Test that past dates raise error when not allowed."""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        with pytest.raises(RetryableToolError, match="Date cannot be in the past"):
            validate_date_format(past_date, allow_past=False)

    def test_past_date_allowed(self):
        """Test that past dates pass when explicitly allowed."""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        # Should not raise any exception
        validate_date_format(past_date, allow_past=True)

    def test_invalid_date_format(self):
        """Test that invalid date formats raise error."""
        invalid_dates = [
            "2024/12/31",  # Wrong separator
            "31-12-2024",  # Wrong order
            "2024-13-01",  # Invalid month
            "2024-12-32",  # Invalid day
            "not-a-date",  # Completely invalid
        ]

        for invalid_date in invalid_dates:
            with pytest.raises(RetryableToolError, match="Invalid date format"):
                validate_date_format(invalid_date)

    def test_past_date_single_digit(self):
        """Test that past dates with single digits are handled correctly."""
        # This date format is actually valid in Python but may be in the past
        with pytest.raises(RetryableToolError, match="Date cannot be in the past"):
            validate_date_format("2024-1-1", allow_past=False)


class TestValidateTimeFormat:
    """Test cases for validate_time_format function."""

    def test_valid_times(self):
        """Test that valid time formats pass validation."""
        valid_times = [
            "00:00",
            "12:00",
            "23:59",
            "09:30",
            "18:45",
        ]

        for valid_time in valid_times:
            # Should not raise any exception
            validate_time_format(valid_time)

    def test_invalid_time_formats(self):
        """Test that invalid time formats raise error."""
        invalid_times = [
            "24:00",  # Hour 24 not valid
            "12:60",  # Minute 60 not valid
            "12:30:45",  # Seconds included
            "12-30",  # Wrong separator
            "not-time",  # Completely invalid
            "25:30",  # Hour > 23
            "12:99",  # Invalid minute
            "-1:30",  # Negative hour
            "12:-5",  # Negative minute
        ]

        for invalid_time in invalid_times:
            with pytest.raises(RetryableToolError, match="Invalid .* format"):
                validate_time_format(invalid_time)

    def test_single_digit_times_valid(self):
        """Test that single digit times are actually valid in Python datetime parsing."""
        # These are actually valid in Python's datetime parsing
        valid_single_digit_times = ["9:30", "12:5"]

        for valid_time in valid_single_digit_times:
            # Should not raise any exception
            validate_time_format(valid_time)

    def test_custom_param_name(self):
        """Test that custom parameter names appear in error messages."""
        with pytest.raises(RetryableToolError, match="Invalid earliest_time format"):
            validate_time_format("25:00", param_name="earliest_time")


class TestValidateTimeRange:
    """Test cases for validate_time_range function."""

    def test_valid_time_range(self):
        """Test that valid time ranges pass validation."""
        valid_ranges = [
            ("09:00", "18:00"),
            ("00:00", "23:59"),
            ("12:00", "12:01"),
        ]

        for earliest, latest in valid_ranges:
            # Should not raise any exception
            validate_time_range(earliest, latest)

    def test_invalid_time_range(self):
        """Test that invalid time ranges raise error."""
        invalid_ranges = [
            ("18:00", "09:00"),  # Earlier time after later time
            ("12:00", "12:00"),  # Same time
            ("23:59", "00:00"),  # Later time before earlier time
        ]

        for earliest, latest in invalid_ranges:
            with pytest.raises(
                RetryableToolError, match="Earliest time must be before latest time"
            ):
                validate_time_range(earliest, latest)

    def test_invalid_time_format_in_range(self):
        """Test that invalid time formats in range validation raise error."""
        with pytest.raises(RetryableToolError, match="Invalid time format"):
            validate_time_range("25:00", "18:00")


class TestValidatePartySize:
    """Test cases for validate_party_size function."""

    def test_valid_party_sizes(self):
        """Test that valid party sizes pass validation."""
        valid_sizes = [1, 2, 5, 10, 20]

        for size in valid_sizes:
            # Should not raise any exception
            validate_party_size(size)

    def test_invalid_party_sizes(self):
        """Test that invalid party sizes raise error."""
        invalid_sizes = [0, -1, 21, 100]

        for size in invalid_sizes:
            with pytest.raises(RetryableToolError, match="Party size must be between"):
                validate_party_size(size)

    def test_custom_size_limits(self):
        """Test that custom size limits work correctly."""
        # Should pass with custom limits
        validate_party_size(25, min_size=1, max_size=30)

        # Should fail with custom limits
        with pytest.raises(RetryableToolError, match="Party size must be between 5 and 15"):
            validate_party_size(20, min_size=5, max_size=15)


class TestValidateEmailFormat:
    """Test cases for validate_email_format function."""

    def test_valid_emails(self):
        """Test that valid email formats pass validation."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.org",
            "user+tag@example.co.uk",
            "first.last@sub.domain.com",
            "user123@example123.com",
        ]

        for email in valid_emails:
            # Should not raise any exception
            validate_email_format(email)

    def test_invalid_emails(self):
        """Test that invalid email formats raise error."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user space@domain.com",
            "user@domain@com",
            "",
        ]

        for email in invalid_emails:
            with pytest.raises(RetryableToolError, match="Invalid email address format"):
                validate_email_format(email)


class TestValidatePhoneFormat:
    """Test cases for validate_phone_format function."""

    def test_valid_phones(self):
        """Test that valid phone formats pass validation."""
        valid_phones = [
            "555-123-4567",
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567",
            "+15551234567",
            "1234567",  # Minimum length
        ]

        for phone in valid_phones:
            # Should not raise any exception
            validate_phone_format(phone)

    def test_invalid_phones(self):
        """Test that invalid phone formats raise error."""
        invalid_phones = [
            "123abc4567",  # Contains letters
            "555-123",  # Too short
            "1234567890123456",  # Too long
            "",  # Empty
            "555-123-456a",  # Contains letter at end
        ]

        for phone in invalid_phones:
            with pytest.raises(RetryableToolError, match="Phone"):
                validate_phone_format(phone)


class TestValidateLimitParameter:
    """Test cases for validate_limit_parameter function."""

    def test_valid_limits(self):
        """Test that valid limit values pass validation."""
        valid_limits = [1, 50, 100]

        for limit in valid_limits:
            # Should not raise any exception
            validate_limit_parameter(limit)

    def test_invalid_limits(self):
        """Test that invalid limit values raise error."""
        invalid_limits = [0, -1, 101, 1000]

        for limit in invalid_limits:
            with pytest.raises(RetryableToolError, match="Limit must be between"):
                validate_limit_parameter(limit)

    def test_custom_limit_range(self):
        """Test that custom limit ranges work correctly."""
        # Should pass with custom range
        validate_limit_parameter(25, min_limit=10, max_limit=50)

        # Should fail with custom range
        with pytest.raises(RetryableToolError, match="Limit must be between 5 and 20"):
            validate_limit_parameter(30, min_limit=5, max_limit=20)


class TestValidateCoordinates:
    """Test cases for validate_coordinates function."""

    def test_valid_coordinates(self):
        """Test that valid coordinate pairs pass validation."""
        valid_coords = [
            (0.0, 0.0),
            (40.7128, -74.0060),  # NYC
            (-33.8688, 151.2093),  # Sydney
            (90.0, 180.0),  # Extremes
            (-90.0, -180.0),  # Extremes
        ]

        for lat, lng in valid_coords:
            # Should not raise any exception
            validate_coordinates(lat, lng)

    def test_both_none_coordinates(self):
        """Test that both None coordinates pass validation."""
        # Should not raise any exception
        validate_coordinates(None, None)

    def test_invalid_coordinate_ranges(self):
        """Test that coordinates outside valid ranges raise error."""
        invalid_coords = [
            (91.0, 0.0),  # Latitude > 90
            (-91.0, 0.0),  # Latitude < -90
            (0.0, 181.0),  # Longitude > 180
            (0.0, -181.0),  # Longitude < -180
        ]

        for lat, lng in invalid_coords:
            with pytest.raises(RetryableToolError, match="must be between"):
                validate_coordinates(lat, lng)

    def test_partial_coordinates(self):
        """Test that providing only one coordinate raises error."""
        with pytest.raises(
            RetryableToolError, match="Both latitude and longitude must be provided"
        ):
            validate_coordinates(40.7128, None)

        with pytest.raises(
            RetryableToolError, match="Both latitude and longitude must be provided"
        ):
            validate_coordinates(None, -74.0060)


class TestValidateNonEmptyString:
    """Test cases for validate_non_empty_string function."""

    def test_valid_strings(self):
        """Test that valid non-empty strings pass validation."""
        valid_strings = [
            "valid string",
            "a",
            "123",
            "special@chars!",
        ]

        for string in valid_strings:
            # Should not raise any exception
            validate_non_empty_string(string, "test_param")

    def test_invalid_strings(self):
        """Test that empty or whitespace strings raise error."""
        invalid_strings = [
            "",
            "   ",
            "\t",
            "\n",
            "  \t  \n  ",
        ]

        for string in invalid_strings:
            with pytest.raises(RetryableToolError, match="test_param cannot be empty"):
                validate_non_empty_string(string, "test_param")

    def test_custom_param_name_in_error(self):
        """Test that custom parameter names appear in error messages."""
        with pytest.raises(RetryableToolError, match="restaurant_name cannot be empty"):
            validate_non_empty_string("", "restaurant_name")

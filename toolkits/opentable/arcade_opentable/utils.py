"""Utility functions for OpenTable toolkit validation and processing."""

import re
from datetime import datetime
from typing import Optional

from arcade_tdk.errors import RetryableToolError


def validate_date_format(date_str: str, allow_past: bool = False) -> None:
    """
    Validate date string is in YYYY-MM-DD format and optionally check if it's not in the past.

    Args:
        date_str: Date string to validate
        allow_past: Whether to allow past dates (default: False)

    Raises:
        RetryableToolError: If date format is invalid or date is in the past when not allowed
    """
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")

        if not allow_past and parsed_date.date() < datetime.now().date():
            raise RetryableToolError(
                message="Date cannot be in the past.",
                developer_message=f"Past date provided: {date_str}",
                retry_after_ms=100,
                additional_prompt_content="Provide a current or future date in YYYY-MM-DD format",
            )

    except ValueError as e:
        raise RetryableToolError(
            message="Invalid date format. Please use YYYY-MM-DD format.",
            developer_message=f"Date parsing failed for '{date_str}': {e}",
            retry_after_ms=100,
            additional_prompt_content="Use YYYY-MM-DD format for the date (e.g., 2024-12-31)",
        ) from e


def validate_time_format(time_str: str, param_name: str = "time") -> None:
    """
    Validate time format is HH:MM (24-hour).

    Args:
        time_str: Time string to validate
        param_name: Name of the parameter for error messages

    Raises:
        RetryableToolError: If time format is invalid
    """

    def _raise_validation_error(message: str, additional_content: str) -> None:
        """Helper function to raise validation errors."""
        raise RetryableToolError(
            message=f"Invalid {param_name} format. Please use HH:MM format (24-hour).",
            developer_message=f"Time parsing failed for {param_name} '{time_str}': {message}",
            retry_after_ms=100,
            additional_prompt_content=additional_content,
        )

    try:
        # Parse the time string
        parsed_time = datetime.strptime(time_str, "%H:%M")

        # Additional validation to ensure it's within valid 24-hour range
        hour = parsed_time.hour
        minute = parsed_time.minute

        if hour < 0 or hour > 23:
            _raise_validation_error(
                f"Hour must be between 00 and 23, got {hour:02d}",
                f"Use HH:MM format for {param_name} (24-hour format, e.g., 18:30 for 6:30 PM)",
            )
        if minute < 0 or minute > 59:
            _raise_validation_error(
                f"Minute must be between 00 and 59, got {minute:02d}",
                f"Use HH:MM format for {param_name} (24-hour format, e.g., 18:30 for 6:30 PM)",
            )

    except ValueError as e:
        _raise_validation_error(
            str(e), f"Use HH:MM format for {param_name} (24-hour format, e.g., 18:30 for 6:30 PM)"
        )


def validate_time_range(earliest_time: str, latest_time: str) -> None:
    """
    Validate that earliest_time is before latest_time.

    Args:
        earliest_time: Earliest time in HH:MM format
        latest_time: Latest time in HH:MM format

    Raises:
        RetryableToolError: If earliest time is not before latest time
    """
    try:
        earliest_dt = datetime.strptime(earliest_time, "%H:%M")
        latest_dt = datetime.strptime(latest_time, "%H:%M")

        if earliest_dt >= latest_dt:
            raise RetryableToolError(
                message="Earliest time must be before latest time.",
                developer_message=f"Invalid time range: {earliest_time} to {latest_time}",
                retry_after_ms=100,
                additional_prompt_content="Ensure earliest_time is before latest_time",
            )

    except ValueError as e:
        raise RetryableToolError(
            message="Invalid time format in time range validation.",
            developer_message=f"Time parsing failed during range validation: {e}",
            retry_after_ms=100,
            additional_prompt_content="Use HH:MM format for both earliest_time and latest_time",
        ) from e


def validate_party_size(party_size: int, min_size: int = 1, max_size: int = 20) -> None:
    """
    Validate party size is within acceptable range.

    Args:
        party_size: Number of people in the party
        min_size: Minimum allowed party size (default: 1)
        max_size: Maximum allowed party size (default: 20)

    Raises:
        RetryableToolError: If party size is outside valid range
    """
    if party_size < min_size or party_size > max_size:
        raise RetryableToolError(
            message=f"Party size must be between {min_size} and {max_size} people.",
            developer_message=f"Invalid party size: {party_size} (range: {min_size}-{max_size})",
            retry_after_ms=100,
            additional_prompt_content=f"Provide a party size between {min_size} and {max_size}",
        )


def validate_email_format(email: str) -> None:
    """
    Validate email address format using basic regex pattern.

    Args:
        email: Email address to validate

    Raises:
        RetryableToolError: If email format is invalid
    """
    # Basic email regex pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, email):
        raise RetryableToolError(
            message="Invalid email address format.",
            developer_message=f"Email validation failed for: {email}",
            retry_after_ms=100,
            additional_prompt_content="Provide a valid email address (e.g., user@example.com)",
        )


def validate_phone_format(phone: str) -> None:
    """
    Validate phone number format (basic validation for common formats).

    Args:
        phone: Phone number to validate

    Raises:
        RetryableToolError: If phone format appears invalid
    """
    # Remove common separators and spaces
    cleaned_phone = re.sub(r"[\s\-\(\)\+\.]", "", phone)

    # Check if it contains only digits (after cleaning)
    if not cleaned_phone.isdigit():
        raise RetryableToolError(
            message="Phone number should contain only digits and common separators.",
            developer_message=f"Phone validation failed for: {phone}",
            retry_after_ms=100,
            additional_prompt_content="Provide a valid phone number (e.g., +1-555-123-4567 or 555-123-4567)",
        )

    # Check length (should be reasonable range for international numbers)
    if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
        raise RetryableToolError(
            message="Phone number length should be between 7 and 15 digits.",
            developer_message=f"Phone validation failed for: {phone} (cleaned: {cleaned_phone}, length: {len(cleaned_phone)})",
            retry_after_ms=100,
            additional_prompt_content="Provide a phone number with 7-15 digits",
        )


def validate_limit_parameter(limit: int, min_limit: int = 1, max_limit: int = 100) -> None:
    """
    Validate limit parameter is within acceptable range.

    Args:
        limit: Limit value to validate
        min_limit: Minimum allowed limit (default: 1)
        max_limit: Maximum allowed limit (default: 100)

    Raises:
        RetryableToolError: If limit is outside valid range
    """
    if limit < min_limit or limit > max_limit:
        raise RetryableToolError(
            message=f"Limit must be between {min_limit} and {max_limit}.",
            developer_message=f"Invalid limit: {limit} (range: {min_limit}-{max_limit})",
            retry_after_ms=100,
            additional_prompt_content=f"Provide a limit between {min_limit} and {max_limit}",
        )


def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> None:
    """
    Validate latitude and longitude coordinates.

    Args:
        latitude: Latitude coordinate (can be None)
        longitude: Longitude coordinate (can be None)

    Raises:
        RetryableToolError: If coordinates are invalid or only one is provided
    """
    # Check if only one coordinate is provided
    if (latitude is None) != (longitude is None):
        raise RetryableToolError(
            message="Both latitude and longitude must be provided together.",
            developer_message="Only one coordinate parameter was provided",
            retry_after_ms=100,
            additional_prompt_content="Provide both latitude and longitude coordinates",
        )

    # If both are provided, validate ranges
    if latitude is not None and longitude is not None:
        if latitude < -90 or latitude > 90:
            raise RetryableToolError(
                message="Latitude must be between -90 and 90 degrees.",
                developer_message=f"Invalid latitude: {latitude}",
                retry_after_ms=100,
                additional_prompt_content="Provide a valid latitude between -90 and 90",
            )

        if longitude < -180 or longitude > 180:
            raise RetryableToolError(
                message="Longitude must be between -180 and 180 degrees.",
                developer_message=f"Invalid longitude: {longitude}",
                retry_after_ms=100,
                additional_prompt_content="Provide a valid longitude between -180 and 180",
            )


def validate_non_empty_string(value: str, param_name: str) -> None:
    """
    Validate that a string parameter is not empty or just whitespace.

    Args:
        value: String value to validate
        param_name: Parameter name for error messages

    Raises:
        RetryableToolError: If string is empty or only whitespace
    """
    if not value or not value.strip():
        raise RetryableToolError(
            message=f"{param_name} cannot be empty.",
            developer_message=f"Empty or whitespace-only value for {param_name}",
            retry_after_ms=100,
            additional_prompt_content=f"Provide a valid {param_name}",
        )

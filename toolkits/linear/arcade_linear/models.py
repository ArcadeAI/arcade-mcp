"""Linear toolkit models and enums"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class DateRange(Enum):
    """Date range enum for Linear datetime queries

    Provides consistent datetime range handling.
    All ranges are calculated in UTC and return timezone-aware datetime objects.
    """

    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"

    def to_datetime_range(
        self, reference_time: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """Convert DateRange to start and end datetime objects

        Args:
            reference_time: Optional reference time for calculations. Defaults to now in UTC.

        Returns:
            Tuple of (start_datetime, end_datetime) - both timezone-aware in UTC
        """
        now = reference_time or datetime.now(timezone.utc)

        # Map enum values to their corresponding helper methods
        range_methods = {
            DateRange.TODAY: self._get_today_range,
            DateRange.YESTERDAY: self._get_yesterday_range,
            DateRange.THIS_WEEK: self._get_this_week_range,
            DateRange.LAST_WEEK: self._get_last_week_range,
            DateRange.THIS_MONTH: self._get_this_month_range,
            DateRange.LAST_MONTH: self._get_last_month_range,
            DateRange.THIS_YEAR: self._get_this_year_range,
            DateRange.LAST_YEAR: self._get_last_year_range,
            DateRange.LAST_7_DAYS: lambda n: self._get_last_n_days_range(n, 7),
            DateRange.LAST_30_DAYS: lambda n: self._get_last_n_days_range(n, 30),
        }

        if self in range_methods:
            return range_methods[self](now)
        else:
            raise ValueError("Invalid DateRange enum value")

    def _get_today_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get today's start and end datetime."""
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    def _get_yesterday_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get yesterday's start and end datetime."""
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    def _get_this_week_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get this week's start and end datetime."""
        # Start of current week (Monday)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        return start, end

    def _get_last_week_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get last week's start and end datetime."""
        # Start of last week (Monday)
        start = now - timedelta(days=now.weekday() + 7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        return start, end

    def _get_this_month_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get this month's start and end datetime."""
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        return start, end

    def _get_last_month_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get last month's start and end datetime."""
        # First day of current month
        first_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Last day of previous month
        end = first_of_current_month - timedelta(microseconds=1)
        # First day of previous month
        start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, end

    def _get_this_year_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get this year's start and end datetime."""
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        return start, end

    def _get_last_year_range(self, now: datetime) -> tuple[datetime, datetime]:
        """Get last year's start and end datetime."""
        last_year = now.year - 1
        start = now.replace(
            year=last_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = now.replace(
            year=last_year,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        return start, end

    def _get_last_n_days_range(self, now: datetime, days: int) -> tuple[datetime, datetime]:
        """Get range for last N days."""
        start = now - timedelta(days=days)
        end = now
        return start, end

    def to_start_datetime(self, reference_time: datetime | None = None) -> datetime:
        """Get just the start datetime for this range

        Args:
            reference_time: Optional reference time for calculations. Defaults to now in UTC.

        Returns:
            Start datetime for this range
        """
        start, _ = self.to_datetime_range(reference_time)
        return start

    def to_end_datetime(self, reference_time: datetime | None = None) -> datetime:
        """Get just the end datetime for this range

        Args:
            reference_time: Optional reference time for calculations. Defaults to now in UTC.

        Returns:
            End datetime for this range
        """
        _, end = self.to_datetime_range(reference_time)
        return end

    def to_iso_strings(self, reference_time: datetime | None = None) -> tuple[str, str]:
        """Get start and end as ISO format strings

        Args:
            reference_time: Optional reference time for calculations. Defaults to now in UTC.

        Returns:
            Tuple of (start_iso, end_iso) strings
        """
        start, end = self.to_datetime_range(reference_time)
        return start.isoformat(), end.isoformat()

    @classmethod
    def from_string(cls, date_str: str) -> Optional["DateRange"]:
        """Create DateRange from string if it matches a known value

        Args:
            date_str: String representation of date range

        Returns:
            DateRange enum or None if no match found
        """
        normalized = date_str.lower().strip()

        # Direct mapping
        value_map = {
            "today": cls.TODAY,
            "yesterday": cls.YESTERDAY,
            "this week": cls.THIS_WEEK,
            "last week": cls.LAST_WEEK,
            "this month": cls.THIS_MONTH,
            "last month": cls.LAST_MONTH,
            "this year": cls.THIS_YEAR,
            "last year": cls.LAST_YEAR,
            "last 7 days": cls.LAST_7_DAYS,
            "last 30 days": cls.LAST_30_DAYS,
        }

        return value_map.get(normalized)

import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.models import DateRange
from arcade_linear.utils import (
    add_pagination_info,
    clean_issue_data,
    clean_team_data,
    parse_date_range,
    parse_date_string,
    remove_none_values,
    validate_date_format,
)


class TestDateParsing:
    """Tests for date parsing utilities"""

    def test_parse_date_string_valid_iso(self):
        """Test date parsing with valid ISO strings"""
        result = parse_date_string("2024-01-01")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo is not None

    def test_parse_date_string_with_time(self):
        """Test date parsing with date and time"""
        result = parse_date_string("2024-01-01T12:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.hour == 12
        assert result.minute == 30

    def test_parse_date_string_relative(self):
        """Test date parsing with relative strings"""
        result = parse_date_string("today")
        assert result is not None

        result = parse_date_string("yesterday")
        assert result is not None

    def test_parse_date_string_time_mappings(self):
        """Test date parsing with DateRange enum expressions"""
        result = parse_date_string("this week")
        assert result is not None

        result = parse_date_string("last month")
        assert result is not None

        result = parse_date_string("yesterday")
        assert result is not None

        result = parse_date_string("last 7 days")
        assert result is not None

    def test_parse_date_string_invalid(self):
        """Test date parsing with invalid strings"""
        result = parse_date_string("invalid-date")
        assert result is None

        result = parse_date_string("not-a-date")
        assert result is None

    def test_parse_date_string_empty(self):
        """Test date parsing with empty string"""
        result = parse_date_string("")
        assert result is None

        result = parse_date_string(None)
        assert result is None

    def test_validate_date_format_valid(self):
        """Test date validation with valid format"""
        # Should not raise exception
        validate_date_format("test_field", "2024-01-01")
        validate_date_format("test_field", "today")
        validate_date_format("test_field", None)
        validate_date_format("test_field", "")

    def test_validate_date_format_invalid(self):
        """Test date validation with invalid format"""
        with pytest.raises(ToolExecutionError) as exc_info:
            validate_date_format("test_field", "invalid-date")

        assert "Invalid date format for test_field" in str(exc_info.value)


class TestDateRange:
    """Tests for DateRange enum"""

    def test_date_range_from_string_valid(self):
        """Test DateRange.from_string with valid strings"""
        assert DateRange.from_string("today") == DateRange.TODAY
        assert DateRange.from_string("yesterday") == DateRange.YESTERDAY
        assert DateRange.from_string("last week") == DateRange.LAST_WEEK
        assert DateRange.from_string("this month") == DateRange.THIS_MONTH
        assert DateRange.from_string("last month") == DateRange.LAST_MONTH
        assert DateRange.from_string("last 7 days") == DateRange.LAST_7_DAYS
        assert DateRange.from_string("last 30 days") == DateRange.LAST_30_DAYS

    def test_date_range_from_string_case_insensitive(self):
        """Test DateRange.from_string is case insensitive"""
        assert DateRange.from_string("TODAY") == DateRange.TODAY
        assert DateRange.from_string("Last Week") == DateRange.LAST_WEEK
        assert DateRange.from_string("THIS MONTH") == DateRange.THIS_MONTH

    def test_date_range_from_string_invalid(self):
        """Test DateRange.from_string with invalid strings"""
        assert DateRange.from_string("invalid") is None
        assert DateRange.from_string("next week") is None
        assert DateRange.from_string("") is None

    def test_date_range_to_datetime_range(self):
        """Test DateRange.to_datetime_range returns proper datetime objects"""
        today_range = DateRange.TODAY.to_datetime_range()
        assert len(today_range) == 2
        start, end = today_range
        assert start.tzinfo is not None
        assert end.tzinfo is not None
        assert start <= end

    def test_date_range_to_start_datetime(self):
        """Test DateRange.to_start_datetime returns proper datetime"""
        start = DateRange.LAST_WEEK.to_start_datetime()
        assert start.tzinfo is not None

    def test_date_range_to_end_datetime(self):
        """Test DateRange.to_end_datetime returns proper datetime"""
        end = DateRange.LAST_MONTH.to_end_datetime()
        assert end.tzinfo is not None


class TestParseDateRange:
    """Tests for parse_date_range function"""

    def test_parse_date_range_valid(self):
        """Test parse_date_range with valid DateRange strings"""
        result = parse_date_range("today")
        assert result is not None
        assert len(result) == 2
        start, end = result
        assert start.tzinfo is not None
        assert end.tzinfo is not None

    def test_parse_date_range_invalid(self):
        """Test parse_date_range with invalid strings"""
        assert parse_date_range("invalid") is None
        assert parse_date_range("") is None
        assert parse_date_range("2024-01-01") is None  # ISO date, not range

    def test_parse_date_range_relative_dates(self):
        """Test parse_date_range with various relative date strings"""
        ranges = ["yesterday", "last week", "this month", "last month", "last 7 days"]
        for range_str in ranges:
            result = parse_date_range(range_str)
            assert result is not None, f"Failed for {range_str}"
            start, end = result
            assert start <= end, f"Invalid range for {range_str}"


class TestDataCleaning:
    """Tests for data cleaning functions"""

    def test_remove_none_values(self):
        """Test removing None values from dictionary"""
        data = {"a": 1, "b": None, "c": "test", "d": None}
        result = remove_none_values(data)
        assert result == {"a": 1, "c": "test"}

    def test_clean_team_data(self):
        """Test team data cleaning"""
        team_data = {
            "id": "team_1",
            "key": "FE",
            "name": "Frontend",
            "description": "Frontend team",
            "private": False,
            "archivedAt": None,
            "createdAt": "2024-01-01T00:00:00Z",
            "members": {"nodes": [{"id": "user_1", "name": "John Doe"}]},
        }

        result = clean_team_data(team_data)

        assert result["id"] == "team_1"
        assert result["key"] == "FE"
        assert result["name"] == "Frontend"
        assert len(result["members"]) == 1
        assert result["members"][0]["name"] == "John Doe"

    def test_clean_issue_data(self):
        """Test issue data cleaning"""
        issue_data = {
            "id": "issue_1",
            "identifier": "FE-123",
            "title": "Test issue",
            "description": "Issue description",
            "priority": 2,
            "priorityLabel": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "assignee": {"id": "user_1", "name": "John Doe"},
            "state": {"id": "state_1", "name": "In Progress"},
            "team": {"id": "team_1", "name": "Frontend"},
            "labels": {"nodes": [{"id": "label_1", "name": "bug"}]},
            "children": {"nodes": []},
        }

        result = clean_issue_data(issue_data)

        assert result["id"] == "issue_1"
        assert result["identifier"] == "FE-123"
        assert result["title"] == "Test issue"
        assert result["assignee"]["name"] == "John Doe"
        assert result["state"]["name"] == "In Progress"
        assert result["team"]["name"] == "Frontend"
        assert len(result["labels"]) == 1
        assert result["labels"][0]["name"] == "bug"

    def test_add_pagination_info(self):
        """Test adding pagination information"""
        response = {"data": "test"}
        page_info = {
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": "start123",
            "endCursor": "end456",
        }

        result = add_pagination_info(response, page_info)

        assert result["pagination"]["has_next_page"] is True
        assert result["pagination"]["has_previous_page"] is False
        assert result["pagination"]["start_cursor"] == "start123"
        assert result["pagination"]["end_cursor"] == "end456"

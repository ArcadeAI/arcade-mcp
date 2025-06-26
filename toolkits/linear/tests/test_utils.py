import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.utils import (
    normalize_priority,
    parse_date_string,
    validate_date_format,
    clean_issue_data,
    clean_user_data,
    clean_team_data,
    clean_state_data,
    clean_project_data,
    clean_label_data,
    clean_cycle_data,
    clean_workflow_state_data,
    add_pagination_info,
    remove_none_values,
    build_issue_filter,
    resolve_team_by_name,
    resolve_user_by_email_or_name,
    resolve_workflow_state_by_name,
    resolve_project_by_name,
    resolve_labels_by_names,
    resolve_projects_by_name,
)


class TestPriorityNormalization:
    """Tests for priority normalization"""

    def test_normalize_priority_valid_string(self):
        """Test priority normalization with valid strings"""
        assert normalize_priority("urgent") == 1
        assert normalize_priority("high") == 2
        assert normalize_priority("medium") == 3
        assert normalize_priority("low") == 4
        assert normalize_priority("none") == 0
        assert normalize_priority("no priority") == 0

    def test_normalize_priority_case_insensitive(self):
        """Test priority normalization is case insensitive"""
        assert normalize_priority("URGENT") == 1
        assert normalize_priority("High") == 2
        assert normalize_priority("MEDIUM") == 3
        assert normalize_priority("Low") == 4

    def test_normalize_priority_valid_int(self):
        """Test priority normalization with valid integers"""
        assert normalize_priority(0) == 0
        assert normalize_priority(1) == 1
        assert normalize_priority(2) == 2
        assert normalize_priority(3) == 3
        assert normalize_priority(4) == 4

    def test_normalize_priority_invalid_string(self):
        """Test priority normalization with invalid strings"""
        with pytest.raises(ToolExecutionError) as exc_info:
            normalize_priority("invalid")
        assert "Invalid priority: 'invalid'" in str(exc_info.value)

    def test_normalize_priority_invalid_int(self):
        """Test priority normalization with invalid integers"""
        with pytest.raises(ToolExecutionError):
            normalize_priority(10)
        with pytest.raises(ToolExecutionError):
            normalize_priority(-1)

    def test_normalize_priority_none(self):
        """Test priority normalization with None"""
        assert normalize_priority(None) is None


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
        """Test date parsing with mapped time expressions"""
        result = parse_date_string("this week")
        assert result is not None
        
        result = parse_date_string("last month")
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


class TestDataCleaning:
    """Tests for data cleaning functions"""

    def test_remove_none_values(self):
        """Test removing None values from dictionary"""
        data = {"a": 1, "b": None, "c": "test", "d": None}
        result = remove_none_values(data)
        assert result == {"a": 1, "c": "test"}

    def test_clean_user_data(self):
        """Test user data cleaning"""
        user_data = {
            "id": "user_1",
            "name": "John Doe",
            "email": "john@company.com",
            "displayName": "John Doe",
            "avatarUrl": "https://avatar.url",
            "extra_field": "should_be_ignored"
        }
        
        result = clean_user_data(user_data)
        
        assert result["id"] == "user_1"
        assert result["name"] == "John Doe"
        assert result["email"] == "john@company.com"
        assert result["display_name"] == "John Doe"
        assert result["avatar_url"] == "https://avatar.url"
        assert "extra_field" not in result

    def test_clean_user_data_empty(self):
        """Test user data cleaning with empty data"""
        result = clean_user_data({})
        assert result == {}
        
        result = clean_user_data(None)
        assert result == {}

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
            "members": {
                "nodes": [
                    {"id": "user_1", "name": "John Doe"}
                ]
            }
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

    def test_clean_state_data(self):
        """Test workflow state data cleaning"""
        state_data = {
            "id": "state_1",
            "name": "In Progress",
            "type": "started",
            "color": "#f2c94c",
            "position": 2
        }
        
        result = clean_state_data(state_data)
        
        assert result["id"] == "state_1"
        assert result["name"] == "In Progress"
        assert result["type"] == "started"
        assert result["color"] == "#f2c94c"
        assert result["position"] == 2

    def test_clean_project_data(self):
        """Test project data cleaning"""
        project_data = {
            "id": "project_1",
            "name": "Q1 Initiative",
            "description": "Major project",
            "state": "started",
            "progress": 0.6,
            "startDate": "2024-01-01",
            "targetDate": "2024-03-31",
            "url": "https://project.url"
        }
        
        result = clean_project_data(project_data)
        
        assert result["id"] == "project_1"
        assert result["name"] == "Q1 Initiative"
        assert result["state"] == "started"
        assert result["progress"] == 0.6
        assert result["start_date"] == "2024-01-01"
        assert result["target_date"] == "2024-03-31"

    def test_clean_cycle_data(self):
        """Test cycle data cleaning"""
        cycle_data = {
            "id": "cycle_1",
            "number": 1,
            "name": "Sprint 1",
            "description": "First sprint",
            "startsAt": "2024-01-01T00:00:00Z",
            "endsAt": "2024-01-14T23:59:59Z",
            "progress": 0.5,
            "team": {"id": "team_1", "name": "Frontend"},
            "issues": {"nodes": []}
        }
        
        result = clean_cycle_data(cycle_data)
        
        assert result["id"] == "cycle_1"
        assert result["number"] == 1
        assert result["name"] == "Sprint 1"
        assert result["starts_at"] == "2024-01-01T00:00:00Z"
        assert result["ends_at"] == "2024-01-14T23:59:59Z"
        assert result["progress"] == 0.5
        assert result["team"]["name"] == "Frontend"

    def test_clean_workflow_state_data(self):
        """Test workflow state data cleaning"""
        state_data = {
            "id": "state_1",
            "name": "To Do",
            "description": "Work to be done",
            "type": "unstarted",
            "color": "#e2e2e2",
            "position": 1,
            "team": {"id": "team_1", "name": "Frontend"}
        }
        
        result = clean_workflow_state_data(state_data)
        
        assert result["id"] == "state_1"
        assert result["name"] == "To Do"
        assert result["description"] == "Work to be done"
        assert result["type"] == "unstarted"
        assert result["team"]["name"] == "Frontend"

    def test_add_pagination_info(self):
        """Test adding pagination information"""
        response = {"data": "test"}
        page_info = {
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": "start123",
            "endCursor": "end456"
        }
        
        result = add_pagination_info(response, page_info)
        
        assert result["pagination"]["has_next_page"] is True
        assert result["pagination"]["has_previous_page"] is False
        assert result["pagination"]["start_cursor"] == "start123"
        assert result["pagination"]["end_cursor"] == "end456"


class TestIssueFilter:
    """Tests for issue filter building"""

    def test_build_issue_filter_basic(self):
        """Test basic issue filter building"""
        result = build_issue_filter(
            team_id="team_1",
            assignee_id="user_1",
            priority=2
        )
        
        assert result["team"]["id"]["eq"] == "team_1"
        assert result["assignee"]["id"]["eq"] == "user_1"
        assert result["priority"]["eq"] == 2

    def test_build_issue_filter_dates(self):
        """Test issue filter with date ranges"""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = build_issue_filter(
            created_at_gte=start_date,
            created_at_lte=end_date,
            updated_at_gte=start_date
        )
        
        assert result["createdAt"]["gte"] == "2024-01-01T00:00:00+00:00"
        assert result["createdAt"]["lte"] == "2024-01-31T00:00:00+00:00"
        assert result["updatedAt"]["gte"] == "2024-01-01T00:00:00+00:00"

    def test_build_issue_filter_labels(self):
        """Test issue filter with label IDs"""
        result = build_issue_filter(label_ids=["label_1", "label_2"])
        
        # Multiple labels should use AND logic (in 'and' condition)
        assert "and" in result
        label_conditions = result["and"]
        assert len(label_conditions) == 2
        assert {"labels": {"some": {"id": {"eq": "label_1"}}}} in label_conditions
        assert {"labels": {"some": {"id": {"eq": "label_2"}}}} in label_conditions

    def test_build_issue_filter_search(self):
        """Test issue filter with search query"""
        result = build_issue_filter(search_query="authentication bug")
        
        # Should use OR structure with enhanced keyword-based search
        assert "or" in result
        
        # With multiple keywords, should create conditions for:
        # 1. Multiple keywords in title (2 combinations: auth+bug)
        # 2. One keyword in title, one in description (4 combinations)  
        # 3. Individual keyword matches in all fields (6 conditions total)
        # Total: 1 + 4 + 6 = 11 conditions minimum
        
        or_conditions = result["or"]
        assert len(or_conditions) >= 9  # Should have many conditions for flexible search
        
        # Should include multi-keyword conditions for title
        expected_multi_title = {
            "and": [
                {"title": {"containsIgnoreCase": "authentication"}},
                {"title": {"containsIgnoreCase": "bug"}}
            ]
        }
        assert expected_multi_title in or_conditions
        
        # Should include individual keyword conditions
        expected_individual_conditions = [
            {"title": {"containsIgnoreCase": "authentication"}},
            {"title": {"containsIgnoreCase": "bug"}},
            {"description": {"containsIgnoreCase": "authentication"}},
            {"description": {"containsIgnoreCase": "bug"}},
            {"labels": {"some": {"name": {"containsIgnoreCase": "authentication"}}}},
            {"labels": {"some": {"name": {"containsIgnoreCase": "bug"}}}}
        ]
        
        for condition in expected_individual_conditions:
            assert condition in or_conditions
        
        # Should NOT use the old searchableContent field
        assert "searchableContent" not in result

    def test_build_issue_filter_empty(self):
        """Test issue filter with no parameters"""
        result = build_issue_filter()
        
        assert result == {}

    def test_build_issue_filter_enhanced_search_examples(self):
        """Test issue filter with real-world search examples that should work better"""
        # Test case 1: "Dark Mode Support" should match issues containing "dark" and "mode"
        result1 = build_issue_filter(search_query="Dark Mode Support")
        
        # Should have OR conditions
        assert "or" in result1
        or_conditions1 = result1["or"]
        
        # Should include individual keyword conditions that would match "Feature request: Add dark mode"
        expected_dark_conditions = [
            {"title": {"containsIgnoreCase": "Dark"}},
            {"title": {"containsIgnoreCase": "Mode"}},
            {"description": {"containsIgnoreCase": "Dark"}},
            {"description": {"containsIgnoreCase": "Mode"}},
        ]
        
        # Check that individual keyword conditions are present
        for condition in expected_dark_conditions:
            assert condition in or_conditions1, f"Missing condition: {condition}"
        
        # Should also include multi-keyword condition for title
        expected_multi_dark = {
            "and": [
                {"title": {"containsIgnoreCase": "Dark"}},
                {"title": {"containsIgnoreCase": "Mode"}}
            ]
        }
        assert expected_multi_dark in or_conditions1
        
        # Test case 2: "Improved Checkout Flow" should match issues containing "checkout"
        result2 = build_issue_filter(search_query="Improved Checkout Flow")
        
        # Should have OR conditions
        assert "or" in result2
        or_conditions2 = result2["or"]
        
        # Should include checkout condition that would match "Critical bug in checkout process"
        expected_checkout_conditions = [
            {"title": {"containsIgnoreCase": "Checkout"}},
            {"description": {"containsIgnoreCase": "Checkout"}},
        ]
        
        for condition in expected_checkout_conditions:
            assert condition in or_conditions2, f"Missing condition: {condition}"
        
        # Test case 3: Single word search still works
        result3 = build_issue_filter(search_query="authentication")
        
        assert "or" in result3
        or_conditions3 = result3["or"]
        assert len(or_conditions3) == 3  # Should have exactly 3 conditions for single word
        
        expected_single_conditions = [
            {"title": {"containsIgnoreCase": "authentication"}},
            {"description": {"containsIgnoreCase": "authentication"}},
            {"labels": {"some": {"name": {"containsIgnoreCase": "authentication"}}}}
        ]
        
        for condition in expected_single_conditions:
            assert condition in or_conditions3


class TestResolutionFunctions:
    """Tests for name resolution functions"""

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_team_by_name_exact_match(self, mock_client_class):
        """Test team name resolution with exact match"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_teams.return_value = {
            "nodes": [
                {"id": "team_1", "name": "Frontend"},
                {"id": "team_2", "name": "Frontend-Mobile"}
            ]
        }
        
        result = await resolve_team_by_name(mock_context, "Frontend")
        
        assert result["id"] == "team_1"
        assert result["name"] == "Frontend"

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_team_by_name_not_found(self, mock_client_class):
        """Test team name resolution when not found"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_teams.return_value = {"nodes": []}
        
        result = await resolve_team_by_name(mock_context, "NonExistent")
        
        assert result is None

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_team_by_name_multiple_exact(self, mock_client_class):
        """Test team name resolution with multiple exact matches"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_teams.return_value = {
            "nodes": [
                {"id": "team_1", "name": "Frontend"},
                {"id": "team_2", "name": "Frontend"}  # Duplicate name
            ]
        }
        
        with pytest.raises(ToolExecutionError) as exc_info:
            await resolve_team_by_name(mock_context, "Frontend")
        
        assert "Multiple teams found with name 'Frontend'" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_user_by_email_or_name_email(self, mock_client_class):
        """Test user resolution by email"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_query.return_value = {
            "data": {
                "users": {
                    "nodes": [
                        {"id": "user_1", "name": "John Doe", "email": "john@company.com"}
                    ]
                }
            }
        }
        
        result = await resolve_user_by_email_or_name(mock_context, "john@company.com")
        
        assert result["id"] == "user_1"
        assert result["email"] == "john@company.com"

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_labels_by_names_success(self, mock_client_class):
        """Test label name resolution"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_query.return_value = {
            "data": {
                "issueLabels": {
                    "nodes": [
                        {"id": "label_1", "name": "bug", "color": "#ff0000"}
                    ]
                }
            }
        }
        
        result = await resolve_labels_by_names(mock_context, ["bug"])
        
        assert len(result) == 1
        assert result[0]["id"] == "label_1"
        assert result[0]["name"] == "bug"

    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_labels_by_names_not_found(self, mock_client_class):
        """Test label name resolution when label not found"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_query.return_value = {
            "data": {
                "issueLabels": {
                    "nodes": []
                }
            }
        }
        
        with pytest.raises(ToolExecutionError) as exc_info:
            await resolve_labels_by_names(mock_context, ["nonexistent"])
        
        assert "Label 'nonexistent' not found" in str(exc_info.value)


class TestProjectNameVariations:
    """Test project name resolution with different variations"""
    
    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_projects_space_to_hyphen_variation(self, mock_client_class):
        """Test that 'arcade testing' finds 'arcade-testing' project"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock projects response with hyphenated name
        mock_client.get_projects.return_value = {
            "nodes": [
                {"id": "proj_1", "name": "arcade-testing", "description": "Test project"},
                {"id": "proj_2", "name": "other-project", "description": "Other project"}
            ]
        }
        
        # Search for space-separated name
        result = await resolve_projects_by_name(mock_context, "arcade testing")
        
        # Should find the hyphenated project
        assert len(result) == 1
        assert result[0]["id"] == "proj_1"
        assert result[0]["name"] == "arcade-testing"
    
    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_projects_hyphen_to_space_variation(self, mock_client_class):
        """Test that 'arcade-testing' finds 'arcade testing' project"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock projects response with space-separated name
        mock_client.get_projects.return_value = {
            "nodes": [
                {"id": "proj_1", "name": "arcade testing", "description": "Test project"},
                {"id": "proj_2", "name": "other project", "description": "Other project"}
            ]
        }
        
        # Search for hyphenated name
        result = await resolve_projects_by_name(mock_context, "arcade-testing")
        
        # Should find the space-separated project
        assert len(result) == 1
        assert result[0]["id"] == "proj_1"
        assert result[0]["name"] == "arcade testing"
    
    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_projects_underscore_variation(self, mock_client_class):
        """Test that 'arcade testing' finds 'arcade_testing' project"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock projects response with underscore name
        mock_client.get_projects.return_value = {
            "nodes": [
                {"id": "proj_1", "name": "arcade_testing", "description": "Test project"}
            ]
        }
        
        # Search for space-separated name
        result = await resolve_projects_by_name(mock_context, "arcade testing")
        
        # Should find the underscore project
        assert len(result) == 1
        assert result[0]["id"] == "proj_1"
        assert result[0]["name"] == "arcade_testing"
    
    @pytest.mark.asyncio
    @patch("arcade_linear.utils.LinearClient")
    async def test_resolve_projects_no_match_returns_empty(self, mock_client_class):
        """Test that searching for non-existent project returns empty list"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock projects response with different projects
        mock_client.get_projects.return_value = {
            "nodes": [
                {"id": "proj_1", "name": "different-project", "description": "Different project"},
                {"id": "proj_2", "name": "another-one", "description": "Another project"}
            ]
        }
        
        # Search for non-existent project
        result = await resolve_projects_by_name(mock_context, "arcade testing")
        
        # Should return empty list
        assert len(result) == 0 
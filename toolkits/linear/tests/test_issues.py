from unittest.mock import AsyncMock, patch

import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.tools.issues import (
    add_comment_to_issue,
    create_issue,
    get_issue,
    get_templates,
    search_issues,
    update_issue,
)


@pytest.fixture
def mock_context():
    """Fixture for mocked ToolContext"""
    context = AsyncMock()
    context.get_auth_token_or_empty.return_value = "test_token"
    return context


class TestSearchIssues:
    """Tests for search_issues tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_success(self, mock_client_class, mock_context):
        """Test successful issue search"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issues.return_value = {
            "nodes": [
                {
                    "id": "issue_1",
                    "identifier": "FE-123",
                    "title": "Fix authentication bug",
                    "description": "Authentication not working",
                    "priority": 1,
                    "priorityLabel": "Urgent",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
                    "assignee": {"id": "user_1", "name": "John Doe"},
                    "state": {"id": "state_1", "name": "In Progress"},
                    "labels": {"nodes": []},
                    "children": {"nodes": []},
                    "relations": {"nodes": []},
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await search_issues(
            mock_context,
            keywords="authentication",
            priority="urgent",
            assignee="me",
        )

        # Assertions
        assert result["total_count"] == 1
        assert len(result["issues"]) == 1
        assert result["issues"][0]["title"] == "Fix authentication bug"
        assert result["issues"][0]["identifier"] == "FE-123"
        assert result["search_criteria"]["keywords"] == "authentication"
        assert result["search_criteria"]["priority"] == "urgent"
        mock_client.get_issues.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.resolve_team_by_name")
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_team_resolution(
        self, mock_client_class, mock_resolve_team, mock_context
    ):
        """Test issue search with team name resolution"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}
        mock_client.get_issues.return_value = {"nodes": [], "pageInfo": {"hasNextPage": False}}

        # Call function
        await search_issues(mock_context, team="Frontend")

        # Assertions
        mock_resolve_team.assert_called_once_with(mock_context, "Frontend")
        mock_client.get_issues.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_issues_invalid_priority(self, mock_context):
        """Test issue search with invalid priority"""
        with pytest.raises(ToolExecutionError) as exc_info:
            await search_issues(mock_context, priority="invalid")

        assert "Invalid priority" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.resolve_labels_read_only")
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_labels(
        self, mock_client_class, mock_resolve_labels, mock_context
    ):
        """Test issue search with label filtering"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_resolve_labels.return_value = [
            {"id": "label_1", "name": "bug"},
            {"id": "label_2", "name": "urgent"},
        ]
        mock_client.get_issues.return_value = {"nodes": [], "pageInfo": {"hasNextPage": False}}

        # Call function
        await search_issues(mock_context, labels=["bug", "urgent"])

        # Assertions
        mock_resolve_labels.assert_called_once_with(mock_context, ["bug", "urgent"], None)
        mock_client.get_issues.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_relative_date_range(
        self, mock_client_class, mock_context, build_issue_dict
    ):
        """Test searching issues with relative date ranges like 'last week'"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issues.return_value = {
            "nodes": [build_issue_dict()],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function with relative date
        result = await search_issues(mock_context, updated_after="last week")

        # Assertions
        assert len(result["issues"]) == 1
        assert result["search_criteria"]["updated_after"] == "last week"

        # Verify the client was called with a proper date filter
        mock_client.get_issues.assert_called_once()
        call_args = mock_client.get_issues.call_args
        filter_conditions = call_args.kwargs.get("filter_conditions")

        # Should have updatedAt filter with both gte (start) set
        assert "updatedAt" in filter_conditions
        assert "gte" in filter_conditions["updatedAt"]
        # Should NOT have "lte" (end) since we want "up to now"
        assert "lte" not in filter_conditions["updatedAt"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_multiple_labels_and_logic(
        self, mock_client_class, mock_context, build_issue_dict
    ):
        """Test that multiple labels use AND logic (issues must have ALL labels)"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issues.return_value = {
            "nodes": [build_issue_dict()],
            "pageInfo": {"hasNextPage": False},
        }

        # Mock label resolution - return 2 different label IDs
        with patch("arcade_linear.tools.issues.resolve_labels_read_only") as mock_resolve_labels:
            mock_resolve_labels.return_value = [
                {"id": "label_bug", "name": "bug"},
                {"id": "label_critical", "name": "critical"},
            ]

            # Call function with multiple labels
            result = await search_issues(mock_context, labels=["bug", "critical"])

            # Assertions
            assert len(result["issues"]) == 1
            mock_resolve_labels.assert_called_once_with(mock_context, ["bug", "critical"], None)

            # Verify the filter uses AND logic for multiple labels
            mock_client.get_issues.assert_called_once()
            call_args = mock_client.get_issues.call_args
            filter_conditions = call_args.kwargs.get("filter_conditions")

            # Should have 'and' condition with separate label filters
            assert "and" in filter_conditions
            assert len(filter_conditions["and"]) == 2

            # Each condition should require a specific label
            label_conditions = filter_conditions["and"]
            assert {"labels": {"some": {"id": {"eq": "label_bug"}}}} in label_conditions
            assert {"labels": {"some": {"id": {"eq": "label_critical"}}}} in label_conditions

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_single_label(
        self, mock_client_class, mock_context, build_issue_dict
    ):
        """Test that single label filtering still works with simple logic"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issues.return_value = {
            "nodes": [build_issue_dict()],
            "pageInfo": {"hasNextPage": False},
        }

        # Mock label resolution - return 1 label ID
        with patch("arcade_linear.tools.issues.resolve_labels_read_only") as mock_resolve_labels:
            mock_resolve_labels.return_value = [{"id": "label_bug", "name": "bug"}]

            # Call function with single label
            result = await search_issues(mock_context, labels=["bug"])

            # Assertions
            assert len(result["issues"]) == 1

            # Verify the filter uses simple label filtering for single label
            mock_client.get_issues.assert_called_once()
            call_args = mock_client.get_issues.call_args
            filter_conditions = call_args.kwargs.get("filter_conditions")

            # Should have simple labels filter, not 'and' condition
            assert "labels" in filter_conditions
            assert filter_conditions["labels"] == {"some": {"id": {"eq": "label_bug"}}}
            assert "and" not in filter_conditions

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_search_issues_with_text_includes_label_names(
        self, mock_client_class, mock_context, build_issue_dict
    ):
        """Test that text search now includes label names in addition to titles and descriptions"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issues.return_value = {
            "nodes": [build_issue_dict()],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function with keywords (no explicit labels)
        result = await search_issues(mock_context, keywords="authentication")

        # Assertions
        assert len(result["issues"]) == 1

        # Verify the filter includes comprehensive text search
        mock_client.get_issues.assert_called_once()
        call_args = mock_client.get_issues.call_args
        filter_conditions = call_args.kwargs.get("filter_conditions")

        # Should have 'or' condition for comprehensive text search
        assert "or" in filter_conditions
        or_conditions = filter_conditions["or"]

        # Should search in title, description, and label names
        expected_conditions = [
            {"title": {"containsIgnoreCase": "authentication"}},
            {"description": {"containsIgnoreCase": "authentication"}},
            {"labels": {"some": {"name": {"containsIgnoreCase": "authentication"}}}},
        ]

        for condition in expected_conditions:
            assert condition in or_conditions, f"Missing condition: {condition}"


class TestGetIssue:
    """Tests for get_issue tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_get_issue_success(self, mock_client_class, mock_context):
        """Test successful issue retrieval"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = {
            "id": "issue_1",
            "identifier": "FE-123",
            "title": "Fix authentication bug",
            "description": "Authentication not working",
            "priority": 1,
            "priorityLabel": "Urgent",
            "createdAt": "2024-01-01T00:00:00Z",
            "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
            "assignee": {"id": "user_1", "name": "John Doe"},
            "state": {"id": "state_1", "name": "In Progress"},
            "labels": {"nodes": []},
            "attachments": {"nodes": []},
            "comments": {"nodes": []},
            "children": {"nodes": []},
            "relations": {"nodes": []},
        }

        # Call function
        result = await get_issue(mock_context, "FE-123")

        # Assertions
        assert "issue" in result
        assert result["issue"]["identifier"] == "FE-123"
        assert result["issue"]["title"] == "Fix authentication bug"
        mock_client.get_issue_by_id.assert_called_once_with("FE-123")

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_get_issue_not_found(self, mock_client_class, mock_context):
        """Test issue retrieval when issue not found"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = None

        # Call function
        result = await get_issue(mock_context, "NON-EXISTENT")

        # Assertions
        assert "error" in result
        assert "Issue not found" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_get_issue_selective_includes(self, mock_client_class, mock_context):
        """Test issue retrieval with selective includes"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = {
            "id": "issue_1",
            "identifier": "FE-123",
            "title": "Fix authentication bug",
            "comments": {"nodes": [{"id": "comment_1"}]},
            "attachments": {"nodes": [{"id": "attachment_1"}]},
        }

        # Call function without comments and attachments
        result = await get_issue(
            mock_context,
            "FE-123",
            include_comments=False,
            include_attachments=False,
        )

        # Assertions
        assert "comments" not in result["issue"]
        assert "attachments" not in result["issue"]


class TestUpdateIssue:
    """Tests for update_issue tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_update_issue_success(self, mock_client_class, mock_context):
        """Test successful issue update"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = {
            "id": "issue_1",
            "team": {"id": "team_1"},
        }
        mock_client.update_issue.return_value = {
            "success": True,
            "issue": {
                "id": "issue_1",
                "identifier": "FE-123",
                "title": "Updated title",
                "priority": 2,
            },
        }

        # Call function
        result = await update_issue(
            mock_context,
            "FE-123",
            title="Updated title",
            priority="high",
        )

        # Assertions
        assert result["success"] is True
        assert "Successfully updated issue" in result["message"]
        assert result["issue"]["title"] == "Updated title"
        assert "title" in result["updated_fields"]
        assert "priority" in result["updated_fields"]
        mock_client.update_issue.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_update_issue_not_found(self, mock_client_class, mock_context):
        """Test update when issue not found"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = None

        # Call function
        result = await update_issue(mock_context, "NON-EXISTENT", title="New title")

        # Assertions
        assert "error" in result
        assert "Issue not found" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_update_issue_no_fields(self, mock_client_class, mock_context):
        """Test update with no fields provided"""
        # Setup mock to avoid real API calls
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        # Mock the get_issue_by_id to return valid issue data
        mock_client.get_issue_by_id.return_value = {
            "id": "issue_1",
            "identifier": "FE-123",
            "team": {"id": "team_1"},
        }

        result = await update_issue(mock_context, "FE-123")

        assert "error" in result
        assert "No valid fields provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_issue_closure_with_comment(self):
        """Test that closing an issue with description adds a comment instead of updating description"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"

        # Mock current issue data
        current_issue = {
            "id": "issue_1",
            "identifier": "TEST-123",
            "title": "Test Issue",
            "description": "Original description",
            "team": {"id": "team_1", "name": "Test Team"},
            "state": {"id": "state_1", "name": "In Progress", "type": "started"},
        }

        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock client methods
            mock_client.get_issue_by_id.return_value = current_issue
            mock_client.update_issue.return_value = {"success": True, "issue": current_issue}
            mock_client.create_comment.return_value = {
                "success": True,
                "comment": {
                    "id": "comment_1",
                    "body": "Issue closed due to changelog item: Feature implemented",
                },
            }

            # Mock workflow state resolution
            with patch(
                "arcade_linear.tools.issues.resolve_workflow_state_by_name"
            ) as mock_resolve_state:
                mock_resolve_state.return_value = {
                    "id": "state_done",
                    "name": "Done",
                    "type": "completed",
                }

                # Test closing with description - should add comment instead of updating description
                result = await update_issue(
                    mock_context,
                    issue_id="TEST-123",
                    status="Done",
                    description="Issue closed due to changelog item: Feature implemented",
                )

        # Verify the issue was updated but description was NOT included in update
        mock_client.update_issue.assert_called_once()
        update_call_args = mock_client.update_issue.call_args[0]
        update_input = update_call_args[1]

        # Description should NOT be in the update input
        assert "description" not in update_input
        # Status should be in the update input
        assert "stateId" in update_input
        assert update_input["stateId"] == "state_done"

        # Comment should have been created
        mock_client.create_comment.assert_called_once_with(
            "TEST-123", "Issue closed due to changelog item: Feature implemented"
        )

        # Result should indicate success with comment
        assert result["success"] is True
        assert "added closure reason as comment" in result["message"]

    @pytest.mark.asyncio
    async def test_update_issue_normal_description_update(self):
        """Test that normal description updates (non-closure) still work as before"""
        mock_context = AsyncMock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"

        # Mock current issue data
        current_issue = {
            "id": "issue_1",
            "identifier": "TEST-123",
            "title": "Test Issue",
            "description": "Original description",
            "team": {"id": "team_1", "name": "Test Team"},
            "state": {"id": "state_1", "name": "In Progress", "type": "started"},
        }

        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock client methods
            mock_client.get_issue_by_id.return_value = current_issue
            mock_client.update_issue.return_value = {"success": True, "issue": current_issue}

            # Test normal description update (no status change) - should update description normally
            result = await update_issue(
                mock_context,
                issue_id="TEST-123",
                description="Updated description with more details",
            )

        # Verify the issue was updated with description included
        mock_client.update_issue.assert_called_once()
        update_call_args = mock_client.update_issue.call_args[0]
        update_input = update_call_args[1]

        # Description should be in the update input
        assert "description" in update_input
        assert update_input["description"] == "Updated description with more details"

        # No comment should have been created
        mock_client.create_comment.assert_not_called()

        # Result should indicate success without comment message
        assert result["success"] is True
        assert "added closure reason as comment" not in result["message"]


class TestCreateIssue:
    """Tests for create_issue tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.resolve_team_by_name")
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_create_issue_success(self, mock_client_class, mock_resolve_team, mock_context):
        """Test successful issue creation"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}
        mock_client.create_issue.return_value = {
            "success": True,
            "issue": {
                "id": "issue_1",
                "identifier": "FE-124",
                "title": "New bug report",
                "url": "https://linear.app/team/issue/FE-124",
            },
        }

        # Call function
        result = await create_issue(
            mock_context,
            title="New bug report",
            team="Frontend",
            description="Bug description",
            priority="high",
        )

        # Assertions
        assert result["success"] is True
        assert "Successfully created issue" in result["message"]
        assert result["issue"]["identifier"] == "FE-124"
        assert result["url"] == "https://linear.app/team/issue/FE-124"
        mock_resolve_team.assert_called_once_with(mock_context, "Frontend")
        mock_client.create_issue.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.resolve_team_by_name")
    async def test_create_issue_team_not_found(self, mock_resolve_team, mock_context):
        """Test creation when team not found"""
        # Setup mock
        mock_resolve_team.return_value = None

        # Call function
        result = await create_issue(
            mock_context,
            title="New issue",
            team="NonExistent",
        )

        # Assertions
        assert "error" in result
        assert "Team 'NonExistent' not found" in result["error"]
        assert "get_teams" in result["error"]  # Should suggest using get_teams tool


class TestAddCommentToIssue:
    """Tests for add_comment_to_issue tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_add_comment_success(self, mock_client_class, mock_context):
        """Test successful comment addition"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_issue_by_id.return_value = {
            "id": "issue_1",
            "identifier": "FE-123",
            "title": "Fix authentication bug",
        }
        mock_client.create_comment.return_value = {
            "success": True,
            "comment": {
                "id": "comment_1",
                "body": "Issue resolved by changelog update",
                "createdAt": "2024-01-01T00:00:00Z",
                "user": {"id": "user_1", "name": "John Doe"},
            },
        }

        # Call function
        result = await add_comment_to_issue(
            mock_context, "FE-123", "Issue resolved by changelog update"
        )

        # Assertions
        assert result["success"] is True
        assert "Successfully added comment" in result["message"]
        assert result["comment"]["body"] == "Issue resolved by changelog update"
        mock_client.get_issue_by_id.assert_called_once_with("FE-123")
        mock_client.create_comment.assert_called_once_with(
            "FE-123", "Issue resolved by changelog update"
        )

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.issues.LinearClient")
    async def test_add_comment_issue_not_found(self, mock_client_class, mock_context):
        """Test adding comment to non-existent issue"""
        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock issue not found
            mock_client.get_issue_by_id.return_value = None

            result = await add_comment_to_issue(
                context=mock_context, issue_id="nonexistent-123", comment="This is a test comment"
            )

            assert "error" in result
            assert "Issue not found" in result["error"]


class TestSearchIssuesProjectFilter:
    """Test search_issues project filtering edge cases"""

    @pytest.mark.asyncio
    async def test_search_issues_nonexistent_project_returns_error(self, mock_context):
        """Test that searching for non-existent project returns error instead of all issues"""
        with patch("arcade_linear.tools.issues.resolve_projects_by_name") as mock_resolve_projects:
            # Mock no projects found
            mock_resolve_projects.return_value = []

            result = await search_issues(context=mock_context, project="nonexistent-project")

            # Should return error, not all issues
            assert "error" in result
            assert "Project 'nonexistent-project' not found" in result["error"]
            assert result["issues"] == []
            assert result["total_count"] == 0
            assert result["search_criteria"]["project"] == "nonexistent-project"

    @pytest.mark.asyncio
    async def test_search_issues_with_project_space_hyphen_variation(self, mock_context):
        """Test that searching for project with space finds hyphenated project"""
        with patch("arcade_linear.tools.issues.resolve_projects_by_name") as mock_resolve_projects:
            with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock project resolution finds the hyphenated project
                mock_resolve_projects.return_value = [{"id": "proj_123", "name": "arcade-testing"}]

                # Mock successful issue search
                mock_client.get_issues.return_value = {
                    "nodes": [
                        {
                            "id": "issue_1",
                            "identifier": "TEST-1",
                            "title": "Test issue",
                            "project": {"id": "proj_123", "name": "arcade-testing"},
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "hasPreviousPage": False},
                }

                result = await search_issues(
                    context=mock_context,
                    project="arcade testing",  # Space-separated
                )

                # Should successfully find issues in the hyphenated project
                assert "error" not in result
                assert len(result["issues"]) == 1
                assert result["issues"][0]["project"]["name"] == "arcade-testing"
                assert result["search_criteria"]["project"] == "arcade testing"

                # Verify project resolution was called with the search term
                mock_resolve_projects.assert_called_once_with(mock_context, "arcade testing")


class TestGetTemplates:
    """Test get_templates tool"""

    @pytest.mark.asyncio
    async def test_get_templates_success(self, mock_context):
        """Test successful template retrieval"""
        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock templates response
            mock_client.get_templates.return_value = {
                "nodes": [
                    {
                        "id": "template_1",
                        "name": "Bug Report Template",
                        "description": "Standard bug report template",
                        "team": {"id": "team_1", "name": "Engineering"},
                    },
                    {
                        "id": "template_2",
                        "name": "Feature Request Template",
                        "description": "Standard feature request template",
                        "team": {"id": "team_1", "name": "Engineering"},
                    },
                ]
            }

            result = await get_templates(context=mock_context)

            assert "error" not in result
            assert len(result["templates"]) == 2
            assert result["total_count"] == 2
            assert result["templates"][0]["name"] == "Bug Report Template"
            assert result["templates"][1]["name"] == "Feature Request Template"

    @pytest.mark.asyncio
    async def test_get_templates_with_team_filter(self, mock_context):
        """Test template retrieval with team filter"""
        with patch("arcade_linear.tools.issues.resolve_team_by_name") as mock_resolve_team:
            with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock team resolution
                mock_resolve_team.return_value = {"id": "team_123", "name": "Engineering"}

                # Mock templates response for specific team
                mock_client.get_templates.return_value = {
                    "nodes": [
                        {
                            "id": "template_1",
                            "name": "Engineering Bug Report",
                            "description": "Bug report for engineering team",
                            "team": {"id": "team_123", "name": "Engineering"},
                        }
                    ]
                }

                result = await get_templates(context=mock_context, team="Engineering")

                assert "error" not in result
                assert len(result["templates"]) == 1
                assert result["team_filter"] == "Engineering"
                assert result["templates"][0]["name"] == "Engineering Bug Report"

                # Verify team resolution and template fetching
                mock_resolve_team.assert_called_once_with(mock_context, "Engineering")
                mock_client.get_templates.assert_called_once_with(team_id="team_123")

    @pytest.mark.asyncio
    async def test_get_templates_team_not_found(self, mock_context):
        """Test template retrieval with non-existent team"""
        with patch("arcade_linear.tools.issues.resolve_team_by_name") as mock_resolve_team:
            # Mock team not found
            mock_resolve_team.return_value = None

            result = await get_templates(context=mock_context, team="NonExistentTeam")

            assert "error" in result
            assert "Team 'NonExistentTeam' not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_templates_empty_result(self, mock_context):
        """Test template retrieval when no templates exist"""
        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock empty templates response
            mock_client.get_templates.return_value = {"nodes": []}

            result = await get_templates(context=mock_context)

            assert "error" not in result
            assert len(result["templates"]) == 0
            assert result["total_count"] == 0
            assert "No templates found" in result["message"]

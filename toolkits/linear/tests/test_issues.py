from unittest.mock import AsyncMock, patch

import pytest

from arcade_linear.tools.issues import get_issue


@pytest.fixture
def mock_context():
    """Mock context for testing"""
    context = AsyncMock()
    context.get_auth_token_or_empty.return_value = "test-token"
    return context


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

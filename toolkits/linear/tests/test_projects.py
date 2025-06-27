from unittest.mock import AsyncMock, patch

import pytest

from arcade_linear.tools.projects import (
    get_projects,
)


@pytest.fixture
def mock_context():
    """Fixture for mocked ToolContext"""
    context = AsyncMock()
    context.get_auth_token_or_empty.return_value = "test_token"
    return context


class TestGetProjects:
    """Tests for get_projects tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.projects.LinearClient")
    async def test_get_projects_success(self, mock_client_class, mock_context):
        """Test successful projects retrieval"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_projects.return_value = {
            "nodes": [
                {
                    "id": "project_1",
                    "name": "Q1 Initiative",
                    "description": "Major Q1 project",
                    "state": "started",
                    "progress": 0.6,
                    "startDate": "2024-01-01",
                    "targetDate": "2024-03-31",
                    "creator": {"name": "John Doe"},
                    "lead": {"name": "Jane Smith"},
                    "teams": {"nodes": [{"name": "Frontend"}]},
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_projects(mock_context)

        # Assertions
        assert result["total_count"] == 1
        assert len(result["projects"]) == 1
        assert result["projects"][0]["name"] == "Q1 Initiative"
        assert result["projects"][0]["state"] == "started"
        assert result["projects"][0]["progress"] == 0.6
        mock_client.get_projects.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.projects.resolve_team_by_name")
    @patch("arcade_linear.tools.projects.LinearClient")
    async def test_get_projects_with_team_filter(
        self, mock_client_class, mock_resolve_team, mock_context
    ):
        """Test projects retrieval filtered by team"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}
        mock_client.get_projects.return_value = {
            "nodes": [
                {
                    "id": "project_1",
                    "name": "Frontend Redesign",
                    "state": "started",
                    "teams": {"nodes": [{"id": "team_1", "name": "Frontend"}]},
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_projects(mock_context, team="Frontend")

        # Assertions
        assert result["total_count"] == 1
        assert result["projects"][0]["name"] == "Frontend Redesign"
        assert result["filters"]["team"] == "Frontend"
        mock_resolve_team.assert_called_once_with(mock_context, "Frontend")
        mock_client.get_projects.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.projects.LinearClient")
    async def test_get_projects_with_status_filter(self, mock_client_class, mock_context):
        """Test projects retrieval filtered by status"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_projects.return_value = {
            "nodes": [
                {
                    "id": "project_1",
                    "name": "Completed Project",
                    "state": "completed",
                    "completedAt": "2024-01-15T00:00:00Z",
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_projects(mock_context, status="completed")

        # Assertions
        assert result["total_count"] == 1
        assert result["projects"][0]["state"] == "completed"
        assert result["filters"]["status"] == "completed"
        mock_client.get_projects.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.projects.LinearClient")
    async def test_get_projects_include_archived(self, mock_client_class, mock_context):
        """Test projects retrieval including archived projects"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_projects.return_value = {
            "nodes": [
                {
                    "id": "project_1",
                    "name": "Archived Project",
                    "state": "completed",
                    "autoArchivedAt": "2024-01-20T00:00:00Z",
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_projects(mock_context, include_archived=True)

        # Assertions
        assert result["total_count"] == 1
        assert result["filters"]["include_archived"] is True
        mock_client.get_projects.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.projects.LinearClient")
    async def test_get_projects_pagination(self, mock_client_class, mock_context):
        """Test projects retrieval with pagination"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_projects.return_value = {
            "nodes": [{"id": "project_1", "name": "Project 1"}],
            "pageInfo": {
                "hasNextPage": True,
                "endCursor": "cursor1",
                "startCursor": "cursor0",
            },
        }

        # Call function
        result = await get_projects(mock_context, limit=25, after_cursor="prev_cursor")

        # Assertions
        assert result["pagination"]["has_next_page"] is True
        assert result["pagination"]["end_cursor"] == "cursor1"
        mock_client.get_projects.assert_called_once()

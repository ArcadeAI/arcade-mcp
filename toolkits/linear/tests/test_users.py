import pytest
from unittest.mock import AsyncMock, patch
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.tools.users import (
    get_users,
)


@pytest.fixture
def mock_context():
    """Fixture for mocked ToolContext"""
    context = AsyncMock()
    context.get_auth_token_or_empty.return_value = "test_token"
    return context


class TestGetUsers:
    """Tests for get_users tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.users.LinearClient")
    async def test_get_users_success(self, mock_client_class, mock_context):
        """Test successful users retrieval"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_users.return_value = {
            "nodes": [
                {
                    "id": "user_1",
                    "name": "John Doe",
                    "email": "john@company.com",
                    "displayName": "John Doe",
                    "avatarUrl": "https://avatar.url",
                    "active": True,
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_users(mock_context)

        # Assertions
        assert result["total_count"] == 1
        assert len(result["users"]) == 1
        assert result["users"][0]["name"] == "John Doe"
        assert result["users"][0]["email"] == "john@company.com"
        mock_client.get_users.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.users.resolve_team_by_name")
    @patch("arcade_linear.tools.users.LinearClient")
    async def test_get_users_with_team_filter(self, mock_client_class, mock_resolve_team, mock_context):
        """Test users retrieval filtered by team"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}
        mock_client.get_users.return_value = {
            "nodes": [
                {
                    "id": "user_1",
                    "name": "Frontend Developer",
                    "email": "frontend@company.com",
                    "displayName": "Frontend Developer",
                    "active": True,
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_users(mock_context, team="Frontend")

        # Assertions
        assert result["total_count"] == 1
        assert result["users"][0]["name"] == "Frontend Developer"
        assert result["filters"]["team"] == "Frontend"
        mock_resolve_team.assert_called_once_with(mock_context, "Frontend")
        mock_client.get_users.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.users.LinearClient")
    async def test_get_users_include_guests(self, mock_client_class, mock_context):
        """Test users retrieval including guest users"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_users.return_value = {
            "nodes": [
                {
                    "id": "user_1",
                    "name": "Guest User",
                    "email": "guest@external.com",
                    "displayName": "Guest User",
                    "active": True,
                }
            ],
            "pageInfo": {"hasNextPage": False},
        }

        # Call function
        result = await get_users(mock_context, include_guests=True)

        # Assertions
        assert result["total_count"] == 1
        assert result["filters"]["include_guests"] is True
        mock_client.get_users.assert_called_once_with(
            first=50,
            after=None,
            team_id=None,
            include_guests=True,
        )

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.users.LinearClient")
    async def test_get_users_pagination(self, mock_client_class, mock_context):
        """Test users retrieval with pagination"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_users.return_value = {
            "nodes": [{"id": "user_1", "name": "User 1"}],
            "pageInfo": {
                "hasNextPage": True,
                "endCursor": "cursor1",
                "startCursor": "cursor0",
            },
        }

        # Call function
        result = await get_users(
            mock_context,
            limit=25,
            after_cursor="prev_cursor"
        )

        # Assertions
        assert result["pagination"]["has_next_page"] is True
        assert result["pagination"]["end_cursor"] == "cursor1"
        mock_client.get_users.assert_called_once_with(
            first=25,
            after="prev_cursor",
            team_id=None,
            include_guests=False,
        ) 
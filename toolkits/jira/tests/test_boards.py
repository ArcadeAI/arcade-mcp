from unittest.mock import AsyncMock, Mock, patch

import pytest

# from arcade_jira.client import JiraClient
from arcade_jira.tools.boards import list_all_boards


class TestListAllBoards:
    """Test cases for listing all boards functionality."""

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_success(self, mock_jira_client):
        """Test successful listing of all boards."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {"id": 1, "name": "Scrum Board", "type": "scrum"},
                    {"id": 2, "name": "Kanban Board", "type": "kanban"},
                    {"id": 3, "name": "Simple Board", "type": "simple"},
                ],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=0)

        assert len(result["boards"]) == 3
        assert result["boards"][0]["name"] == "Scrum Board"
        assert result["boards"][1]["name"] == "Kanban Board"
        assert result["boards"][2]["name"] == "Simple Board"
        assert result["total"] == 3
        assert result["isLast"] is True
        assert result["startAt"] == 0
        assert result["maxResults"] == 10

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_pagination(self, mock_jira_client):
        """Test pagination in board listing."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            side_effect=[
                {"values": [{"id": 1, "name": "Board 1", "type": "scrum"}], "isLast": False},
                {"values": [{"id": 2, "name": "Board 2", "type": "kanban"}], "isLast": True},
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=2, offset=0)

        assert len(result["boards"]) == 2
        assert result["boards"][0]["name"] == "Board 1"
        assert result["boards"][1]["name"] == "Board 2"
        assert result["total"] == 2
        assert result["isLast"] is True

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_with_offset(self, mock_jira_client):
        """Test board listing with offset."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 3, "name": "Board 3", "type": "simple"}],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=2)

        assert len(result["boards"]) == 1
        assert result["boards"][0]["name"] == "Board 3"
        assert result["startAt"] == 2

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_limit_enforcement(self, mock_jira_client):
        """Test that limit is properly enforced."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {"id": 1, "name": "Board 1", "type": "scrum"},
                    {"id": 2, "name": "Board 2", "type": "kanban"},
                    {"id": 3, "name": "Board 3", "type": "simple"},
                ],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=2, offset=0)

        assert len(result["boards"]) == 2
        assert result["boards"][0]["name"] == "Board 1"
        assert result["boards"][1]["name"] == "Board 2"
        # Board 3 should be excluded due to limit

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_empty_response(self, mock_jira_client):
        """Test board listing with empty response."""
        mock_client = Mock()
        mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=0)

        assert len(result["boards"]) == 0
        assert result["total"] == 0
        assert result["isLast"] is True

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_limit_validation_max(self, mock_jira_client):
        """Test that maximum limit is enforced."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={"values": [{"id": 1, "name": "Board 1", "type": "scrum"}], "isLast": True}
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=150, offset=0)

        # Should use maximum limit of 100
        assert result["maxResults"] == 100

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_negative_limit(self, mock_jira_client):
        """Test board listing with negative limit."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={"values": [{"id": 1, "name": "Board 1", "type": "scrum"}], "isLast": True}
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=-5, offset=0)

        # Should use minimum limit of 1
        assert result["maxResults"] == 1

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_clean_board_dict(self, mock_jira_client):
        """Test that board dictionaries are properly cleaned."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Test Board",
                        "type": "scrum",
                        "self": "https://example.com/board/1",
                        "extra_field": "should_be_ignored",
                    }
                ],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=0)

        assert len(result["boards"]) == 1
        board = result["boards"][0]
        assert board["id"] == 1
        assert board["name"] == "Test Board"
        assert board["type"] == "scrum"
        assert board["self"] == "https://example.com/board/1"
        assert "extra_field" not in board

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_missing_fields(self, mock_jira_client):
        """Test board listing with boards missing optional fields."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {"id": 1, "name": "Board 1"},  # Missing type and self
                ],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=0)

        assert len(result["boards"]) == 1
        board = result["boards"][0]
        assert board["id"] == 1
        assert board["name"] == "Board 1"
        assert board["type"] is None
        assert board["self"] is None

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_multiple_pages(self, mock_jira_client):
        """Test board listing across multiple pages."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            side_effect=[
                {"values": [{"id": 1, "name": "Board 1", "type": "scrum"}], "isLast": False},
                {"values": [{"id": 2, "name": "Board 2", "type": "kanban"}], "isLast": False},
                {"values": [{"id": 3, "name": "Board 3", "type": "simple"}], "isLast": True},
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=3, offset=0)

        assert len(result["boards"]) == 3
        assert result["boards"][0]["name"] == "Board 1"
        assert result["boards"][1]["name"] == "Board 2"
        assert result["boards"][2]["name"] == "Board 3"
        assert result["total"] == 3
        assert result["isLast"] is True

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_list_all_boards_partial_page(self, mock_jira_client):
        """Test board listing when last page has fewer items than maxResults."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={"values": [{"id": 1, "name": "Board 1", "type": "scrum"}], "isLast": True}
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=10, offset=0)

        assert len(result["boards"]) == 1
        assert result["total"] == 1
        assert result["isLast"] is True

    @pytest.mark.asyncio
    async def test_list_all_boards_client_initialization(self):
        """Test that JiraClient is properly initialized with agile API."""
        with patch("arcade_jira.tools.boards.JiraClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})

            await list_all_boards(Mock(), limit=10, offset=0)

            # Verify JiraClient was called with use_agile_api=True
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[1]["use_agile_api"] is True


class TestBoardIntegration:
    """Integration tests for board functionality."""

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_board_listing_workflow(self, mock_jira_client):
        """Test complete board listing workflow."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {"id": 1, "name": "Scrum Board", "type": "scrum"},
                    {"id": 2, "name": "Kanban Board", "type": "kanban"},
                ],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await list_all_boards(Mock(), limit=5, offset=0)

        # Verify the API call was made correctly
        mock_client.get.assert_called_once_with("/board", params={"startAt": 0, "maxResults": 5})

        # Verify the result structure
        assert len(result["boards"]) == 2
        assert result["total"] == 2
        assert result["isLast"] is True
        assert result["startAt"] == 0
        assert result["maxResults"] == 5

        # Verify board data is properly cleaned
        for board in result["boards"]:
            assert "id" in board
            assert "name" in board
            assert "type" in board
            assert "self" in board
            assert len(board) == 4  # Only the expected fields

    @pytest.mark.asyncio
    async def test_board_listing_with_context(self):
        """Test board listing with proper context handling."""
        mock_context = Mock()
        mock_context.get_auth_token_or_empty.return_value = "test_token"

        with patch("arcade_jira.tools.boards.JiraClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get = AsyncMock(
                return_value={
                    "values": [{"id": 1, "name": "Test Board", "type": "scrum"}],
                    "isLast": True,
                }
            )

            result = await list_all_boards(mock_context, limit=10, offset=0)

            # Verify context was used to get auth token
            mock_context.get_auth_token_or_empty.assert_called_once()

            # Verify JiraClient was initialized with the token
            mock_client_class.assert_called_once_with("test_token", use_agile_api=True)

            assert len(result["boards"]) == 1
            assert result["boards"][0]["name"] == "Test Board"

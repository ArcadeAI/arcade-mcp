from unittest.mock import AsyncMock, Mock, patch

import pytest

from arcade_jira.tools.boards import get_boards


class TestGetBoards:
    """Test cases for getting boards functionality."""

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_all_boards_success(self, mock_jira_client):
        """Test successful listing of all boards with default pagination."""
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

        result = await get_boards(Mock())

        assert len(result["boards"]) == 3
        assert result["boards"][0]["name"] == "Scrum Board"
        assert result["boards"][1]["name"] == "Kanban Board"
        assert result["boards"][2]["name"] == "Simple Board"
        assert result["total"] == 3
        assert result["isLast"] is True
        assert result["startAt"] == 0
        assert result["maxResults"] == 50

        # Verify API call
        mock_client.get.assert_called_once_with("/board", params={"startAt": 0, "maxResults": 50})

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_all_boards_with_pagination(self, mock_jira_client):
        """Test board listing with custom pagination parameters."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 10, "name": "Board 10", "type": "scrum"}],
                "isLast": False,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), limit=10, offset=5)

        assert len(result["boards"]) == 1
        assert result["boards"][0]["name"] == "Board 10"
        assert result["isLast"] is False
        assert result["startAt"] == 5
        assert result["maxResults"] == 10

        # Verify API call with pagination
        mock_client.get.assert_called_once_with("/board", params={"startAt": 5, "maxResults": 10})

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_by_id_success(self, mock_jira_client):
        """Test successful retrieval of boards by numeric ID."""
        mock_client = Mock()
        mock_client.get = AsyncMock(return_value={"id": 123, "name": "Test Board", "type": "scrum"})
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["123"])

        assert len(result["boards"]) == 1
        assert result["boards"][0]["id"] == 123
        assert result["boards"][0]["name"] == "Test Board"
        assert result["boards"][0]["found_by"] == "id"
        assert len(result["errors"]) == 0

        # Verify API call
        mock_client.get.assert_called_once_with("/board/123")

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_by_name_success(self, mock_jira_client):
        """Test successful retrieval of boards by name."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 456, "name": "My Board", "type": "kanban"}],
                "isLast": True,
            }
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["My Board"])

        assert len(result["boards"]) == 1
        assert result["boards"][0]["id"] == 456
        assert result["boards"][0]["name"] == "My Board"
        assert result["boards"][0]["found_by"] == "name"
        assert len(result["errors"]) == 0

        # Verify API call
        mock_client.get.assert_called_once_with(
            "/board", params={"name": "My Board", "startAt": 0, "maxResults": 1}
        )

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_mixed_identifiers(self, mock_jira_client):
        """Test retrieval with mixed ID and name identifiers."""
        mock_client = Mock()

        # Mock responses: first call for ID, second call for name
        mock_client.get = AsyncMock(
            side_effect=[
                {"id": 123, "name": "Board by ID", "type": "scrum"},  # ID lookup
                {"values": [{"id": 456, "name": "Board by Name", "type": "kanban"}]},  # Name lookup
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["123", "Board by Name"])

        assert len(result["boards"]) == 2
        assert result["boards"][0]["id"] == 123
        assert result["boards"][0]["found_by"] == "id"
        assert result["boards"][1]["id"] == 456
        assert result["boards"][1]["found_by"] == "name"
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_id_not_found_fallback_to_name(self, mock_jira_client):
        """Test fallback from ID to name when numeric ID is not found."""
        mock_client = Mock()

        # First call fails (ID not found), second call succeeds (name found)
        mock_client.get = AsyncMock(
            side_effect=[
                Exception("Board not found"),  # ID lookup fails
                {"values": [{"id": 789, "name": "123", "type": "simple"}]},  # Name lookup succeeds
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["123"])

        assert len(result["boards"]) == 1
        assert result["boards"][0]["id"] == 789
        assert result["boards"][0]["name"] == "123"
        assert result["boards"][0]["found_by"] == "name"
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_not_found(self, mock_jira_client):
        """Test when boards are not found by either ID or name."""
        mock_client = Mock()

        # Both ID and name lookups fail
        mock_client.get = AsyncMock(
            side_effect=[
                Exception("Board not found"),  # ID lookup fails
                {"values": []},  # Name lookup returns empty
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["999"])

        assert len(result["boards"]) == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["board_identifier"] == "999"
        assert "not found" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_name_not_found(self, mock_jira_client):
        """Test when board name is not found."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={"values": []}  # Empty response
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["Nonexistent Board"])

        assert len(result["boards"]) == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["board_identifier"] == "Nonexistent Board"
        assert "not found" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_partial_success(self, mock_jira_client):
        """Test when some boards are found and some are not."""
        mock_client = Mock()

        # First board found by ID, second board not found
        mock_client.get = AsyncMock(
            side_effect=[
                {"id": 123, "name": "Found Board", "type": "scrum"},  # First board found
                Exception("Not found"),  # Second board ID fails
                {"values": []},  # Second board name lookup empty
            ]
        )
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["123", "Missing Board"])

        assert len(result["boards"]) == 1
        assert result["boards"][0]["id"] == 123
        assert len(result["errors"]) == 1
        assert result["errors"][0]["board_identifier"] == "Missing Board"

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_api_error_treated_as_not_found(self, mock_jira_client):
        """Test that API errors during board lookup are treated as 'not found'."""
        mock_client = Mock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("API error"))
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), ["123"])

        assert len(result["boards"]) == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]["error"]
        assert result["errors"][0]["board_identifier"] == "123"

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    @patch("arcade_jira.tools.boards.validate_board_limit")
    async def test_get_boards_limit_validation(self, mock_validate, mock_jira_client):
        """Test that board limit validation is called."""
        mock_validate.return_value = 25
        mock_client = Mock()
        mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
        mock_jira_client.return_value = mock_client

        await get_boards(Mock(), limit=25)

        mock_validate.assert_called_once_with(25)

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.boards.JiraClient")
    async def test_get_boards_empty_list(self, mock_jira_client):
        """Test behavior with empty board identifiers list."""
        mock_client = Mock()
        mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
        mock_jira_client.return_value = mock_client

        result = await get_boards(Mock(), [])

        # Empty list should trigger get all boards behavior
        assert "boards" in result
        assert "total" in result
        mock_client.get.assert_called_once_with("/board", params={"startAt": 0, "maxResults": 50})

from unittest.mock import AsyncMock, Mock, patch

import pytest

from arcade_jira.tools.sprint_planning import list_sprints_for_boards


class TestListSprintsForBoards:
    """Test cases for the list_sprints_for_boards tool."""

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_success(self, mock_jira_client):
        """Test successful listing of sprints for multiple boards."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {"id": 1, "name": "Sprint 1", "state": "active"},
                    {"id": 2, "name": "Sprint 2", "state": "future"},
                ],
                "isLast": True,
                "total": 2,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
        ) as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), boards=["123"])

            assert len(result["boards"]) == 1
            assert result["boards"][0]["name"] == "Test Board"
            assert 123 in result["sprints_by_board"]
            assert len(result["sprints_by_board"][123]["sprints"]) == 2

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_no_boards_specified(self, mock_jira_client):
        """Test listing sprints when no boards are specified and none support sprints."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning._list_boards_with_sprints"
        ) as mock_list_boards:
            mock_list_boards.return_value = {
                "boards": []  # No boards that support sprints
            }

            result = await list_sprints_for_boards(Mock())

            assert "No boards that support sprints found" in result["message"]
            assert len(result["boards"]) == 0
            assert len(result["sprints_by_board"]) == 0

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_auto_discover_boards(self, mock_jira_client):
        """Test listing sprints when no boards are specified but some support sprints."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 1, "name": "Sprint 1", "state": "active"}],
                "isLast": True,
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with (
            patch(
                "arcade_jira.tools.sprint_planning._list_boards_with_sprints"
            ) as mock_list_boards,
            patch(
                "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
            ) as mock_get_boards,
        ):
            mock_list_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}]
            }
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock())

            assert len(result["boards"]) == 1
            assert 123 in result["sprints_by_board"]
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_board_not_found(self, mock_jira_client):
        """Test handling when a board is not found."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
        ) as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [],
                "errors": [{"board_identifier": "999", "error": "Board not found"}],
            }

            result = await list_sprints_for_boards(Mock(), boards=["999"])

            assert len(result["boards"]) == 0
            assert len(result["errors"]) == 1
            assert result["errors"][0]["board_identifier"] == "999"

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_non_sprint_board(self, mock_jira_client):
        """Test handling when a board doesn't support sprints."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with (
            patch(
                "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
            ) as mock_get_boards,
            patch(
                "arcade_jira.tools.sprint_planning._try_fetch_sprints_and_determine_type"
            ) as mock_try_fetch,
        ):
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Kanban Board", "type": "kanban"}],
                "errors": [],
            }
            mock_try_fetch.return_value = (False, "kanban", None)

            result = await list_sprints_for_boards(Mock(), boards=["123"])

            assert len(result["boards"]) == 0
            assert len(result["errors"]) == 1
            assert "does not support sprints" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_state_filter(self, mock_jira_client):
        """Test listing sprints with state filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 1, "name": "Active Sprint", "state": "active"}],
                "isLast": True,
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
        ) as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), boards=["123"], state="active")

            assert len(result["boards"]) == 1
            assert 123 in result["sprints_by_board"]
            assert len(result["sprints_by_board"][123]["sprints"]) == 1
            assert result["sprints_by_board"][123]["sprints"][0]["state"] == "active"

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_pagination(self, mock_jira_client):
        """Test listing sprints with pagination parameters."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [{"id": 11, "name": "Sprint 11", "state": "closed"}],
                "isLast": False,
                "total": 20,
                "startAt": 10,
                "maxResults": 1,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
        ) as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(
                Mock(), boards=["123"], sprints_per_board=1, offset=10
            )

            assert len(result["boards"]) == 1
            assert 123 in result["sprints_by_board"]
            assert result["sprints_by_board"][123]["startAt"] == 10
            assert result["sprints_by_board"][123]["maxResults"] == 1

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_exception_handling(self, mock_jira_client):
        """Test handling of unexpected exceptions."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with patch(
            "arcade_jira.tools.sprint_planning.get_boards_by_ids_or_names"
        ) as mock_get_boards:
            mock_get_boards.side_effect = Exception("Unexpected API error")

            result = await list_sprints_for_boards(Mock(), boards=["123"])

            assert len(result["boards"]) == 0
            assert len(result["errors"]) == 1
            assert "Unexpected error" in result["errors"][0]["error"]

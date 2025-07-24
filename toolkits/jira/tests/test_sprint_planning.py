from unittest.mock import AsyncMock, Mock, patch

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

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
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "active",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "future",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 2,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), board_ids=["123"])

            assert len(result["boards"]) == 1
            assert result["boards"][0]["name"] == "Test Board"
            assert 123 in result["sprints_by_board"]
            assert len(result["sprints_by_board"][123]["sprints"]) == 2
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_list_sprints_for_boards_no_boards_specified(self):
        """Test error when no board IDs are specified."""
        with pytest.raises(ToolExecutionError) as exc_info:
            await list_sprints_for_boards(Mock(), board_ids=[])

        assert "Board IDs are required" in str(exc_info.value)
        assert "scrum boards" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_multiple_boards(self, mock_jira_client):
        """Test listing sprints for multiple boards."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "active",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    }
                ],
                "isLast": True,
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            # Mock responses for two different boards
            def mock_get_boards_side_effect(context, board_ids, **kwargs):
                return {
                    "boards": [
                        {"id": 123, "name": "Board 1", "type": "scrum"},
                        {"id": 456, "name": "Board 2", "type": "scrum"},
                    ],
                    "errors": [],
                }

            mock_get_boards.side_effect = mock_get_boards_side_effect

            result = await list_sprints_for_boards(Mock(), board_ids=["123", "456"])

            assert len(result["boards"]) == 2
            assert result["boards"][0]["name"] == "Board 1"
            assert result["boards"][1]["name"] == "Board 2"
            assert 123 in result["sprints_by_board"]
            assert 456 in result["sprints_by_board"]
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_pagination(self, mock_jira_client):
        """Test listing sprints with pagination."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 11,
                        "name": "Sprint 11",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    }
                ],
                "isLast": False,
                "total": 20,
                "startAt": 10,
                "maxResults": 1,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(
                Mock(), board_ids=["123"], offset=10, sprints_per_board=1
            )

            assert len(result["boards"]) == 1
            assert result["sprints_by_board"][123]["startAt"] == 10
            assert result["sprints_by_board"][123]["maxResults"] == 1
            assert len(result["sprints_by_board"][123]["sprints"]) == 1

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_board_not_found(self, mock_jira_client):
        """Test handling when a board is not found."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [],
                "errors": [{"board_identifier": "999", "error": "Board not found"}],
            }

            result = await list_sprints_for_boards(Mock(), board_ids=["999"])

            assert len(result["boards"]) == 0
            assert len(result["sprints_by_board"]) == 0
            assert len(result["errors"]) == 1
            assert "Board not found" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_non_sprint_board(self, mock_jira_client):
        """Test handling when a board doesn't support sprints."""
        mock_client = Mock()
        mock_jira_client.return_value = mock_client

        with (
            patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards,
            patch(
                "arcade_jira.tools.sprint_planning._try_fetch_sprints_and_determine_type"
            ) as mock_try_fetch,
        ):
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Kanban Board", "type": "kanban"}],
                "errors": [],
            }
            mock_try_fetch.return_value = (False, "kanban", None)

            result = await list_sprints_for_boards(Mock(), board_ids=["123"])

            assert len(result["boards"]) == 0
            assert len(result["sprints_by_board"]) == 0
            assert len(result["errors"]) == 1
            assert "does not support sprints" in result["errors"][0]["error"]
            assert "Only Scrum boards support sprints" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_state_filter(self, mock_jira_client):
        """Test listing sprints with state filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Active Sprint",
                        "state": "active",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    }
                ],
                "isLast": True,
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), board_ids=["123"], state=["active"])

            assert len(result["boards"]) == 1
            assert len(result["sprints_by_board"][123]["sprints"]) == 1
            assert result["sprints_by_board"][123]["sprints"][0]["state"] == "active"

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_date_range(self, mock_jira_client):
        """Test listing sprints with date range filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "active",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                    {
                        "id": 3,
                        "name": "Sprint 3",
                        "state": "future",
                        "startDate": "2024-02-01T00:00:00.000Z",
                        "endDate": "2024-02-14T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(
                Mock(), board_ids=["123"], start_date="2024-01-10", end_date="2024-01-20"
            )

            assert len(result["boards"]) == 1
            # Should include sprints 1 and 2 (overlapping with date range)
            sprint_names = [s["name"] for s in result["sprints_by_board"][123]["sprints"]]
            assert "Sprint 1" in sprint_names
            assert "Sprint 2" in sprint_names
            assert "Sprint 3" not in sprint_names

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_start_date_only(self, mock_jira_client):
        """Test listing sprints with only start date filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "active",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                    {
                        "id": 3,
                        "name": "Sprint 3",
                        "state": "future",
                        "startDate": "2024-02-01T00:00:00.000Z",
                        "endDate": "2024-02-14T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(
                Mock(), board_ids=["123"], start_date="2024-01-10"
            )

            assert len(result["boards"]) == 1
            # Should include sprints 2 and 3 (start on or after 2024-01-10)
            sprint_names = [s["name"] for s in result["sprints_by_board"][123]["sprints"]]
            assert "Sprint 1" in sprint_names  # Overlaps with filter start
            assert "Sprint 2" in sprint_names
            assert "Sprint 3" in sprint_names

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_end_date_only(self, mock_jira_client):
        """Test listing sprints with only end date filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "active",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                    {
                        "id": 3,
                        "name": "Sprint 3",
                        "state": "future",
                        "startDate": "2024-02-01T00:00:00.000Z",
                        "endDate": "2024-02-14T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), board_ids=["123"], end_date="2024-01-20")

            assert len(result["boards"]) == 1
            # Should include sprints 1 and 2 (end on or before 2024-01-20 or overlap)
            sprint_names = [s["name"] for s in result["sprints_by_board"][123]["sprints"]]
            assert "Sprint 1" in sprint_names
            assert "Sprint 2" in sprint_names  # Overlaps with filter end
            assert "Sprint 3" not in sprint_names  # Starts after filter end

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_for_boards_with_specific_date(self, mock_jira_client):
        """Test listing sprints with specific date filter."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "active",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 2,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(
                Mock(), board_ids=["123"], specific_date="2024-01-10"
            )

            assert len(result["boards"]) == 1
            # Should only include Sprint 1 (active on 2024-01-10)
            assert len(result["sprints_by_board"][123]["sprints"]) == 1
            assert result["sprints_by_board"][123]["sprints"][0]["name"] == "Sprint 1"

    @pytest.mark.asyncio
    async def test_list_sprints_conflicting_date_parameters(self):
        """Test error when specific_date is used with start_date or end_date."""
        with pytest.raises(ToolExecutionError) as exc_info:
            await list_sprints_for_boards(
                Mock(), board_ids=["123"], start_date="2024-01-01", specific_date="2024-01-15"
            )

        assert "Cannot use 'specific_date' together with 'start_date' or 'end_date'" in str(
            exc_info.value
        )

        with pytest.raises(ToolExecutionError) as exc_info:
            await list_sprints_for_boards(
                Mock(), board_ids=["123"], end_date="2024-01-31", specific_date="2024-01-15"
            )

        assert "Cannot use 'specific_date' together with 'start_date' or 'end_date'" in str(
            exc_info.value
        )

        with pytest.raises(ToolExecutionError) as exc_info:
            await list_sprints_for_boards(
                Mock(),
                board_ids=["123"],
                start_date="2024-01-01",
                end_date="2024-01-31",
                specific_date="2024-01-15",
            )

        assert "Cannot use 'specific_date' together with 'start_date' or 'end_date'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    @patch("arcade_jira.tools.sprint_planning.JiraClient")
    async def test_list_sprints_sorting_latest_first(self, mock_jira_client):
        """Test that sprints are sorted with latest first."""
        mock_client = Mock()
        mock_client.get = AsyncMock(
            return_value={
                "values": [
                    {
                        "id": 1,
                        "name": "Sprint 1",
                        "state": "closed",
                        "startDate": "2024-01-01T00:00:00.000Z",
                        "endDate": "2024-01-14T00:00:00.000Z",
                    },
                    {
                        "id": 3,
                        "name": "Sprint 3",
                        "state": "future",
                        "startDate": "2024-02-01T00:00:00.000Z",
                        "endDate": "2024-02-14T00:00:00.000Z",
                    },
                    {
                        "id": 2,
                        "name": "Sprint 2",
                        "state": "active",
                        "startDate": "2024-01-15T00:00:00.000Z",
                        "endDate": "2024-01-28T00:00:00.000Z",
                    },
                ],
                "isLast": True,
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
            }
        )
        mock_jira_client.return_value = mock_client

        with patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards:
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            result = await list_sprints_for_boards(Mock(), board_ids=["123"])

            assert len(result["boards"]) == 1
            sprints = result["sprints_by_board"][123]["sprints"]
            # Should be sorted by end date descending: Sprint 3, Sprint 2, Sprint 1
            assert sprints[0]["name"] == "Sprint 3"  # Latest end date
            assert sprints[1]["name"] == "Sprint 2"
            assert sprints[2]["name"] == "Sprint 1"  # Earliest end date


class TestSprintStateValidationIntegration:
    """Integration tests for sprint state validation in list_sprints_for_boards."""

    @pytest.mark.asyncio
    async def test_list_sprints_valid_state_single(self):
        """Test list_sprints_for_boards with valid single state."""
        with (
            patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards,
            patch("arcade_jira.tools.sprint_planning.JiraClient") as mock_jira_client,
        ):
            # Mock board resolution
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            # Mock client response
            mock_client = Mock()
            mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
            mock_jira_client.return_value = mock_client

            # Should not raise an exception
            result = await list_sprints_for_boards(Mock(), board_ids=["123"], state=["active"])

            assert "boards" in result
            assert "sprints_by_board" in result

    @pytest.mark.asyncio
    async def test_list_sprints_valid_state_multiple(self):
        """Test list_sprints_for_boards with valid multiple states."""
        with (
            patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards,
            patch("arcade_jira.tools.sprint_planning.JiraClient") as mock_jira_client,
        ):
            # Mock board resolution
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            # Mock client response
            mock_client = Mock()
            mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
            mock_jira_client.return_value = mock_client

            # Should not raise an exception
            result = await list_sprints_for_boards(
                Mock(), board_ids=["123"], state=["active", "future"]
            )

            assert "boards" in result
            assert "sprints_by_board" in result

    @pytest.mark.asyncio
    async def test_list_sprints_invalid_state_single(self):
        """Test list_sprints_for_boards with invalid single state raises error."""
        with pytest.raises(RetryableToolError) as exc_info:
            await list_sprints_for_boards(Mock(), board_ids=["123"], state=["invalid"])

        assert "Invalid sprint state(s): 'invalid'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_sprints_invalid_state_multiple(self):
        """Test list_sprints_for_boards with invalid multiple states raises error."""
        with pytest.raises(RetryableToolError) as exc_info:
            await list_sprints_for_boards(
                Mock(), board_ids=["123"], state=["active", "invalid", "badstate"]
            )

        assert "Invalid sprint state(s):" in str(exc_info.value)
        assert "'invalid'" in str(exc_info.value)
        assert "'badstate'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_sprints_mixed_valid_invalid_state(self):
        """Test list_sprints_for_boards with mix of valid and invalid states."""
        with pytest.raises(RetryableToolError) as exc_info:
            await list_sprints_for_boards(
                Mock(), board_ids=["123"], state=["active", "invalid", "future"]
            )

        # Should only report invalid states, not the valid ones
        assert "Invalid sprint state(s): 'invalid'" in str(exc_info.value)
        assert "'active'" not in str(exc_info.value) or "Invalid" not in str(exc_info.value)
        assert "'future'" not in str(exc_info.value) or "Invalid" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_sprints_none_state(self):
        """Test list_sprints_for_boards with None state (should work fine)."""
        with (
            patch("arcade_jira.tools.sprint_planning.get_boards") as mock_get_boards,
            patch("arcade_jira.tools.sprint_planning.JiraClient") as mock_jira_client,
        ):
            # Mock board resolution
            mock_get_boards.return_value = {
                "boards": [{"id": 123, "name": "Test Board", "type": "scrum"}],
                "errors": [],
            }

            # Mock client response
            mock_client = Mock()
            mock_client.get = AsyncMock(return_value={"values": [], "isLast": True})
            mock_jira_client.return_value = mock_client

            # Should not raise an exception
            result = await list_sprints_for_boards(Mock(), board_ids=["123"], state=None)

            assert "boards" in result
            assert "sprints_by_board" in result

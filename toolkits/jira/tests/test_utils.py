from arcade_jira.constants import BOARD_TYPES_WITH_SPRINTS
from arcade_jira.utils import (
    build_sprint_params,
    clean_board_dict,
    clean_sprint_dict,
    create_board_error_message,
    create_board_result_dict,
    create_error_entry,
    create_sprint_result_dict,
    find_board_by_name,
    validate_board_limit,
    validate_sprint_limit,
)


class TestBoardUtils:
    """Test cases for board-related utility functions."""

    def test_clean_board_dict(self):
        """Test cleaning board dictionary."""
        raw_board = {
            "id": 123,
            "name": "Test Board",
            "type": "scrum",
            "self": "https://example.com/board/123",
            "extra_field": "should_be_ignored",
        }

        cleaned = clean_board_dict(raw_board)

        assert cleaned == {
            "id": 123,
            "name": "Test Board",
            "type": "scrum",
            "self": "https://example.com/board/123",
        }
        assert "extra_field" not in cleaned

    def test_clean_board_dict_missing_fields(self):
        """Test cleaning board dictionary with missing optional fields."""
        raw_board = {
            "id": 123,
            "name": "Test Board",
        }

        cleaned = clean_board_dict(raw_board)

        assert cleaned == {
            "id": 123,
            "name": "Test Board",
            "type": None,
            "self": None,
        }

    def test_validate_board_limit(self):
        """Test board limit validation."""
        assert validate_board_limit(1) == 1
        assert validate_board_limit(50) == 50
        assert validate_board_limit(100) == 100
        assert validate_board_limit(0) == 1  # Min enforced
        assert validate_board_limit(-5) == 1  # Min enforced
        assert validate_board_limit(150) == 100  # Max enforced
        assert validate_board_limit(200) == 100  # Max enforced

    def test_find_board_by_name_exact_match(self):
        """Test finding board by exact name match."""
        boards = [
            {"id": 1, "name": "Scrum Board"},
            {"id": 2, "name": "Kanban Board"},
            {"id": 3, "name": "Test Board"},
        ]

        result = find_board_by_name(boards, "Scrum Board")
        assert result == {"id": 1, "name": "Scrum Board"}

    def test_find_board_by_name_case_insensitive(self):
        """Test finding board by name with case insensitive matching."""
        boards = [
            {"id": 1, "name": "Scrum Board"},
            {"id": 2, "name": "Kanban Board"},
        ]

        result = find_board_by_name(boards, "scrum board")
        assert result == {"id": 1, "name": "Scrum Board"}

    def test_find_board_by_name_not_found(self):
        """Test finding board by name when not found."""
        boards = [
            {"id": 1, "name": "Scrum Board"},
            {"id": 2, "name": "Kanban Board"},
        ]

        result = find_board_by_name(boards, "Non-existent Board")
        assert result is None

    def test_find_board_by_name_empty_list(self):
        """Test finding board by name in empty list."""
        boards = []
        result = find_board_by_name(boards, "Any Board")
        assert result is None

    def test_create_board_error_message(self):
        """Test creating board error message."""
        available_boards = [
            {"id": 1, "name": "Scrum Board"},
            {"id": 2, "name": "Kanban Board"},
        ]

        result = create_board_error_message("Test Board", available_boards)
        expected = "Board 'Test Board' not found. Available boards: Scrum Board, Kanban Board"
        assert result == expected

    def test_create_board_error_message_empty_list(self):
        """Test creating board error message with empty available boards."""
        available_boards = []
        result = create_board_error_message("Test Board", available_boards)
        expected = "Board 'Test Board' not found. Available boards: "
        assert result == expected

    def test_create_board_result_dict(self):
        """Test creating board result dictionary."""
        boards = [
            {"id": 1, "name": "Board 1", "type": "scrum"},
            {"id": 2, "name": "Board 2", "type": "kanban"},
        ]

        result = create_board_result_dict(boards, 2, True, 0, 50)

        assert result == {
            "boards": [
                {"id": 1, "name": "Board 1", "type": "scrum", "self": None},
                {"id": 2, "name": "Board 2", "type": "kanban", "self": None},
            ],
            "total": 2,
            "isLast": True,
            "startAt": 0,
            "maxResults": 50,
        }


class TestSprintUtils:
    """Test cases for sprint-related utility functions."""

    def test_clean_sprint_dict(self):
        """Test cleaning sprint dictionary."""
        raw_sprint = {
            "id": 456,
            "name": "Sprint 1",
            "state": "active",
            "startDate": "2024-01-01T00:00:00.000Z",
            "endDate": "2024-01-15T00:00:00.000Z",
            "completeDate": None,
            "originBoardId": 123,
            "goal": "Complete feature X",
            "self": "https://example.com/sprint/456",
            "extra_field": "should_be_ignored",
        }

        cleaned = clean_sprint_dict(raw_sprint)

        assert cleaned == {
            "id": 456,
            "name": "Sprint 1",
            "state": "active",
            "startDate": "2024-01-01T00:00:00.000Z",
            "endDate": "2024-01-15T00:00:00.000Z",
            "completeDate": None,
            "originBoardId": 123,
            "goal": "Complete feature X",
            "self": "https://example.com/sprint/456",
        }
        assert "extra_field" not in cleaned

    def test_clean_sprint_dict_missing_fields(self):
        """Test cleaning sprint dictionary with missing optional fields."""
        raw_sprint = {
            "id": 456,
            "name": "Sprint 1",
        }

        cleaned = clean_sprint_dict(raw_sprint)

        assert cleaned == {
            "id": 456,
            "name": "Sprint 1",
            "state": None,
            "startDate": None,
            "endDate": None,
            "completeDate": None,
            "originBoardId": None,
            "goal": None,
            "self": None,
        }

    def test_build_sprint_params_basic(self):
        """Test building sprint parameters with basic values."""
        result = build_sprint_params(0, 50)

        assert result == {
            "startAt": "0",
            "maxResults": "50",
        }

    def test_build_sprint_params_with_state(self):
        """Test building sprint parameters with state filter."""
        result = build_sprint_params(10, 25, "active")

        assert result == {
            "startAt": "10",
            "maxResults": "25",
            "state": "active",
        }

    def test_build_sprint_params_with_none_state(self):
        """Test building sprint parameters with None state."""
        result = build_sprint_params(0, 50, None)

        assert result == {
            "startAt": "0",
            "maxResults": "50",
        }

    def test_validate_sprint_limit(self):
        """Test sprint limit validation."""
        assert validate_sprint_limit(1) == 1
        assert validate_sprint_limit(25) == 25
        assert validate_sprint_limit(50) == 50
        assert validate_sprint_limit(0) == 1  # Min enforced
        assert validate_sprint_limit(-5) == 1  # Min enforced
        assert validate_sprint_limit(75) == 50  # Max enforced
        assert validate_sprint_limit(100) == 50  # Max enforced

    def test_create_sprint_result_dict(self):
        """Test creating sprint result dictionary."""
        board = {"id": 123, "name": "Test Board", "type": "scrum"}
        sprints = [
            {"id": 1, "name": "Sprint 1", "state": "active"},
            {"id": 2, "name": "Sprint 2", "state": "future"},
        ]
        response = {
            "isLast": True,
            "total": 2,
            "startAt": 0,
            "maxResults": 50,
        }

        result = create_sprint_result_dict(board, sprints, response)

        assert result == {
            "board": {"id": 123, "name": "Test Board", "type": "scrum", "self": None},
            "sprints": [
                {"id": 1, "name": "Sprint 1", "state": "active"},
                {"id": 2, "name": "Sprint 2", "state": "future"},
            ],
            "isLast": True,
            "total": 2,
            "startAt": 0,
            "maxResults": 50,
        }


class TestErrorUtils:
    """Test cases for error-related utility functions."""

    def test_create_error_entry_basic(self):
        """Test creating basic error entry."""
        result = create_error_entry("board123", "Board not found")

        assert result == {
            "board_identifier": "board123",
            "error": "Board not found",
        }

    def test_create_error_entry_with_board_name(self):
        """Test creating error entry with board name."""
        result = create_error_entry("board123", "Board not found", "Test Board")

        assert result == {
            "board_identifier": "board123",
            "error": "Board not found",
            "board_name": "Test Board",
        }

    def test_create_error_entry_with_board_id(self):
        """Test creating error entry with board ID."""
        result = create_error_entry("board123", "Board not found", board_id=456)

        assert result == {
            "board_identifier": "board123",
            "error": "Board not found",
            "board_id": "456",
        }

    def test_create_error_entry_with_all_fields(self):
        """Test creating error entry with all optional fields."""
        result = create_error_entry("board123", "Board not found", "Test Board", 456)

        assert result == {
            "board_identifier": "board123",
            "error": "Board not found",
            "board_name": "Test Board",
            "board_id": "456",
        }


class TestConstants:
    """Test cases for constants."""

    def test_board_types_with_sprints(self):
        """Test BOARD_TYPES_WITH_SPRINTS constant."""
        assert {"scrum"} == BOARD_TYPES_WITH_SPRINTS
        assert "scrum" in BOARD_TYPES_WITH_SPRINTS
        assert "kanban" not in BOARD_TYPES_WITH_SPRINTS
        assert "simple" not in BOARD_TYPES_WITH_SPRINTS


class TestIntegration:
    """Integration tests for utility functions working together."""

    def test_board_workflow(self):
        """Test complete board workflow using multiple utility functions."""
        # Simulate raw board data from API
        raw_board = {
            "id": 123,
            "name": "Scrum Board",
            "type": "simple",  # This would trigger sprint endpoint check
            "self": "https://example.com/board/123",
        }

        # Create a board to clean
        raw_board = {"id": 123, "name": "Scrum Board", "type": "simple", "self": "url"}
        cleaned_board = clean_board_dict(raw_board)
        assert cleaned_board["name"] == "Scrum Board"

        # Check if we should verify with sprint endpoint (should be True)
        # Simulate finding board by name
        boards_list = [cleaned_board]
        found_board = find_board_by_name(boards_list, "scrum board")
        assert found_board == cleaned_board

        # Create result dictionary
        result = create_board_result_dict([cleaned_board], 1, True, 0, 50)
        assert result["total"] == 1
        assert result["boards"][0]["name"] == "Scrum Board"

    def test_sprint_workflow(self):
        """Test complete sprint workflow using multiple utility functions."""
        # Simulate board and sprint data
        board = {"id": 123, "name": "Test Board", "type": "scrum"}
        sprints = [
            {"id": 1, "name": "Sprint 1", "state": "active"},
            {"id": 2, "name": "Sprint 2", "state": "future"},
        ]

        # Build parameters
        params = build_sprint_params(0, 50, "active")
        assert params["maxResults"] == "50"
        assert params["state"] == "active"

        # Validate limits
        validated_limit = validate_sprint_limit(75)  # Should be capped at 50
        assert validated_limit == 50

        # Create result
        response = {"isLast": True, "total": 2, "startAt": 0, "maxResults": 50}
        result = create_sprint_result_dict(board, sprints, response)

        assert result["board"]["name"] == "Test Board"
        assert len(result["sprints"]) == 2
        assert result["total"] == 2

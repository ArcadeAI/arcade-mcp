from datetime import timedelta
from typing import Any, ClassVar

from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import Critic
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.tools.sprint_planning import list_sprints_for_boards


class BoardIdsCritic(Critic):
    """Custom critic for board IDs that accepts either name or ID as equivalent."""

    # Mapping of board names to IDs from test context
    BOARD_MAPPING: ClassVar[dict[str, str]] = {
        "Development Team": "123",
        "Marketing Board": "456",
        "QA Testing": "789",
        "Product Roadmap": "999",
    }

    def evaluate(self, expected: list[str], actual: list[str]) -> dict[str, Any]:
        """Evaluate board IDs, accepting either name or ID as valid."""
        if not expected or not actual:
            match = expected == actual
            return {"match": match, "score": self.weight if match else 0.0}

        # Normalize both expected and actual to sets of IDs
        expected_ids = set()
        for board in expected:
            if board in self.BOARD_MAPPING:
                expected_ids.add(self.BOARD_MAPPING[board])
            else:
                expected_ids.add(board)  # Already an ID

        actual_ids = set()
        for board in actual:
            if board in self.BOARD_MAPPING:
                actual_ids.add(self.BOARD_MAPPING[board])
            else:
                actual_ids.add(board)  # Already an ID

        match = expected_ids == actual_ids
        return {"match": match, "score": self.weight if match else 0.0}


class StateListCritic(Critic):
    """Custom critic for state lists that ignores order."""

    def evaluate(self, expected: list[str] | None, actual: list[str] | None) -> dict[str, Any]:
        """Evaluate state lists, ignoring order."""
        if expected is None and actual is None:
            return {"match": True, "score": self.weight}

        if expected is None or actual is None:
            match = expected == actual
            return {"match": match, "score": self.weight if match else 0.0}

        # Compare as sets to ignore order
        expected_set = set(expected)
        actual_set = set(actual)
        match = expected_set == actual_set
        return {"match": match, "score": self.weight if match else 0.0}


# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the Jira tools
catalog.add_module(arcade_jira)


@tool_eval()
def list_sprints_for_boards_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the sprint planning list_sprints_for_boards tool."""
    suite = EvalSuite(
        name="Sprint Planning Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Test 1: Basic board name request
    suite.add_case(
        name="Get sprints using board name",
        user_message="Show me the sprints for the Development Team board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.3),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.15),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.15),
        ],
    )

    # Test 2: Board ID with numeric reference
    suite.add_case(
        name="Get sprints using numeric board ID",
        user_message="I need sprint data from board 123",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["123"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.3),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.15),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.15),
        ],
    )

    # Test 3: Mixed board identifiers
    suite.add_case(
        name="Get sprints using mixed board identifiers",
        user_message="Get sprint information for Development Team, board 456, and QA Testing",
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team", "456", "QA Testing"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.3),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.15),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.15),
        ],
    )

    # Test 4: Natural language limit with written numbers
    suite.add_case(
        name="Limit sprints with natural language",
        user_message="Show me the last ten sprints from the Marketing Board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Marketing Board"],
                    "sprints_per_board": 10,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.25),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 5: Pagination scenario with context
    suite.add_case(
        name="Pagination with previous context",
        user_message=("Now show me the next 15 sprints after those."),
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
            "\n"
            "Previous conversation context:\n"
            "User: 'Get 15 sprints from Development Team board'\n"
            "Tool call: list_sprints_for_boards(board_ids=['Development Team'], "
            "sprints_per_board=15, offset=0)\n"
            "Tool response: {\n"
            "  'boards': [{'id': 123, 'name': 'Development Team', 'type': 'scrum'}],\n"
            "  'sprints_by_board': {\n"
            "    '123': {\n"
            "      'board_info': {'id': 123, 'name': 'Development Team'},\n"
            "      'sprints': [/* 15 sprint objects returned */],\n"
            "      'total_sprints_returned': 15\n"
            "    }\n"
            "  },\n"
            "  'errors': []\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team"],
                    "sprints_per_board": 15,
                    "offset": 15,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.2),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 6: Active sprints using synonyms
    suite.add_case(
        name="Filter for active sprints with synonyms",
        user_message="What are the current running sprints on board 123?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["123"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["active"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 7: Multiple states with different terminology
    suite.add_case(
        name="Filter for upcoming and active sprints",
        user_message=(
            "Show me both the ongoing sprints and planned future ones from QA Testing board"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["QA Testing"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["active", "future"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 8: Completed sprints with synonym
    suite.add_case(
        name="Filter for completed sprints using synonym",
        user_message="Get all the finished sprints from Development Team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["closed"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 9: Date range filtering
    suite.add_case(
        name="Filter sprints by date range",
        user_message=(
            "Show sprints from Marketing Board between January 1st 2024 and February 29th 2024"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Marketing Board"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": "2024-01-01",
                    "end_date": "2024-02-29",
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.2),
            BinaryCritic(critic_field="end_date", weight=0.2),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 10: Start date only with natural language
    suite.add_case(
        name="Filter sprints from a start date",
        user_message="Get all sprints from board 999 starting from March 1st, 2024",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["999"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": "2024-03-01",
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.25),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 11: Specific date filtering
    suite.add_case(
        name="Filter sprints active on specific date",
        user_message=(
            "What sprints were running on February 14, 2024 in the Development Team board?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": "2024-02-14",
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.25),
        ],
    )

    # Test 12: Relative date - yesterday
    suite.add_case(
        name="Filter sprints with relative date - yesterday",
        user_message="Show me sprints that were active yesterday on QA Testing board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["QA Testing"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": "2024-03-14",
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.25),
        ],
    )

    # Test 13: Relative date - last month
    suite.add_case(
        name="Filter sprints from last month",
        user_message="Get sprints from last month for Marketing Board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Marketing Board"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": "2024-02-01",
                    "end_date": "2024-02-29",
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.2),
            BinaryCritic(critic_field="end_date", weight=0.2),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 14: Relative date - next week
    suite.add_case(
        name="Filter sprints for next week",
        user_message="What sprints will be running next week on board 123?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["123"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": "2024-03-16",
                    "end_date": "2024-03-22",
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            DatetimeCritic(
                critic_field="start_date",
                weight=0.2,
                tolerance=timedelta(
                    days=3
                ),  # Allow 3 days tolerance for "next week" interpretation
                max_difference=timedelta(
                    days=7
                ),  # Max 7 days difference still considered reasonable
            ),
            DatetimeCritic(
                critic_field="end_date",
                weight=0.2,
                tolerance=timedelta(
                    days=3
                ),  # Allow 3 days tolerance for "next week" interpretation
                max_difference=timedelta(
                    days=7
                ),  # Max 7 days difference still considered reasonable
            ),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 15: Complex natural language query
    suite.add_case(
        name="Complex natural language query",
        user_message=(
            "I want to see five completed sprints from the second page of results "
            "for Development Team and QA Testing boards"
        ),
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
            "\n"
            "Previous conversation context:\n"
            "User: 'Show me completed sprints for Development Team and QA Testing boards'\n"
            "Tool call: list_sprints_for_boards(board_ids=['Development Team', "
            "'QA Testing'], sprints_per_board=5, offset=0, state=['closed'])\n"
            "Tool response: {\n"
            "  'boards': [\n"
            "    {'id': 123, 'name': 'Development Team', 'type': 'scrum'},\n"
            "    {'id': 789, 'name': 'QA Testing', 'type': 'scrum'}\n"
            "  ],\n"
            "  'sprints_by_board': {\n"
            "    '123': {'board_info': {'id': 123}, 'sprints': [/* 5 closed sprints */]},\n"
            "    '789': {'board_info': {'id': 789}, 'sprints': [/* 5 closed sprints */]}\n"
            "  },\n"
            "  'errors': []\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team", "QA Testing"],
                    "sprints_per_board": 5,
                    "offset": 5,
                    "state": ["closed"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.2),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 16: Fuzzy board name matching with context
    suite.add_case(
        name="Fuzzy board name matching with context",
        user_message="Get sprints from the dev team board and marketing",
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team", "Marketing Board"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.3),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.2),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 17: Written numbers and ordinals
    suite.add_case(
        name="Natural language numbers with ordinals",
        user_message="Give me twenty sprints starting from the third page for board 789",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["789"],
                    "sprints_per_board": 20,
                    "offset": 40,  # Third page with 20 per page means offset of 40
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.15),
            BinaryCritic(critic_field="offset", weight=0.25),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 18: Alternative date formats
    suite.add_case(
        name="Alternative date format",
        user_message="Show sprints active on 03/10/2024 from Product Roadmap board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Product Roadmap"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": "2024-03-10",
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.25),
        ],
    )

    # Test 19: State synonyms - in progress
    suite.add_case(
        name="State filter using 'in progress' synonym",
        user_message="What sprints are currently in progress on Development Team board?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["active"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 20: State synonyms - upcoming/planned
    suite.add_case(
        name="State filter using 'upcoming' synonym",
        user_message="Show me upcoming sprints that haven't started yet from Marketing Board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Marketing Board"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["future"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 21: Very specific pagination context
    suite.add_case(
        name="Specific pagination with context",
        user_message=("Skip the first 30 sprints and show me 10 more from QA Testing board"),
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
            "\n"
            "Previous conversation context:\n"
            "User: 'Show me 10 sprints from QA Testing board'\n"
            "Tool call: list_sprints_for_boards(board_ids=['QA Testing'], "
            "sprints_per_board=10, offset=0)\n"
            "Tool response: {\n"
            "  'boards': [{'id': 789, 'name': 'QA Testing', 'type': 'scrum'}],\n"
            "  'sprints_by_board': {\n"
            "    '789': {'sprints': [/* 10 sprint objects 0-9 */]}\n"
            "  }\n"
            "}\n"
            "User: 'Show me the next 10 sprints'\n"
            "Tool call: list_sprints_for_boards(board_ids=['QA Testing'], "
            "sprints_per_board=10, offset=10)\n"
            "Tool response: {\n"
            "  'sprints_by_board': {'789': {'sprints': [/* 10 sprint objects 10-19 */]}}\n"
            "}\n"
            "User: 'Show me the next 10 sprints again'\n"
            "Tool call: list_sprints_for_boards(board_ids=['QA Testing'], "
            "sprints_per_board=10, offset=20)\n"
            "Tool response: {\n"
            "  'sprints_by_board': {'789': {'sprints': [/* 10 sprint objects 20-29 */]}}\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["QA Testing"],
                    "sprints_per_board": 10,
                    "offset": 30,
                    "state": None,
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.15),
            BinaryCritic(critic_field="offset", weight=0.25),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 22: Date with only end date
    suite.add_case(
        name="Filter sprints up to end date only",
        user_message="Show me all sprints that ended before April 1st, 2024 from board 456",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["456"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": None,
                    "start_date": None,
                    "end_date": "2024-04-01",
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.25),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.25),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 23: Multiple states with natural language
    suite.add_case(
        name="Multiple states with natural language",
        user_message=(
            "Get me all sprints that are either done or currently happening from board 999"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["999"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["closed", "active"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            StateListCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 24: Request for "other states" based on previous context
    suite.add_case(
        name="Request for remaining states with context",
        user_message="Now show me the other states for the same board",
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
            "\n"
            "Previous conversation context:\n"
            "User: 'Show me active sprints from Marketing Board'\n"
            "Tool call: list_sprints_for_boards(board_ids=['Marketing Board'], "
            "sprints_per_board=50, offset=0, state=['active'])\n"
            "Tool response: {\n"
            "  'boards': [{'id': 456, 'name': 'Marketing Board', 'type': 'scrum'}],\n"
            "  'sprints_by_board': {\n"
            "    '456': {\n"
            "      'board_info': {'id': 456, 'name': 'Marketing Board'},\n"
            "      'sprints': [\n"
            "        {'id': 101, 'name': 'Sprint 10', 'state': 'active'},\n"
            "        {'id': 98, 'name': 'Sprint 9', 'state': 'active'}\n"
            "      ],\n"
            "      'total_sprints_returned': 2\n"
            "    }\n"
            "  },\n"
            "  'errors': []\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Marketing Board"],
                    "sprints_per_board": 50,
                    "offset": 0,
                    "state": ["future", "closed"],
                    "start_date": None,
                    "end_date": None,
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.2),
            BinaryCritic(critic_field="sprints_per_board", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="state", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.1),
            BinaryCritic(critic_field="end_date", weight=0.1),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    # Test 25: Ultra complex test - all parameters with natural language
    suite.add_case(
        name="Ultra complex test with all parameters",
        user_message=(
            "I need fifteen completed and ongoing sprints from the second batch of results "
            "for both the development team and board 789, covering the period from "
            "February 1st through March 31st, 2024"
        ),
        system_message=(
            "You are an AI assistant that can interact with Jira to get sprint "
            "information from boards. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "Current date context: Today is 2024-03-15. "
            "\n"
            "Previous conversation context:\n"
            "User: 'Get 15 completed and ongoing sprints from development team and "
            "board 789 for Feb-March 2024'\n"
            "Tool call: list_sprints_for_boards(board_ids=['Development Team', '789'], "
            "sprints_per_board=15, offset=0, state=['closed', 'active'], "
            "start_date='2024-02-01', end_date='2024-03-31')\n"
            "Tool response: {\n"
            "  'boards': [\n"
            "    {'id': 123, 'name': 'Development Team', 'type': 'scrum'},\n"
            "    {'id': 789, 'name': 'QA Testing', 'type': 'scrum'}\n"
            "  ],\n"
            "  'sprints_by_board': {\n"
            "    '123': {'sprints': [/* 15 sprints with states closed/active */]},\n"
            "    '789': {'sprints': [/* 15 sprints with states closed/active */]}\n"
            "  },\n"
            "  'errors': []\n"
            "}\n"
            "In paginated results, 'second batch' typically means offset=15 when "
            "requesting 15 items per page."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_sprints_for_boards,
                args={
                    "board_ids": ["Development Team", "789"],
                    "sprints_per_board": 15,
                    "offset": 15,
                    "state": ["closed", "active"],
                    "start_date": "2024-02-01",
                    "end_date": "2024-03-31",
                    "specific_date": None,
                },
            ),
        ],
        critics=[
            BoardIdsCritic(critic_field="board_ids", weight=0.1),
            BinaryCritic(critic_field="sprints_per_board", weight=0.15),
            BinaryCritic(critic_field="offset", weight=0.15),
            StateListCritic(critic_field="state", weight=0.2),
            BinaryCritic(critic_field="start_date", weight=0.15),
            BinaryCritic(critic_field="end_date", weight=0.15),
            BinaryCritic(critic_field="specific_date", weight=0.1),
        ],
    )

    return suite

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.tools.boards import get_boards
from evals.jira_eval_critics import BoardIdentifiersCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the Jira tools
catalog.add_module(arcade_jira)


@tool_eval()
def get_boards_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the boards get_boards tool."""
    suite = EvalSuite(
        name="Boards Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Jira to get board "
            "information. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Test 1: List all boards with default pagination
    suite.add_case(
        name="List all boards with default parameters",
        user_message="Show me all available boards",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.35),
            BinaryCritic(critic_field="offset", weight=0.35),
        ],
    )

    # Test 2: List boards with custom pagination
    suite.add_case(
        name="List boards with custom pagination parameters",
        user_message="Get the first 20 boards",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 20,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.35),
            BinaryCritic(critic_field="offset", weight=0.35),
        ],
    )

    # Test 3: Get specific board by name
    suite.add_case(
        name="Get board by name",
        user_message="Get the Development Team board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Development Team"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 4: Get board by numeric ID
    suite.add_case(
        name="Get board by numeric ID",
        user_message="Show me board 123",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["123"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 5: Get multiple boards with mixed identifiers
    suite.add_case(
        name="Get multiple boards with mixed identifiers",
        user_message=(
            "Get Development Team, 456, and QA Testing boards with the newest available "
            "data on jira"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Development Team", "456", "QA Testing"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 6: Pagination scenario with context - second page
    suite.add_case(
        name="Pagination - second page of results",
        user_message="Now show me the next 25 boards",
        system_message=(
            "You are an AI assistant that can interact with Jira to get board "
            "information. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "\n"
            "Previous conversation context:\n"
            "User: 'Show me 25 boards'\n"
            "Tool call: get_boards(board_identifiers=None, limit=25, offset=0)\n"
            "Tool response: {\n"
            "  'boards': [/* 25 board objects returned */],\n"
            "  'total_boards_returned': 25,\n"
            "  'is_last_page': false,\n"
            "  'offset': 0,\n"
            "  'limit': 25\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 25,
                    "offset": 25,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.375),
            BinaryCritic(critic_field="offset", weight=0.375),
        ],
    )

    # Test 7: Natural language limit with written numbers
    suite.add_case(
        name="Natural language limit with written numbers",
        user_message="Show me ten boards with the newest available data on jira",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.35),
            BinaryCritic(critic_field="offset", weight=0.35),
        ],
    )

    # Test 8: Fuzzy board name matching
    suite.add_case(
        name="Fuzzy board name matching",
        user_message="Get the marketing and dev team boards",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Marketing Board", "Development Team"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 9: Specific pagination with skip instruction
    suite.add_case(
        name="Specific pagination with skip instruction",
        user_message="Skip the first 15 boards and show me 30 more",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 30,
                    "offset": 15,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.375),
            BinaryCritic(critic_field="offset", weight=0.375),
        ],
    )

    # Test 10: Written numbers and ordinals for pagination
    suite.add_case(
        name="Written numbers and ordinals for pagination",
        user_message="Give me fifteen boards starting from the third page",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 15,
                    "offset": 30,  # Third page with 15 per page means offset of 30
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.375),
            BinaryCritic(critic_field="offset", weight=0.375),
        ],
    )

    # Test 11: Board identifiers with specific context
    suite.add_case(
        name="Board identifiers with specific context",
        user_message="Show me details for boards 999 and the QA Testing one",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["999", "QA Testing"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 12: Multiple pages context
    suite.add_case(
        name="Multiple pages context with specific offset",
        user_message="Now get the next batch",
        system_message=(
            "You are an AI assistant that can interact with Jira to get board "
            "information. "
            "You have access to these example boards: "
            "- 'Development Team' (ID: 123) - Scrum board "
            "- 'Marketing Board' (ID: 456) - Scrum board "
            "- 'QA Testing' (ID: 789) - Scrum board "
            "- Board ID 999 called 'Product Roadmap' "
            "\n"
            "Previous conversation context:\n"
            "User: 'Show me 10 boards'\n"
            "Tool call: get_boards(board_identifiers=None, limit=10, offset=0)\n"
            "Tool response: {\n"
            "  'boards': [/* 10 board objects returned */],\n"
            "  'total_boards_returned': 10\n"
            "}\n"
            "User: 'Show me the next 10 boards'\n"
            "Tool call: get_boards(board_identifiers=None, limit=10, offset=10)\n"
            "Tool response: {\n"
            "  'boards': [/* 10 board objects returned */],\n"
            "  'total_boards_returned': 10\n"
            "}"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 10,
                    "offset": 20,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.375),
            BinaryCritic(critic_field="offset", weight=0.375),
        ],
    )

    # Test 13: Large limit request
    suite.add_case(
        name="Large limit request",
        user_message="Show me all boards, up to 100 if needed",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 100,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.35),
            BinaryCritic(critic_field="offset", weight=0.35),
        ],
    )

    # Test 14: Single board by partial name
    suite.add_case(
        name="Single board by partial name",
        user_message="Get the Product Roadmap board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Product Roadmap"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 15: Complex scenario with multiple boards and custom limit
    suite.add_case(
        name="Complex scenario with multiple boards",
        user_message=(
            "Get Development Team, Marketing Board, and board 789, but only show up to "
            "25 results total"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Development Team", "Marketing Board", "789"],
                    "limit": 25,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.35),
            BinaryCritic(critic_field="limit", weight=0.325),
            BinaryCritic(critic_field="offset", weight=0.325),
        ],
    )

    # Test 16: Alternative phrasing for listing boards
    suite.add_case(
        name="Alternative phrasing for listing boards",
        user_message=(
            "What boards are available? Show me a list with the newest available data on jira"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.35),
            BinaryCritic(critic_field="offset", weight=0.35),
        ],
    )

    # Test 17: Board names with special handling
    suite.add_case(
        name="Board names with special handling",
        user_message="Show me the dev and qa boards with the newest available data on jira",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Development Team", "QA Testing"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 18: Pagination with larger page size
    suite.add_case(
        name="Pagination with larger page size",
        user_message="Get the next 50 boards after the first 20",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": None,
                    "limit": 50,
                    "offset": 20,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="board_identifiers", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.375),
            BinaryCritic(critic_field="offset", weight=0.375),
        ],
    )

    # Test 19: Mixed natural language request
    suite.add_case(
        name="Mixed natural language request",
        user_message="I want to see boards 123 and 456, plus the QA Testing board",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["123", "456", "QA Testing"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    # Test 20: Request with emphasis on specific boards
    suite.add_case(
        name="Request with emphasis on specific boards",
        user_message="Find the Marketing Board and Development Team boards specifically",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_boards,
                args={
                    "board_identifiers": ["Marketing Board", "Development Team"],
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BoardIdentifiersCritic(critic_field="board_identifiers", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.3),
        ],
    )

    return suite

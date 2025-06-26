"""
Comprehensive evaluation suite for Linear user management tools.
"""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_linear
from arcade_linear.tools.users import get_users
from arcade_linear.tools.issues import search_issues

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def users_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for user and assignment management tools"""
    suite = EvalSuite(
        name="Users Management Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear users and assignments."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all users in the workspace
    suite.add_case(
        name="Get all users in workspace",
        user_message="Show me all users in the workspace",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_users,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: Find users in the Frontend team
    suite.add_case(
        name="Get team users",
        user_message="Find users in the Frontend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_users,
                args={
                    "team": "Frontend",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me all users in the test team
    suite.add_case(
        name="Get test team members",
        user_message="Show me all users in the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_users,
                args={
                    "team": "test",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me active users only
    suite.add_case(
        name="Get active users",
        user_message="Show me active users only",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_users,
                args={
                    "include_guests": False,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="include_guests", weight=1.0),
        ],
    )

    # Eval Prompt: Find all my assigned issues
    suite.add_case(
        name="Get my assigned issues",
        user_message="Find all my assigned issues",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "me",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=1.0),
        ],
    )

    # Eval Prompt: Find all issues assigned to John
    suite.add_case(
        name="Get user assigned issues",
        user_message="Find all issues assigned to John",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "John",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=1.0),
        ],
    )

    # Eval Prompt: Show my high priority tasks
    suite.add_case(
        name="Get my high priority issues",
        user_message="Show my high priority tasks",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "me",
                    "priority": "high",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=0.5),
            BinaryCritic(critic_field="priority", weight=0.5),
        ],
    )

    # Eval Prompt: Find all unassigned issues
    suite.add_case(
        name="Get unassigned issues",
        user_message="Find all unassigned issues",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "unassigned",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=1.0),
        ],
    )

    # Eval Prompt: Find all issues assigned to shub
    suite.add_case(
        name="Get specific user's issues",
        user_message="Find all issues assigned to shub",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "shub",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=1.0),
        ],
    )

    return suite 
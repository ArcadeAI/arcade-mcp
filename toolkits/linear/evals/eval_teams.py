"""
Evaluation suite for Linear get_teams tool.
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
from arcade_linear.tools.teams import get_teams

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def teams_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_teams tool"""
    suite = EvalSuite(
        name="Teams Management Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear teams and organizational structure."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all teams in our workspace
    suite.add_case(
        name="Get all teams in workspace",
        user_message="Show me all teams in our workspace",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: Which teams were created in the last month?
    suite.add_case(
        name="Find recently created teams",
        user_message="Which teams were created in the last month?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "created_after": "last month",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="created_after", weight=1.0),
        ],
    )

    # Eval Prompt: Show me teams created this week
    suite.add_case(
        name="Find teams created this week",
        user_message="Show me teams created this week",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "created_after": "this week",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="created_after", weight=1.0),
        ],
    )

    # Eval Prompt: Which teams were created in the last 7 days?
    suite.add_case(
        name="Find teams created in last 7 days",
        user_message="Which teams were created in the last 7 days?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "created_after": "last 7 days",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="created_after", weight=1.0),
        ],
    )

    # Eval Prompt: Find teams that aren't archived
    suite.add_case(
        name="Get active teams only",
        user_message="Find teams that aren't archived",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "include_archived": False,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="include_archived", weight=1.0),
        ],
    )

    # Eval Prompt: Find teams that have "Engineering" in their name
    suite.add_case(
        name="Search teams by name",
        user_message='Find teams that have "Engineering" in their name',
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "team_name": "Engineering",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="team_name", weight=1.0),
        ],
    )

    # Eval Prompt: Show me the Frontend team details
    suite.add_case(
        name="Get specific team by name",
        user_message="Show me the Frontend team details",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "team_name": "Frontend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_name", weight=1.0),
        ],
    )

    return suite

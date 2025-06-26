"""
Comprehensive evaluation suite for Linear team management tools.
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
from arcade_linear.tools.users import get_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def teams_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for team management tools"""
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

    # Eval Prompt: Who is in the "test" team?
    suite.add_case(
        name="Get test team members",
        user_message="Who is in the \"test\" team?",
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

    # Eval Prompt: Find teams that have "Engineering" in their name
    suite.add_case(
        name="Search teams by name",
        user_message="Find teams that have \"Engineering\" in their name",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_teams,
                args={
                    "name_filter": "Engineering",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="name_filter", weight=1.0),
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
                    "name_filter": "Frontend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="name_filter", weight=1.0),
        ],
    )

    return suite 
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.teams import get_team

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_team_eval_suite() -> EvalSuite:
    """Create an evaluation suite for getting a team tool in MS Teams."""
    suite = EvalSuite(
        name="Getting a Team Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get a team by ID",
        user_message="Get the team with ID 'team_111'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_team,
                args={
                    "team_id": "team_111",
                    "team_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id", weight=0.5),
            BinaryCritic(critic_field="team_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get a team by name",
        user_message="Get the team with name 'Team Foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_team,
                args={
                    "team_id": None,
                    "team_name": "Team Foobar",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id", weight=0.5),
            BinaryCritic(critic_field="team_name", weight=0.5),
        ],
    )

    return suite

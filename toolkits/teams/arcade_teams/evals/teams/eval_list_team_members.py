from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.teams import list_team_members

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def list_team_members_eval_suite() -> EvalSuite:
    """Create an evaluation suite for listing team members tool in MS Teams."""
    suite = EvalSuite(
        name="Listing Team Members Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List members of a team by ID",
        user_message="List the members of the team with ID 'team_111'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_team_members,
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
        name="List members of a team by name",
        user_message="List the members of the team with name 'Team Foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_team_members,
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

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.teams import search_team_members

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_team_members_eval_suite() -> EvalSuite:
    """Create an evaluation suite for searching team members tool in MS Teams."""
    suite = EvalSuite(
        name="Searching Team Members Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search members of a team by ID",
        user_message="Search for 'foobar' in the members of the team with ID 'team_111'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_team_members,
                args={
                    "member_name_starts_with": "foobar",
                    "team_id": "team_111",
                    "team_name": None,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="member_name_starts_with", weight=0.3),
            BinaryCritic(critic_field="team_id", weight=0.3),
            BinaryCritic(critic_field="team_name", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search members of a team by team name with custom limit",
        user_message="Search for 10 members with 'foobar' in the members of the 'Engineering' team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_team_members,
                args={
                    "member_name_starts_with": "foobar",
                    "team_id": None,
                    "team_name": "Engineering",
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="member_name_starts_with", weight=0.3),
            BinaryCritic(critic_field="team_id", weight=0.1),
            BinaryCritic(critic_field="team_name", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    return suite

import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.teams import search_teams

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_teams_eval_suite() -> EvalSuite:
    """Create an evaluation suite for searching teams tool in MS Teams."""
    suite = EvalSuite(
        name="Searching Teams Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search teams by name",
        user_message="Search for teams with 'foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_teams,
                args={
                    "team_name_starts_with": "foobar",
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_name_starts_with", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Search teams by name with custom limit",
        user_message="Search for 20 teams with 'foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_teams,
                args={
                    "team_name_starts_with": "foobar",
                    "limit": 20,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_name_starts_with", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Search teams by name with custom limit and pagination",
        user_message="Get the next 2 teams",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_teams,
                args={
                    "team_name_starts_with": "foobar",
                    "limit": 2,
                    "next_page_token": "RFNwdAIAAQAAAD8489594356YNW45824958AAA",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_name_starts_with", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
        additional_messages=[
            {"role": "user", "content": "Search 2 teams with 'foobar'"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Teams_SearchTeams",
                            "arguments": json.dumps({
                                "team_name_starts_with": "foobar",
                                "limit": 2,
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 2,
                    "teams": [
                        {
                            "id": "team_111",
                            "display_name": "Team Foobar",
                            "description": "This is team foobar",
                        },
                        {
                            "id": "team_222",
                            "display_name": "Foobar We Are",
                            "description": "We are all foobar!",
                        },
                    ],
                    "pagination": {
                        "is_last_page": False,
                        "next_page_token": "RFNwdAIAAQAAAD8489594356YNW45824958AAA",
                    },
                }),
                "tool_call_id": "call_1",
                "name": "Teams_SearchTeams",
            },
            {
                "role": "assistant",
                "content": (
                    "Here are the first 2 teams with 'foobar' in your organization:\n\n"
                    "1. **Team:** Team Foobar  \n   **Description:** This is team foobar\n\n"
                    "2. **Team:** Foobar We Are  \n   **Description:** We are all foobar!"
                ),
            },
        ],
    )

    return suite

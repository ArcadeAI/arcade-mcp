import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_asana
from arcade_asana.tools import get_team_by_id, list_teams_the_current_user_is_a_member_of

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def get_team_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get team by id eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get team by id",
        user_message="Get the team with ID 1234567890.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_team_by_id,
                args={
                    "team_id": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="team_id", weight=1),
        ],
    )

    return suite


@tool_eval()
def list_teams_the_current_user_is_a_member_of_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="list teams the current user is a member of eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List teams the current user is a member of",
        user_message="List the teams the current user is a member of.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={},
            ),
        ],
        rubric=rubric,
        critics=[],
    )

    suite.add_case(
        name="List teams I am a member of",
        user_message="List the teams I'm a member of.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={},
            ),
        ],
        rubric=rubric,
        critics=[],
    )

    suite.add_case(
        name="List teams I am a member of",
        user_message="What teams am I a member of in asana?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={},
            ),
        ],
        rubric=rubric,
        critics=[],
    )

    suite.add_case(
        name="List teams the current user is a member of filtering by workspace",
        user_message="List the teams the current user is a member of in the workspace 1234567890.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={
                    "workspace_ids": ["1234567890"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="workspace_ids", weight=1),
        ],
    )

    suite.add_case(
        name="List up to 5 teams the current user is a member of filtering by workspace",
        user_message="List up to 5 teams the current user is a member of in the workspace 1234567890.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={
                    "workspace_ids": ["1234567890"],
                    "limit": 5,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="workspace_ids", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="List teams with pagination",
        user_message="Show me the next 2 teams.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={
                    "limit": 2,
                    "offset": "abc123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="offset", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 teams I'm a member of in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListTeamsTheCurrentUserIsAMemberOf",
                            "arguments": '{"limit":2}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 1,
                    "next_page": {
                        "has_more_results": True,
                        "next_page_token": "abc123",
                    },
                    "teams": [
                        {
                            "id": "1234567890",
                            "name": "Team Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Team World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListTeamsTheCurrentUserIsAMemberOf",
            },
            {
                "role": "assistant",
                "content": "Here are two teams you're a member of in Asana:\n\n1. Team Hello\n2. Team World",
            },
        ],
    )

    suite.add_case(
        name="List teams with pagination changing the limit",
        user_message="Show me the next 5 teams.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_teams_the_current_user_is_a_member_of,
                args={
                    "limit": 5,
                    "offset": "abc123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 teams I'm a member of in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListTeamsTheCurrentUserIsAMemberOf",
                            "arguments": '{"limit":2}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 1,
                    "next_page": {
                        "has_more_results": True,
                        "next_page_token": "abc123",
                    },
                    "teams": [
                        {
                            "id": "1234567890",
                            "name": "Team Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "Team World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListTeamsTheCurrentUserIsAMemberOf",
            },
            {
                "role": "assistant",
                "content": "Here are two teams you're a member of in Asana:\n\n1. Team Hello\n2. Team World",
            },
        ],
    )

    return suite

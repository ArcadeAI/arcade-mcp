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
from arcade_asana.tools import get_user_by_id, list_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def get_user_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get user by id eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get user by id",
        user_message="Get the user with ID 1234567890.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_user_by_id,
                args={
                    "user_id": "1234567890",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="user_id", weight=0.1),
        ],
    )

    return suite


@tool_eval()
def list_users_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="list users eval suite",
        system_message=(
            "You are an AI assistant with access to Asana tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List users",
        user_message="List the users in Asana.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "workspace_id": None,
                    "limit": 100,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="workspace_id", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.4),
        ],
    )

    suite.add_case(
        name="List users filtering by workspace",
        user_message="List the users in the workspace 1234567890.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "workspace_id": "1234567890",
                    "limit": 100,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="workspace_id", weight=0.8),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="List users with limit",
        user_message="List up to 5 users.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "limit": 5,
                    "workspace_id": None,
                    "offset": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.8),
            BinaryCritic(critic_field="workspace_id", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="List users with pagination",
        user_message="Show me the next 2 users.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "workspace_id": None,
                    "limit": 2,
                    "offset": 2,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.45),
            BinaryCritic(critic_field="offset", weight=0.45),
            BinaryCritic(critic_field="workspace_id", weight=0.1),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 users in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListUsers",
                            "arguments": '{"limit":2}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 2,
                    "users": [
                        {
                            "id": "1234567890",
                            "name": "User Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "User World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListUsers",
            },
            {
                "role": "assistant",
                "content": "Here are two users in Asana:\n\n1. User Hello\n2. User World",
            },
        ],
    )

    suite.add_case(
        name="List users with pagination changing the limit",
        user_message="Show me the next 5 users.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "workspace_id": None,
                    "limit": 5,
                    "offset": 2,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.45),
            BinaryCritic(critic_field="offset", weight=0.45),
            BinaryCritic(critic_field="workspace_id", weight=0.1),
        ],
        additional_messages=[
            {"role": "user", "content": "Show me 2 users in Asana."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Asana_ListUsers",
                            "arguments": '{"limit":2}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "count": 2,
                    "users": [
                        {
                            "id": "1234567890",
                            "name": "User Hello",
                        },
                        {
                            "id": "1234567891",
                            "name": "User World",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Asana_ListUsers",
            },
            {
                "role": "assistant",
                "content": "Here are two users in Asana:\n\n1. User Hello\n2. User World",
            },
        ],
    )

    return suite

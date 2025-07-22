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
from arcade_teams.tools.users import list_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def list_users_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools listing users in Teams."""
    suite = EvalSuite(
        name="Teams Users Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List users",
        user_message="List all users in my organization",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "limit": 100,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
    )

    suite.add_case(
        name="List users with custom limit",
        user_message="List 10 users in my organization",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
    )

    suite.add_case(
        name="List users with custom limit and pagination",
        user_message="Get the next 2 users",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={
                    "limit": 2,
                    "offset": 2,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="offset", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "List 2 users in my organization"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [  # type: ignore[dict-item]
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Teams_ListUsers",
                            "arguments": json.dumps({
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
                    "users": [
                        {
                            "id": "user_111",
                            "display_name": "John Foo",
                            "email": "john.foo@example.com",
                        },
                        {
                            "id": "user_222",
                            "display_name": "Jane Bar",
                            "email": "jane.bar@example.com",
                        },
                    ],
                    "pagination": {
                        "is_last_page": False,
                        "limit": 2,
                        "current_offset": 0,
                        "next_offset": 2,
                    },
                }),
                "tool_call_id": "call_1",
                "name": "Teams_ListUsers",
            },
            {
                "role": "assistant",
                "content": (
                    "Here are the first 2 users in your organization:\n\n"
                    "1. **User:** John Foo  \n   **Email:** john.foo@example.com\n\n"
                    "2. **User:** Jane Bar  \n   **Email:** jane.bar@example.com"
                ),
            },
        ],
    )

    return suite

import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.users import get_user_info_by_id, list_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def get_user_info_by_id_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting user info by id."""
    suite = EvalSuite(
        name="Slack Users Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to get information about users.",
        catalog=catalog,
        rubric=rubric,
    )

    expected_user_id = "U12345"

    get_user_info_by_id_eval_cases = [
        (
            "get user info by id",
            f"What is the name of the user with id {expected_user_id}?",
        ),
        (
            "get user info by id",
            f"get information about the user with id {expected_user_id}",
        ),
    ]

    for name, user_message in get_user_info_by_id_eval_cases:
        suite.add_case(
            name=name,
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_user_info_by_id,
                    args={"user_id": expected_user_id},
                )
            ],
            critics=[BinaryCritic(critic_field="user_id", weight=1.0)],
        )

    return suite


@tool_eval()
def list_users_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools listing users."""
    suite = EvalSuite(
        name="Slack Users Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to get information about users.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="list users",
        user_message="list all users on my slack workspace",
        expected_tool_calls=[
            ExpectedToolCall(func=list_users, args={}),
        ],
    )

    suite.add_case(
        name="list users without bots",
        user_message="list all users on my slack workspace, except bots",
        expected_tool_calls=[
            ExpectedToolCall(func=list_users, args={"exclude_bots": True}),
        ],
        critics=[
            BinaryCritic(critic_field="exclude_bots", weight=1.0),
        ],
    )

    suite.add_case(
        name="list 10 users without bots",
        user_message="get a list of 10 users on my slack workspace, except bots",
        expected_tool_calls=[
            ExpectedToolCall(func=list_users, args={"exclude_bots": True, "limit": 10}),
        ],
        critics=[
            BinaryCritic(critic_field="exclude_bots", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="test list users with pagination",
        user_message="get the next 5 users",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_users,
                args={"limit": 5, "next_cursor": "dXNlcjpVsDjzOTZGVDlQRA=="},
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.5),
            BinaryCritic(critic_field="next_cursor", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "get a list of 2 users from my slack workspace"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "Slack_ListUsers", "arguments": '{"limit":2}'},
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "next_cursor": "dXNlcjpVsDjzOTZGVDlQRA==",
                    "users": [
                        {
                            "display_name": "John Doe",
                            "email": "john.doe@acme.com",
                            "id": "U123",
                            "is_bot": False,
                            "name": "john.doe",
                            "real_name": "John Doe",
                            "timezone": "America/Los_Angeles",
                        },
                        {
                            "display_name": "Jane Doe",
                            "email": "jane.doe@acme.com",
                            "id": "U124",
                            "is_bot": False,
                            "name": "jane.doe",
                            "real_name": "Jane Doe",
                            "timezone": "America/Los_Angeles",
                        },
                    ],
                }),
                "tool_call_id": "call_1",
                "name": "Slack_ListUsers",
            },
            {
                "role": "assistant",
                "content": "Here are two users from your Slack workspace:\n\n1. **John Doe**\n   - Display Name: John Doe\n   - Email: john.doe@acme.com\n   - Timezone: America/Los_Angeles\n\n2. **Jane Doe**\n   - Display Name: Jane Doe\n   - Email: jane.doe@acme.com\n   - Timezone: America/Los_Angeles\n\nIf you need more information or additional users, feel free to ask!",
            },
        ],
    )

    return suite

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
from arcade_teams.tools.search import search_messages

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_messages_eval_suite() -> EvalSuite:
    """Create an evaluation suite for searching messages tool in MS Teams."""
    suite = EvalSuite(
        name="Searching Messages Tool Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search messages by keywords",
        user_message="Search messages about 'foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_messages,
                args={
                    "keywords": "foobar",
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="offset", weight=0.2),
        ],
    )

    suite.add_case(
        name="Search messages by keywords with custom limit",
        user_message="Search 10 messages about 'foobar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_messages,
                args={
                    "keywords": "foobar",
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="offset", weight=0.2),
        ],
    )

    suite.add_case(
        name="Search messages by keywords with custom limit and pagination",
        user_message="Get the next 2 messages",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_messages,
                args={
                    "keywords": "foobar",
                    "limit": 2,
                    "offset": 2,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="offset", weight=0.2),
        ],
        additional_messages=[
            {"role": "user", "content": "Search 2 messages about 'foobar'"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Teams_SearchMessages",
                            "arguments": json.dumps({
                                "keywords": "foobar",
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
                    "messages": [
                        {
                            "id": "message_111",
                            "content": "Hello, foobar world!",
                        },
                        {
                            "id": "message_222",
                            "content": "This is message foobar",
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
                "name": "Teams_SearchMessages",
            },
            {
                "role": "assistant",
                "content": (
                    "Here are the first 2 messages with 'foobar':\n\n"
                    "1. **Message:** Hello, foobar world!\n\n"
                    "2. **Message:** This is message foobar"
                ),
            },
        ],
    )

    return suite

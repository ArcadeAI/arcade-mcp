from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.chat import get_chat_messages

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_chat_messages_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting messages in Teams chats."""
    suite = EvalSuite(
        name="Teams Chat Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get messages in chat by the chat id",
        user_message="Get the messages in the chat with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": "1234567890",
                    "user_ids": None,
                    "user_names": None,
                    "start_datetime": None,
                    "end_datetime": None,
                    "limit": 50,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.5),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.1),
            BinaryCritic(critic_field="start_datetime", weight=0.1),
            BinaryCritic(critic_field="end_datetime", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get messages in chat by user ids",
        user_message=("Get the messages in the chat I have with the users ids 12345 and 67890"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": None,
                    "user_ids": ["12345", "67890"],
                    "user_names": None,
                    "start_datetime": None,
                    "end_datetime": None,
                    "limit": 50,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.5),
            BinaryCritic(critic_field="user_names", weight=0.1),
            BinaryCritic(critic_field="start_datetime", weight=0.1),
            BinaryCritic(critic_field="end_datetime", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get latest 10 messages in individual chat by user name",
        user_message="What were the last 10 messages I exchanged with john smith?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith"],
                    "start_datetime": None,
                    "end_datetime": None,
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.4),
            BinaryCritic(critic_field="start_datetime", weight=0.1),
            BinaryCritic(critic_field="end_datetime", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get latest 10 messages in group chat by user names",
        user_message=(
            "What were the last 10 messages I exchanged in the "
            "group chat with john smith and jane foo?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                    "start_datetime": None,
                    "end_datetime": None,
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.4),
            BinaryCritic(critic_field="start_datetime", weight=0.1),
            BinaryCritic(critic_field="end_datetime", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get latest 10 messages in chat by user names with absolute date range",
        user_message=(
            "What 10 messages I exchanged in the group chat with john smith and jane foo "
            "between 2025-07-01 and 2025-07-31?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                    "start_datetime": "2025-07-01",
                    "end_datetime": "2025-07-31",
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.2),
            BinaryCritic(critic_field="start_datetime", weight=0.2),
            BinaryCritic(critic_field="end_datetime", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get latest 10 messages in chat by user names with relative date range",
        user_message=(
            "What 10 messages I exchanged in the group chat with john smith and jane foo "
            "last month?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_messages,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                    "start_datetime": "2025-06-01",
                    "end_datetime": "2025-06-30",
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.2),
            BinaryCritic(critic_field="start_datetime", weight=0.2),
            BinaryCritic(critic_field="end_datetime", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    return suite

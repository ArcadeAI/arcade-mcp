from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.chat import send_message_to_chat

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def send_message_to_chat_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools sending messages to chats in Teams."""
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
        name="Send message to a group chat by chat id",
        user_message="Send a message to the chat with id 12345 saying hello",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_chat,
                args={
                    "message": "hello",
                    "chat_id": "12345",
                    "user_ids": None,
                    "user_names": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="chat_id", weight=0.4),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.1),
        ],
    )

    suite.add_case(
        name="Send message to a group chat by user names",
        user_message="Send a message to john smith and jane foo saying hello",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_chat,
                args={
                    "message": "hello",
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.4),
        ],
    )

    suite.add_case(
        name="Send message to a group chat by user ids",
        user_message="Send a message to the users 12345 and 67890 saying hello",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_chat,
                args={
                    "message": "hello",
                    "chat_id": None,
                    "user_ids": ["12345", "67890"],
                    "user_names": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.4),
            BinaryCritic(critic_field="user_names", weight=0.1),
        ],
    )

    suite.add_case(
        name="Send message to an individual chat by user name",
        user_message="Send a message to jane foo saying hello",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_chat,
                args={
                    "message": "hello",
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["jane foo"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.4),
        ],
    )

    suite.add_case(
        name="Send message to an individual chat by user id",
        user_message="Send a message to the user 12345 saying hello",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_chat,
                args={
                    "message": "hello",
                    "chat_id": None,
                    "user_ids": ["12345"],
                    "user_names": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="chat_id", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="user_names", weight=0.4),
        ],
    )

    return suite

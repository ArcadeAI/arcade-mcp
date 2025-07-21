from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.chat import get_chat_metadata

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_chat_metadata_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting metadata about Teams chats."""
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
        name="Get metadata about a chat by the chat id",
        user_message="Get metadata about the chat with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_metadata,
                args={
                    "chat_id": "1234567890",
                    "user_ids": None,
                    "user_names": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.6),
            BinaryCritic(critic_field="user_ids", weight=0.2),
            BinaryCritic(critic_field="user_names", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get metadata about a chat by user ids",
        user_message=("Get metadata about the chat I have with the users ids 12345 and 67890"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_metadata,
                args={
                    "chat_id": None,
                    "user_ids": ["12345", "67890"],
                    "user_names": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.6),
            BinaryCritic(critic_field="user_names", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get metadata about a group chat by user names",
        user_message=(
            "Get metadata about the group chat I have with the users john smith and jane foo"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_metadata,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.2),
            BinaryCritic(critic_field="user_names", weight=0.6),
        ],
    )

    suite.add_case(
        name="Get metadata about an individual chat by the user name",
        user_message="Get metadata about the chat I have with the user john smith",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_chat_metadata,
                args={
                    "chat_id": None,
                    "user_ids": None,
                    "user_names": ["john smith"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="chat_id", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.2),
            BinaryCritic(critic_field="user_names", weight=0.6),
        ],
    )

    return suite

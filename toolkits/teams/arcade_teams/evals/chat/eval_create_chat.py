from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.chat import create_chat

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def create_chat_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools creating chats in Teams."""
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
        name="Create a group chat with two users by user names",
        user_message="Create a group chat with the users john smith and jane foo",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_chat,
                args={
                    "user_ids": None,
                    "user_names": ["john smith", "jane foo"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="user_ids", weight=0.2),
            BinaryCritic(critic_field="user_names", weight=0.8),
        ],
    )

    suite.add_case(
        name="Create a group chat with two users by user ids",
        user_message="Create a group chat with the users 12345 and 67890",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_chat,
                args={
                    "user_ids": ["12345", "67890"],
                    "user_names": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="user_ids", weight=0.8),
            BinaryCritic(critic_field="user_names", weight=0.2),
        ],
    )

    suite.add_case(
        name="Create a group chat with two users by mixed user id and user name",
        user_message="Create a group chat with the users 12345 and jane foo",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_chat,
                args={
                    "user_ids": ["12345"],
                    "user_names": ["jane foo"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="user_ids", weight=0.5),
            BinaryCritic(critic_field="user_names", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create an individual chat by user id",
        user_message="Create an chat with the user 12345",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_chat,
                args={
                    "user_ids": ["12345"],
                    "user_names": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="user_ids", weight=0.8),
            BinaryCritic(critic_field="user_names", weight=0.2),
        ],
    )

    suite.add_case(
        name="Create an individual chat by user name",
        user_message="Create a chat with the user jane foo",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_chat,
                args={
                    "user_ids": None,
                    "user_names": ["jane foo"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="user_ids", weight=0.2),
            BinaryCritic(critic_field="user_names", weight=0.8),
        ],
    )

    return suite

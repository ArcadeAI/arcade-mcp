from datetime import timedelta

from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.critics import RelativeTimeBinaryCritic
from arcade_slack.tools.chat import get_messages

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def get_messages_in_direct_message_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting messages in direct messages."""
    suite = EvalSuite(
        name="Slack Chat Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    no_arguments_user_messages_by_username = [
        "what are the latest messages I exchanged with janedoe",
        "show my messages with janedoe on Slack",
        "get the messages I exchanged with janedoe",
        "get the message history with janedoe",
    ]

    for i, user_message in enumerate(no_arguments_user_messages_by_username):
        suite.add_case(
            name=f"{user_message} [{i}]",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages,
                    args={
                        "conversation_id": None,
                        "channel_name": None,
                        "user_ids": None,
                        "usernames": ["janedoe"],
                        "emails": None,
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=0.1),
                BinaryCritic(critic_field="channel_name", weight=0.1),
                BinaryCritic(critic_field="user_ids", weight=0.1),
                BinaryCritic(critic_field="usernames", weight=0.6),
                BinaryCritic(critic_field="emails", weight=0.1),
            ],
        )

    no_arguments_user_messages_by_email = [
        "what are the latest messages I exchanged with jane.doe@acme.com",
        "show my messages with jane.doe@acme.com on Slack",
    ]

    for i, user_message in enumerate(no_arguments_user_messages_by_email):
        suite.add_case(
            name=f"{user_message} [{i}]",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages,
                    args={
                        "conversation_id": None,
                        "channel_name": None,
                        "user_ids": None,
                        "usernames": None,
                        "emails": ["jane.doe@acme.com"],
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=0.1),
                BinaryCritic(critic_field="channel_name", weight=0.1),
                BinaryCritic(critic_field="user_ids", weight=0.1),
                BinaryCritic(critic_field="usernames", weight=0.1),
                BinaryCritic(critic_field="emails", weight=0.6),
            ],
        )

    suite.add_case(
        name="get messages in direct conversation by username (on a specific date)",
        user_message="get the messages I exchanged with janedoe on 2025-01-31",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": ["janedoe"],
                    "emails": None,
                    "oldest_datetime": "2025-01-31 00:00:00",
                    "latest_datetime": "2025-01-31 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.2),
            BinaryCritic(critic_field="emails", weight=0.1),
            DatetimeCritic(
                critic_field="oldest_datetime", weight=0.2, max_difference=timedelta(minutes=2)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=0.2, max_difference=timedelta(minutes=2)
            ),
        ],
    )

    suite.add_case(
        name="get messages in direct conversation by email (on a specific date)",
        user_message="get the messages I exchanged with jane.doe@acme.com on 2025-01-31",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": ["jane.doe@acme.com"],
                    "oldest_datetime": "2025-01-31 00:00:00",
                    "latest_datetime": "2025-01-31 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.2),
            DatetimeCritic(
                critic_field="oldest_datetime", weight=0.2, max_difference=timedelta(minutes=2)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=0.2, max_difference=timedelta(minutes=2)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by username (2 days ago)",
        user_message="Get the messages I exchanged with janedoe starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": ["janedoe"],
                    "emails": None,
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.3),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    return suite

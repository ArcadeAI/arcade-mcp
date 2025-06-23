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
from arcade_slack.tools.chat import get_messages_in_multi_person_dm_conversation_by_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def get_messages_in_multi_person_direct_message_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting messages in multi-person direct messages."""
    suite = EvalSuite(
        name="Slack Chat Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    no_arguments_user_messages_by_username = [
        "what are the latest messages I exchanged together with the usernames john, ryan, and jennifer",
        "show the messages in the multi person dm with the usernames john, ryan, and jennifer on Slack",
        "list the messages I exchanged together with the usernames john, ryan, and jennifer",
        "list the message history together with the usernames john, ryan, and jennifer",
    ]

    for i, user_message in enumerate(no_arguments_user_messages_by_username):
        suite.add_case(
            name=f"{user_message} [{i}]",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages_in_multi_person_dm_conversation_by_users,
                    args={
                        "usernames_or_emails": ["john", "ryan", "jennifer"],
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="usernames_or_emails", weight=1.0),
            ],
        )

    suite.add_case(
        name="get messages in multi person direct conversation with mixed usernames and emails",
        user_message="get the messages I exchanged together with the usernames john, ryan, and jennifer@acme.com",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_multi_person_dm_conversation_by_users,
                args={
                    "usernames_or_emails": ["john", "ryan", "jennifer@acme.com"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="usernames_or_emails", weight=1.0),
        ],
    )

    suite.add_case(
        name="get messages in direct conversation by username (on a specific date)",
        user_message="get the messages I exchanged together with the usernames john, ryan, and jennifer on 2025-01-31",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_multi_person_dm_conversation_by_users,
                args={
                    "usernames_or_emails": ["john", "ryan", "jennifer"],
                    "oldest_datetime": "2025-01-31 00:00:00",
                    "latest_datetime": "2025-01-31 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="usernames_or_emails", weight=1 / 3),
            DatetimeCritic(
                critic_field="oldest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by username (2 days ago)",
        user_message="Get the messages I exchanged together with the usernames john, ryan, and jennifer starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_multi_person_dm_conversation_by_users,
                args={
                    "usernames_or_emails": ["john", "ryan", "jennifer"],
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="usernames_or_emails", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    return suite

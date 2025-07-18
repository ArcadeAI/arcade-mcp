import json
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
def get_messages_in_channel_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting messages in channels."""
    suite = EvalSuite(
        name="Slack Chat Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    no_arguments_user_messages_by_channel_name = [
        "what are the latest messages in the #general channel",
        "show me the messages in the general channel",
        "list the messages in the #general channel",
        "list the messages in the general channel",
    ]

    for i, user_message in enumerate(no_arguments_user_messages_by_channel_name):
        suite.add_case(
            name=f"Get messages in conversation by name {i}: '{user_message}'",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages,
                    args={
                        "conversation_id": None,
                        "channel_name": "general",
                        "user_ids": None,
                        "usernames": None,
                        "emails": None,
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=0.1),
                BinaryCritic(critic_field="channel_name", weight=0.6),
                BinaryCritic(critic_field="user_ids", weight=0.1),
                BinaryCritic(critic_field="usernames", weight=0.1),
                BinaryCritic(critic_field="emails", weight=0.1),
            ],
        )

    no_arguments_user_messages_by_conversation_id = [
        "Get the history of the conversation with id '1234567890'",
        "Get the history of the conversation with id '1234567890'",
        "list the messages in the conversation with id '1234567890'",
        "list the messages in the conversation with id '1234567890'",
    ]

    for user_message in no_arguments_user_messages_by_conversation_id:
        suite.add_case(
            name=f"Get conversation history by id: '{user_message}'",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages,
                    args={
                        "conversation_id": "1234567890",
                        "channel_name": None,
                        "user_ids": None,
                        "usernames": None,
                        "emails": None,
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=0.6),
                BinaryCritic(critic_field="channel_name", weight=0.1),
                BinaryCritic(critic_field="user_ids", weight=0.1),
                BinaryCritic(critic_field="usernames", weight=0.1),
                BinaryCritic(critic_field="emails", weight=0.1),
            ],
        )

    suite.add_case(
        name="Get conversation history with limit by name",
        user_message="Get the last 10 messages in the #general channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get conversation history with limit by id",
        user_message="Get the last 25 messages in the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "limit": 25,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.3),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.3),
        ],
    )

    # Relative time eval cases by id

    suite.add_case(
        name="Get conversation history oldest relative by id (2 days ago)",
        user_message="Get the messages in the conversation with id '1234567890' starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.3),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest and latest relative by id",
        user_message="Get the messages in the conversation with id '1234567890' from 2 days ago to 3 hours ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "02:00:00",
                    "latest_relative": "00:03:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.2),
            RelativeTimeBinaryCritic(critic_field="latest_relative", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by id (1 week ago)",
        user_message="Get the messages in the conversation with id '1234567890' starting 1 week ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "07:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.3),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by id (yesterday)",
        user_message="Get the messages in the conversation with id '1234567890' from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "01:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.3),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    # Relative time eval cases by name

    suite.add_case(
        name="Get conversation history oldest relative by name (2 days ago)",
        user_message="Get the messages in the #general channel starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest and latest relative by name",
        user_message="Get the messages in the #general channel from 2 days ago to 3 hours ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "02:00:00",
                    "latest_relative": "00:03:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.2),
            RelativeTimeBinaryCritic(critic_field="latest_relative", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by name (yesterday)",
        user_message="Get the messages in the #general channel from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "01:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by name (last week)",
        user_message="Get the messages in the #general channel from last week",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_relative": "07:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.3),
        ],
    )

    # Absolute time eval cases by id

    suite.add_case(
        name="Get conversation history oldest absolute by id (on a specific date)",
        user_message="Get the messages in the conversation with id '1234567890' from 2025-01-20",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-20 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
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
        name="Get conversation history oldest absolute by id (between a date range)",
        user_message="Get the messages in the conversation with id '1234567890' from 2025-01-20 to 2025-01-25",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-25 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
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
        name="Get conversation history oldest absolute by name (on a specific date)",
        user_message="Get the messages in the #general channel from 2025-01-20",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-20 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            # We use a timedelta of 10 seconds because sometimes the LLM will select the limit
            # date at 23:59:59, other times it'll select the next day at 00:00:00.
            DatetimeCritic(
                critic_field="oldest_datetime", weight=0.2, max_difference=timedelta(seconds=10)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=0.2, max_difference=timedelta(seconds=10)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest absolute by name (between a date range)",
        user_message="Get the messages in the #general channel from 2025-01-20 to 2025-01-25",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-25 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            # We use a timedelta of 10 seconds because sometimes the LLM will select the limit
            # date at 23:59:59, other times it'll select the next day at 00:00:00.
            DatetimeCritic(
                critic_field="oldest_datetime", weight=0.2, max_difference=timedelta(seconds=10)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=0.2, max_difference=timedelta(seconds=10)
            ),
        ],
    )

    # Eval case for pagination

    suite.add_case(
        name="Get conversation history with pagination",
        user_message="get the next 5 messages",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages,
                args={
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "usernames": None,
                    "emails": None,
                    "limit": 5,
                    "next_cursor": "dXNlcjpVsDjzOTZGVDlQRA==",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.2),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="next_cursor", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
        additional_messages=[
            {"role": "user", "content": "Get the last 2 messages on the general channel"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Slack_GetConversationHistoryByName",
                            "arguments": json.dumps({
                                "conversation_name": "general",
                                "limit": 2,
                            }),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "messages": [
                        {
                            "blocks": [
                                {
                                    "block_id": "abc123",
                                    "elements": [
                                        {
                                            "elements": [
                                                {
                                                    "text": "Almost there, Boss, need to get some evals in!",
                                                    "type": "text",
                                                }
                                            ],
                                            "type": "rich_text_section",
                                        }
                                    ],
                                    "type": "rich_text",
                                }
                            ],
                            "client_msg_id": "msg_id_0",
                            "datetime_timestamp": "2025-01-21 16:59:55",
                            "team": "617263616465207465616D20697320617420626F7373206C6576656C",
                            "text": "Almost there, Boss, need to get some evals in!",
                            "ts": "1737507595.598529",
                            "type": "message",
                            "user": "77686F2069732074686520626F73733F",
                        },
                        {
                            "blocks": [
                                {
                                    "block_id": "xyz456",
                                    "elements": [
                                        {
                                            "elements": [
                                                {
                                                    "text": "hey, are the Slack Tools ready yet?",
                                                    "type": "text",
                                                }
                                            ],
                                            "type": "rich_text_section",
                                        }
                                    ],
                                    "type": "rich_text",
                                }
                            ],
                            "client_msg_id": "msg_id_1",
                            "datetime_timestamp": "2025-01-21 16:57:35",
                            "team": "617263616465207465616D20697320617420626F7373206C6576656C",
                            "text": "hey, are the Slack Tools ready yet?",
                            "ts": "1737507595.598529",
                            "type": "message",
                            "user": "73616D2069732074686520626F7373",
                        },
                    ],
                    "next_cursor": "dXNlcjpVsDjzOTZGVDlQRA==",
                }),
                "tool_call_id": "call_1",
                "name": "Slack_GetConversationHistoryByName",
            },
            {
                "role": "assistant",
                "content": 'Here are the last 2 messages from the general channel:\n\n1. **User:** 77686F2069732074686520626F73733F  \n   **Message:** "Almost there, Boss, need to get some evals in!"  \n   **Timestamp:** 2025-01-21 16:59:55\n\n2. **User:** 73616D2069732074686520626F7373  \n   **Message:** "hey, are the Slack Tools ready yet?"  \n   **Timestamp:** 2025-01-21 16:57:35',
            },
        ],
    )

    return suite

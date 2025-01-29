import json
from datetime import timedelta
from typing import Any

from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import arcade_slack
from arcade_slack.tools.chat import (
    get_conversation_metadata_by_id,
    get_conversation_metadata_by_name,
    get_members_in_conversation_by_id,
    get_members_in_conversation_by_name,
    get_messages_in_channel_by_name,
    get_messages_in_conversation_by_id,
    list_conversations_metadata,
    list_direct_message_conversations_metadata,
    list_group_direct_message_conversations_metadata,
    list_private_channels_metadata,
    list_public_channels_metadata,
    send_dm_to_user,
    send_message_to_channel,
)


class RelativeTimeBinaryCritic(BinaryCritic):
    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Evaluates whether the expected and actual relative time strings are equivalent after casting.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        # Cast actual to the type of expected
        try:
            actual_casted = self.cast_actual(expected, actual)
        # TODO log or something better here
        except TypeError:
            actual_casted = actual

        expected_parts = tuple(map(int, expected.split(":")))
        actual_parts = tuple(map(int, actual_casted.split(":")))

        if len(expected_parts) != 3 or len(actual_parts) != 3:
            return {"match": False, "score": 0.0}

        exp_days, exp_hours, exp_minutes = expected_parts
        act_days, act_hours, act_minutes = actual_parts

        match = exp_days == act_days and exp_hours == act_hours and exp_minutes == act_minutes
        return {"match": match, "score": self.weight if match else 0.0}


# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def send_message_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Slack messaging tools."""
    suite = EvalSuite(
        name="Slack Messaging Tools Evaluation",
        system_message="You are an AI assistant that can send direct messages and post messages to channels in Slack using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Send DM to User Scenarios
    suite.add_case(
        name="Send DM to user with clear username",
        user_message="Send a direct message to johndoe saying 'Hello, can we meet at 3 PM?'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_dm_to_user,
                args={
                    "user_name": "johndoe",
                    "message": "Hello, can we meet at 3 PM?",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="user_name", weight=0.5),
            SimilarityCritic(critic_field="message", weight=0.5, similarity_threshold=0.9),
        ],
    )

    suite.add_case(
        name="Send DM with ambiguous username",
        user_message="ask him for an update on the project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_dm_to_user,
                args={
                    "user_name": "john",
                    "message": "Hi John, could you please provide an update on the Acme project?",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="user_name", weight=0.75),
            SimilarityCritic(critic_field="message", weight=0.25, similarity_threshold=0.6),
        ],
        additional_messages=[
            {"role": "user", "content": "Message John about the Acme project deadline"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Slack_ListUsers",
                            "arguments": '{"exclude_bots":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "users": [
                        {
                            "display_name": "john",
                            "email": "john@randomtech.com",
                            "id": "abc123",
                            "is_bot": False,
                            "name": "john",
                            "real_name": "John Doe",
                            "timezone": "America/Los_Angeles",
                        },
                        {
                            "display_name": "jack",
                            "email": "jack@randomtech.com",
                            "id": "def456",
                            "is_bot": False,
                            "name": "jack",
                            "real_name": "Jack Doe",
                            "timezone": "America/Los_Angeles",
                        },
                    ]
                }),
                "tool_call_id": "call_1",
                "name": "Slack_ListUsers",
            },
            {
                "role": "assistant",
                "content": "What would you like to include in the message to John about the Acme project deadline?",
            },
        ],
    )

    suite.add_case(
        name="Send DM with username in different format",
        user_message="yes, send it",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_dm_to_user,
                args={
                    "user_name": "jane.doe",
                    "message": "Hi Jane, I need to reschedule our meeting. When are you available?",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="user_name", weight=0.75),
            SimilarityCritic(critic_field="message", weight=0.25, similarity_threshold=0.6),
        ],
        additional_messages=[
            {"role": "user", "content": "Message Jane.Doe asking to reschedule our meeting"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Slack_ListUsers",
                            "arguments": '{"exclude_bots":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "users": [
                        {
                            "display_name": "jane.doe",
                            "email": "jane@randomtech.com",
                            "id": "abc123",
                            "is_bot": False,
                            "name": "jane.doe",
                            "real_name": "Jane Doe",
                            "timezone": "America/Los_Angeles",
                        },
                        {
                            "display_name": "jack",
                            "email": "jack@randomtech.com",
                            "id": "def456",
                            "is_bot": False,
                            "name": "jack",
                            "real_name": "Jack Doe",
                            "timezone": "America/Los_Angeles",
                        },
                    ]
                }),
                "tool_call_id": "call_1",
                "name": "Slack_ListUsers",
            },
            {
                "role": "assistant",
                "content": "I found a user with the name 'jane.doe'. Would you like to send a message to them?",
            },
        ],
    )

    # Send Message to Channel Scenarios
    suite.add_case(
        name="Send message to channel with clear name",
        user_message="Post 'The new feature is now live!' in the #announcements channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "channel_name": "announcements",
                    "message": "The new feature is now live!",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="channel_name", weight=0.5),
            SimilarityCritic(critic_field="message", weight=0.5),
        ],
    )

    suite.add_case(
        name="Send message to channel with ambiguous name",
        user_message="Inform the team in the general channel about the upcoming maintenance",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "channel_name": "general",
                    "message": "Attention team: There will be upcoming maintenance. Please save your work and expect some downtime.",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="channel_name", weight=0.8),
            SimilarityCritic(critic_field="message", weight=0.2, similarity_threshold=0.6),
        ],
    )

    # Adversarial Scenarios
    suite.add_case(
        name="Ambiguous between DM and channel message",
        user_message="general",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "channel_name": "general",
                    "message": "Great job on the presentation!",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="channel_name", weight=0.4),
            SimilarityCritic(critic_field="message", weight=0.6),
        ],
        additional_messages=[
            {"role": "user", "content": "Send 'Great job on the presentation!' to the team"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "Slack_ListPublicChannelsMetadata",
                            "arguments": '{"limit":20}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": json.dumps({
                    "conversations": [
                        {
                            "conversation_type": "public_channel",
                            "id": "channel1",
                            "is_archived": False,
                            "is_member": True,
                            "is_private": False,
                            "name": "random",
                            "num_members": 999,
                            "purpose": "Random stuff",
                        },
                        {
                            "conversation_type": "public_channel",
                            "id": "channel2",
                            "is_archived": False,
                            "is_member": True,
                            "is_private": False,
                            "name": "general",
                            "num_members": 999,
                            "purpose": "Just a general channel",
                        },
                    ],
                    "next_cursor": "",
                }),
                "tool_call_id": "call_1",
                "name": "Slack_ListPublicChannelsMetadata",
            },
            {
                "role": "assistant",
                "content": 'To send the message "Great job on the presentation!" to the team, please let me know which Slack channel you\'d like to use:\n\n1. #random\n2. #general\n\nPlease let me know your choice!',
            },
        ],
    )

    # Multiple recipients in DM request
    suite.add_case(
        name="Multiple recipients in DM request",
        user_message="Send DMs to the users 'alice' and 'bob' about pushing the meeting tomorrow. I have to much work to do.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_dm_to_user,
                args={
                    "user_name": "alice",
                    "message": "Hi Alice, about our meeting tomorrow, let's reschedule? I am swamped with work.",
                },
            ),
            ExpectedToolCall(
                func=send_dm_to_user,
                args={
                    "user_name": "bob",
                    "message": "Hi Bob, about our meeting tomorrow, let's reschedule? I am swamped with work.",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="user_name", weight=0.75),
            SimilarityCritic(critic_field="message", weight=0.25, similarity_threshold=0.5),
        ],
    )

    suite.add_case(
        name="Channel name similar to username",
        user_message="Post 'sounds great!' in john-project channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "channel_name": "john-project",
                    "message": "Sounds great!",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="channel_name", weight=0.5),
            SimilarityCritic(critic_field="message", weight=0.5),
        ],
    )

    return suite


@tool_eval()
def list_conversations_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools listing conversations."""
    suite = EvalSuite(
        name="Slack Messaging Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    cases = [
        (
            "List my conversations",
            "List all conversations I am a member of",
            list_conversations_metadata,
        ),
        (
            "List public channels",
            "List all public channels",
            list_public_channels_metadata,
        ),
        (
            "List private channels",
            "List all private channels",
            list_private_channels_metadata,
        ),
        (
            "List group direct message channels",
            "List all group direct message channels",
            list_group_direct_message_conversations_metadata,
        ),
        (
            "List individual direct message channels",
            "List all individual direct message channels",
            list_direct_message_conversations_metadata,
        ),
        (
            "List direct message channels",
            "List all direct message channels",
            list_direct_message_conversations_metadata,
        ),
        (
            "List public and private channels",
            "List public and private channels I am a member of",
            list_public_channels_metadata,
            list_private_channels_metadata,
        ),
        (
            "List public channels and direct message conversations",
            "List public channels and direct message conversations I am a member of",
            list_public_channels_metadata,
            list_direct_message_conversations_metadata,
        ),
    ]

    for name, user_message, *expect_called_tool_functions in cases:
        suite.add_case(
            name=name,
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=tool_function,
                    args={},
                )
                for tool_function in expect_called_tool_functions
            ],
        )

    return suite


@tool_eval()
def get_conversations_metadata_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting conversations metadata."""
    suite = EvalSuite(
        name="Slack Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get conversation metadata by name",
        user_message="Get the metadata of the #general channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata_by_name,
                args={
                    "conversation_name": "general",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by id",
        user_message="Get the metadata of the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata_by_id,
                args={
                    "conversation_id": "1234567890",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def get_conversations_members_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting conversations members."""
    suite = EvalSuite(
        name="Slack Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    user_messages = [
        "Get the members of the #general channel",
        "Get the members of the general channel",
        "Get a list of people in the #general channel",
        "Get a list of people in the general channel",
        "Show me who's in the #general channel",
        "Show me who's in the general channel",
        "Who is in the #general channel?",
        "Who is in the general channel?",
    ]

    for user_message in user_messages:
        suite.add_case(
            name=f"Get conversation members by name: {user_message}",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_members_in_conversation_by_name,
                    args={
                        "conversation_name": "general",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_name", weight=1.0),
            ],
        )

    suite.add_case(
        name="Get conversation members by id",
        user_message="Get the members of the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_members_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def get_conversation_history_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting conversations history."""
    suite = EvalSuite(
        name="Slack Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    no_arguments_user_messages_by_conversation_name = [
        "Get the history of the #general channel",
        "Get the history of the general channel",
        "list the messages in the #general channel",
        "list the messages in the general channel",
    ]

    for user_message in no_arguments_user_messages_by_conversation_name:
        suite.add_case(
            name=f"Get conversation history by name: '{user_message}'",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_messages_in_channel_by_name,
                    args={
                        "conversation_name": "general",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_name", weight=1.0),
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
                    func=get_messages_in_conversation_by_id,
                    args={
                        "conversation_id": "1234567890",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=1.0),
            ],
        )

    suite.add_case(
        name="Get conversation history with limit by name",
        user_message="Get the last 10 messages in the #general channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get conversation history with limit by id",
        user_message="Get the last 25 messages in the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "limit": 25,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1.0),
        ],
    )

    # Relative time eval cases by id

    suite.add_case(
        name="Get conversation history oldest relative by id (2 days ago)",
        user_message="Get the messages in the conversation with id '1234567890' starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest and latest relative by id",
        user_message="Get the messages in the conversation with id '1234567890' from 2 days ago to 3 hours ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_relative": "02:00:00",
                    "latest_relative": "00:03:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1 / 3),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=1 / 3),
            RelativeTimeBinaryCritic(critic_field="latest_relative", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by id (1 week ago)",
        user_message="Get the messages in the conversation with id '1234567890' starting 1 week ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_relative": "07:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by id (yesterday)",
        user_message="Get the messages in the conversation with id '1234567890' from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_relative": "01:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    # Relative time eval cases by name

    suite.add_case(
        name="Get conversation history oldest relative by name (2 days ago)",
        user_message="Get the messages in the #general channel starting 2 days ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_relative": "02:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest and latest relative by name",
        user_message="Get the messages in the #general channel from 2 days ago to 3 hours ago",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_relative": "02:00:00",
                    "latest_relative": "00:03:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1 / 3),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=1 / 3),
            RelativeTimeBinaryCritic(critic_field="latest_relative", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by name (yesterday)",
        user_message="Get the messages in the #general channel from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_relative": "01:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest relative by name (last week)",
        user_message="Get the messages in the #general channel from last week",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_relative": "07:00:00",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=0.5),
            RelativeTimeBinaryCritic(critic_field="oldest_relative", weight=0.5),
        ],
    )

    # Absolute time eval cases by id

    suite.add_case(
        name="Get conversation history oldest absolute by id (on a specific date)",
        user_message="Get the messages in the conversation with id '1234567890' from 2025-01-20",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-20 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1 / 3),
            DatetimeCritic(
                critic_field="oldest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest absolute by id (between a date range)",
        user_message="Get the messages in the conversation with id '1234567890' from 2025-01-20 to 2025-01-25",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_conversation_by_id,
                args={
                    "conversation_id": "1234567890",
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-25 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1 / 3),
            DatetimeCritic(
                critic_field="oldest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=1 / 3, max_difference=timedelta(minutes=2)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest absolute by name (on a specific date)",
        user_message="Get the messages in the #general channel from 2025-01-20",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-20 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1 / 3),
            # We use a timedelta of 10 seconds because sometimes the LLM will select the limit
            # date at 23:59:59, other times it'll select the next day at 00:00:00.
            DatetimeCritic(
                critic_field="oldest_datetime", weight=1 / 3, max_difference=timedelta(seconds=10)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=1 / 3, max_difference=timedelta(seconds=10)
            ),
        ],
    )

    suite.add_case(
        name="Get conversation history oldest absolute by name (between a date range)",
        user_message="Get the messages in the #general channel from 2025-01-20 to 2025-01-25",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "oldest_datetime": "2025-01-20 00:00:00",
                    "latest_datetime": "2025-01-25 23:59:59",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1 / 3),
            # We use a timedelta of 10 seconds because sometimes the LLM will select the limit
            # date at 23:59:59, other times it'll select the next day at 00:00:00.
            DatetimeCritic(
                critic_field="oldest_datetime", weight=1 / 3, max_difference=timedelta(seconds=10)
            ),
            DatetimeCritic(
                critic_field="latest_datetime", weight=1 / 3, max_difference=timedelta(seconds=10)
            ),
        ],
    )

    # Eval case for pagination

    suite.add_case(
        name="Get conversation history with pagination",
        user_message="get the next 5 messages",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_messages_in_channel_by_name,
                args={
                    "conversation_name": "general",
                    "limit": 5,
                    "cursor": "cursor_xyz",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_name", weight=1 / 3),
            BinaryCritic(critic_field="cursor", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
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
                    "next_cursor": "cursor_xyz",
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

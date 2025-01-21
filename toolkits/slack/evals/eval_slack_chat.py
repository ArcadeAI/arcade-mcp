import json

from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import arcade_slack
from arcade_slack.tools.chat import send_dm_to_user, send_message_to_channel

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
            BinaryCritic(critic_field="user_name", weight=0.5),
            SimilarityCritic(critic_field="message", weight=0.5),
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
        user_message="Send DMs to Alice and Bob about pushing the meeting tomorrow. I have to much work to do.",
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

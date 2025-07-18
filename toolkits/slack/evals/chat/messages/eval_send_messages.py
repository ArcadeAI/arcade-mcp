import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.chat import send_message

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
                func=send_message,
                args={
                    "message": "Hello, can we meet at 3 PM?",
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "emails": None,
                    "usernames": ["johndoe"],
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.3, similarity_threshold=0.9),
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.3),
        ],
    )

    suite.add_case(
        name="Send message to channel with clear name",
        user_message="Post 'The new feature is now live!' in the #announcements channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "message": "The new feature is now live!",
                    "conversation_id": None,
                    "channel_name": "announcements",
                    "user_ids": None,
                    "emails": None,
                    "usernames": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.3, similarity_threshold=0.9),
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
        ],
    )

    suite.add_case(
        name="Send message to channel with ambiguous name",
        user_message="Inform the team in the general channel about the upcoming maintenance",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "message": "Attention team: There will be upcoming maintenance. Please save your work and expect some downtime.",
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "emails": None,
                    "usernames": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.3, similarity_threshold=0.9),
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
        ],
    )

    # Adversarial Scenarios
    suite.add_case(
        name="Ambiguous between DM and channel message",
        user_message="general",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "message": "Great job on the presentation!",
                    "conversation_id": None,
                    "channel_name": "general",
                    "user_ids": None,
                    "emails": None,
                    "usernames": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.3, similarity_threshold=0.9),
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
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
                            "name": "Slack_ListConversationsMetadata",
                            "arguments": '{"limit":20, "conversation_types":["public_channel"]}',
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

    suite.add_case(
        name="Multiple recipients in DM request",
        user_message="Send DMs to the users 'alice' and 'bob' about rescheduling our meeting tomorrow. I have too much work to do.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "emails": None,
                    "usernames": ["alice"],
                },
            ),
            ExpectedToolCall(
                func=send_message,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "emails": None,
                    "usernames": ["bob"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.6),
        ],
    )

    suite.add_case(
        name="Multiple recipients in MPIM request",
        user_message="Send a message to the users 'alice' and 'bob' about rescheduling our meeting tomorrow. I have too much work to do.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": None,
                    "emails": None,
                    "usernames": ["alice", "bob"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.6),
        ],
    )

    suite.add_case(
        name="Channel name similar to username",
        user_message="Post 'sounds great!' in john-project channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message,
                args={
                    "conversation_id": None,
                    "channel_name": "john-project",
                    "user_ids": None,
                    "emails": None,
                    "usernames": None,
                    "message": "Sounds great!",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.3, similarity_threshold=0.9),
            BinaryCritic(critic_field="conversation_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.3),
            BinaryCritic(critic_field="user_ids", weight=0.1),
            BinaryCritic(critic_field="emails", weight=0.1),
            BinaryCritic(critic_field="usernames", weight=0.1),
        ],
    )

    return suite

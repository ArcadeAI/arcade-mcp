from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.chat import get_conversation_metadata

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def get_conversations_metadata_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting conversations metadata."""
    suite = EvalSuite(
        name="Slack Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get channel metadata by name",
        user_message="Get the metadata of the #general channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by id",
        user_message="Get the metadata of the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by username mentioning DM",
        user_message="get the metadata of the DM with janedoe",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by username mentioning IM",
        user_message="get metadata about my IM with janedoe",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by email mentioning DM",
        user_message="get the metadata of the DM with jane.doe@acme.com",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by email mentioning IM",
        user_message="get the metadata of the IM with jane.doe@acme.com",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
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
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Get conversation metadata by mixed user ID, email, and username",
        user_message=(
            "get the metadata of the multi-person conversation I have with these users together: "
            "janedoe, john@acme.com, and U0123456789"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_conversation_metadata,
                args={
                    "conversation_id": None,
                    "channel_name": None,
                    "user_ids": ["U0123456789"],
                    "usernames": ["janedoe"],
                    "emails": ["john@acme.com"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=1 / 5),
            BinaryCritic(critic_field="channel_name", weight=1 / 5),
            BinaryCritic(critic_field="user_ids", weight=1 / 5),
            BinaryCritic(critic_field="usernames", weight=1 / 5),
            BinaryCritic(critic_field="emails", weight=1 / 5),
        ],
    )

    return suite

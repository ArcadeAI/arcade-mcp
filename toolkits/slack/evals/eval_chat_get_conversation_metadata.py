from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.chat import (
    get_channel_metadata_by_name,
    get_conversation_metadata_by_id,
    get_direct_message_conversation_metadata_by_user,
)

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
                func=get_channel_metadata_by_name,
                args={
                    "channel_name": "general",
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

    get_metadata_by_username_user_messages = [
        "get the metadata of the direct message conversation with the user 'jane.doe'"
        "get metadata about my private conversation with the user 'jane.doe'",
        "get metadata about my IM conversation with the user 'jane.doe'",
    ]

    for i, user_message in enumerate(get_metadata_by_username_user_messages):
        suite.add_case(
            name=f"Get direct message conversation metadata by username {i}",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_direct_message_conversation_metadata_by_user,
                    args={
                        "username_or_email": "jane.doe",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="username_or_email", weight=1.0),
            ],
        )

    get_metadata_by_email_user_messages = [
        "get the metadata of the direct message conversation with the user 'jane.doe@acme.com'"
        "get metadata about my private conversation with the user 'jane.doe@acme.com'",
        "get metadata about my IM conversation with the user 'jane.doe@acme.com'",
    ]

    for i, user_message in enumerate(get_metadata_by_email_user_messages):
        suite.add_case(
            name=f"Get direct message conversation metadata by email {i}",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_direct_message_conversation_metadata_by_user,
                    args={
                        "username_or_email": "jane.doe@acme.com",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="username_or_email", weight=1.0),
            ],
        )

    return suite

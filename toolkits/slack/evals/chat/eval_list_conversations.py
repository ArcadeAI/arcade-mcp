from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.chat import (
    list_conversations_metadata,
    list_direct_message_conversations_metadata,
    list_group_direct_message_conversations_metadata,
    list_private_channels_metadata,
    list_public_channels_metadata,
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

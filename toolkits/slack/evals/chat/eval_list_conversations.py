from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.models import ConversationType
from arcade_slack.tools.chat import list_conversations

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

    suite.add_case(
        name="List all conversations I am a member of",
        user_message="List all conversations I am a member of",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List 10 conversations I am a member of",
        user_message="List 10 conversations I am a member of",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": None,
                    "limit": 10,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="List all public channels",
        user_message="List all public channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [ConversationType.PUBLIC_CHANNEL.value],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List all private channels",
        user_message="List all private channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [ConversationType.PRIVATE_CHANNEL.value],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List all public and private channels",
        user_message="List all public and private channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [
                        ConversationType.PUBLIC_CHANNEL.value,
                        ConversationType.PRIVATE_CHANNEL.value,
                    ],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List direct message channels",
        user_message="List direct message channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [
                        ConversationType.DIRECT_MESSAGE.value,
                    ],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List group direct message channels",
        user_message="List group direct message channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [
                        ConversationType.MULTI_PERSON_DIRECT_MESSAGE.value,
                    ],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    suite.add_case(
        name="List my multi-person conversations",
        user_message="List my multi-person conversations",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_conversations,
                args={
                    "conversation_types": [
                        ConversationType.MULTI_PERSON_DIRECT_MESSAGE.value,
                    ],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="conversation_types", weight=1.0),
        ],
    )

    return suite

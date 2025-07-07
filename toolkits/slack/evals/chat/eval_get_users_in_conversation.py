from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_slack
from arcade_slack.tools.chat import get_users_in_conversation

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_slack)


@tool_eval()
def get_users_in_conversation_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting conversations members."""
    suite = EvalSuite(
        name="Slack Tools Evaluation",
        system_message="You are an AI assistant that can interact with Slack to send messages and get information from conversations, users, etc.",
        catalog=catalog,
        rubric=rubric,
    )

    user_messages = [
        "Get the members of the #general channel",
        "Get the users in the #general channel",
        "Get a list of people in the #general channel",
        "Get a list of people in the general channel",
        "Show me who's in the #general channel",
        "Who is in the general channel?",
    ]

    for user_message in user_messages:
        suite.add_case(
            name=f"Get users in channel by channel name: {user_message}",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_users_in_conversation,
                    args={
                        "conversation_id": None,
                        "channel_name": "general",
                    },
                ),
            ],
            critics=[
                BinaryCritic(critic_field="conversation_id", weight=0.4),
                BinaryCritic(critic_field="channel_name", weight=0.6),
            ],
        )

    suite.add_case(
        name="Get users in conversation by conversation id",
        user_message="Get the users in the conversation with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_users_in_conversation,
                args={
                    "conversation_id": "1234567890",
                    "channel_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="conversation_id", weight=0.6),
            BinaryCritic(critic_field="channel_name", weight=0.4),
        ],
    )

    return suite

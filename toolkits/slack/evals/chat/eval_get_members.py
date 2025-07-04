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
    get_members_in_channel_by_name,
    get_members_in_conversation_by_id,
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
            name=f"Get channel members by name: {user_message}",
            user_message=user_message,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=get_members_in_channel_by_name,
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

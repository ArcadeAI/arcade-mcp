from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.channel import send_message_to_channel

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def send_message_to_channel_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools sending messages to channels in Teams."""
    suite = EvalSuite(
        name="Teams Channel Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Send message to channel by its id",
        user_message=(
            "Send the message 'Hello, how are you?' to the '19:1234567890@thread.tacv2' channel"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "message": "Hello, how are you?",
                    "channel_id_or_name": "19:1234567890@thread.tacv2",
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="channel_id_or_name", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Send message to channel by its name",
        user_message="Send the message 'Hello, how are you?' to the 'general' channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "message": "Hello, how are you?",
                    "channel_id_or_name": "general",
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=0.4),
            BinaryCritic(critic_field="channel_id_or_name", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Send message to channel by its name in a team",
        user_message=(
            "Send the message 'Hello, how are you?' to the 'general' channel "
            "in the 'engineering' team"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_message_to_channel,
                args={
                    "message": "Hello, how are you?",
                    "channel_id_or_name": "general",
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="message", weight=1 / 3),
            BinaryCritic(critic_field="channel_id_or_name", weight=1 / 3),
            BinaryCritic(critic_field="team_id_or_name", weight=1 / 3),
        ],
    )

    return suite

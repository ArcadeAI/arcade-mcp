from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.channel import get_channel_messages

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_channel_messages_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting channels in Teams."""
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
        name="Get channel messages by the channel id",
        user_message="Get the messages in the channel with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_messages,
                args={
                    "channel_id": "1234567890",
                    "channel_name": None,
                    "limit": 50,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.7),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get channel messages by the channel id with limit",
        user_message="Get 15 messages in the channel with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_messages,
                args={
                    "channel_id": "1234567890",
                    "channel_name": None,
                    "limit": 15,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.4),
            BinaryCritic(critic_field="channel_name", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get channel messages by the channel name",
        user_message="Get the messages in the 'general' channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_messages,
                args={
                    "channel_id": None,
                    "channel_name": "general",
                    "limit": 50,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.7),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get channel messages by the channel name in a team",
        user_message="Get the messages from the 'general' channel in the 'engineering' team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_messages,
                args={
                    "channel_id": None,
                    "channel_name": "general",
                    "limit": 50,
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.1),
            BinaryCritic(critic_field="channel_name", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.4),
        ],
    )

    return suite

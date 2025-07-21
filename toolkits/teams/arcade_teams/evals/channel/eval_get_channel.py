from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.channel import get_channel_metadata

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def get_channel_eval_suite() -> EvalSuite:
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
        name="Get channel by the channel id",
        user_message="Get info about the channel with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "team_id_or_name": None,
                    "channel_id": "1234567890",
                    "channel_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
            BinaryCritic(critic_field="channel_id", weight=0.6),
            BinaryCritic(critic_field="channel_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get channel by the channel name",
        user_message="Get info about the 'general' channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "team_id_or_name": None,
                    "channel_id": None,
                    "channel_name": "general",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
            BinaryCritic(critic_field="channel_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.6),
        ],
    )

    suite.add_case(
        name="Get channel by the channel name and team id",
        user_message="Get info about the 'general' channel in the team with id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "team_id_or_name": "1234567890",
                    "channel_id": None,
                    "channel_name": "general",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id_or_name", weight=0.4),
            BinaryCritic(critic_field="channel_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.4),
        ],
    )

    suite.add_case(
        name="Get channel by the channel name and team name",
        user_message="Get info about the 'general' channel in the engineering team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "team_id_or_name": "engineering",
                    "channel_id": None,
                    "channel_name": "general",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team_id_or_name", weight=0.4),
            BinaryCritic(critic_field="channel_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.4),
        ],
    )

    suite.add_case(
        name="Get channel members by id",
        user_message="What are the members of the channel with id 1234567890?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "channel_id": "1234567890",
                    "channel_name": None,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.6),
            BinaryCritic(critic_field="channel_name", weight=0.2),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get channel members by channel name",
        user_message="Get the members of the 'project-management' channel",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "channel_id": None,
                    "channel_name": "project-management",
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.6),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get channel members by channel name in a team",
        user_message=(
            "Get the members of the 'project-management' channel in the 'engineering' team."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_channel_metadata,
                args={
                    "channel_id": None,
                    "channel_name": "project-management",
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="channel_id", weight=0.2),
            BinaryCritic(critic_field="channel_name", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.4),
        ],
    )

    return suite

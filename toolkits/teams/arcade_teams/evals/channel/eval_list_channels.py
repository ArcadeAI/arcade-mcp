from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.tools.channel import list_channels

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def list_channels_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools listing channels in Teams."""
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
        name="List 20 channels",
        user_message="List 20 channels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_channels,
                args={
                    "limit": 20,
                    "offset": 0,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="offset", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="List 20 channels with offset",
        user_message="List 20 channels with offset 10",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_channels,
                args={
                    "limit": 20,
                    "offset": 10,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="offset", weight=0.4),
            BinaryCritic(critic_field="team_id_or_name", weight=0.2),
        ],
    )

    suite.add_case(
        name="List 20 channels in the engineering team",
        user_message="List 20 channels in the engineering team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_channels,
                args={
                    "limit": 20,
                    "offset": 0,
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="offset", weight=0.2),
            BinaryCritic(critic_field="team_id_or_name", weight=0.4),
        ],
    )

    return suite

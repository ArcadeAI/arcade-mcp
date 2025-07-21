from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.constants import MatchType
from arcade_teams.tools.channel import search_channels

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_channels_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools searching channels in Teams."""
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
        name="Search for channel by name",
        user_message="Search for channels containing 'foo'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_channels,
                args={
                    "keywords": ["foo"],
                    "limit": 50,
                    "offset": 0,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for channel by name with limit",
        user_message="Search for 10 channels containing 'foo'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_channels,
                args={
                    "keywords": ["foo"],
                    "limit": 10,
                    "offset": 0,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for channel containing two keywords",
        user_message="Search for channels containing both 'foo' and 'bar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_channels,
                args={
                    "keywords": ["foo", "bar"],
                    "match_type": MatchType.PARTIAL_ALL,
                    "limit": 50,
                    "offset": 0,
                    "team_id_or_name": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.35),
            BinaryCritic(critic_field="match_type", weight=0.35),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
            BinaryCritic(critic_field="team_id_or_name", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for channel by name",
        user_message="Search for channels in the engineering team containing both 'foo' and 'bar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_channels,
                args={
                    "keywords": ["foo", "bar"],
                    "match_type": MatchType.PARTIAL_ALL,
                    "limit": 50,
                    "offset": 0,
                    "team_id_or_name": "engineering",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.25),
            BinaryCritic(critic_field="match_type", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.125),
            BinaryCritic(critic_field="offset", weight=0.125),
            BinaryCritic(critic_field="team_id_or_name", weight=0.25),
        ],
    )

    return suite

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_teams
from arcade_teams.constants import PartialMatchType
from arcade_teams.critics import BinaryListCaseInsensitiveCritic
from arcade_teams.tools.users import search_users

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_users_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools searching users in Teams."""
    suite = EvalSuite(
        name="Teams Users Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search users by name",
        user_message="Search for users whose name contains 'John Doe'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_users,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search users by name, but mentioning 'people' in my org",
        user_message="Search people in my organization whose name contains 'John Doe'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_users,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search users by name with custom limit",
        user_message="Search for 10 users whose name contains 'John Doe'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_users,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 10,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.3),
            BinaryCritic(critic_field="match_type", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search users by name with multiple keywords",
        user_message="Search for users whose name contains both 'Foo' and 'Bar'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_users,
                args={
                    "keywords": ["Foo", "Bar"],
                    "match_type": PartialMatchType.PARTIAL_ALL,
                    "limit": 50,
                    "offset": 0,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="offset", weight=0.1),
        ],
    )

    return suite

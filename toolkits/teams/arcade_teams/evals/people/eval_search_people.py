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
from arcade_teams.tools.people import search_people

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
# Register the Slack tools
catalog.add_module(arcade_teams)


@tool_eval()
def search_people_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools searching people in Teams."""
    suite = EvalSuite(
        name="Teams People Tools Evaluation",
        system_message=(
            "You are an AI assistant that can interact with Teams to "
            "send messages and get information from chats, channels, users, etc. "
            "Today is 2025-07-21."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search people by name",
        user_message=(
            "Search for people I have interacted with before whose name contains 'John Doe'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_people,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 50,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search people by name, but mentioning 'users' instead of 'people'",
        user_message=(
            "Search for users I have interacted with before whose name contains 'John Doe'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_people,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 50,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search people by name with custom limit",
        user_message=(
            "Search for 10 people I have interacted with before whose name contains 'John Doe'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_people,
                args={
                    "keywords": ["John Doe"],
                    "match_type": PartialMatchType.PARTIAL_ANY,
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.3),
            BinaryCritic(critic_field="match_type", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search people by name with multiple keywords",
        user_message=(
            "Search for people I have interacted with before "
            "whose name contains both 'Foo' and 'Bar'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_people,
                args={
                    "keywords": ["Foo", "Bar"],
                    "match_type": PartialMatchType.PARTIAL_ALL,
                    "limit": 50,
                    "next_page_token": None,
                },
            ),
        ],
        critics=[
            BinaryListCaseInsensitiveCritic(critic_field="keywords", weight=0.4),
            BinaryCritic(critic_field="match_type", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    return suite

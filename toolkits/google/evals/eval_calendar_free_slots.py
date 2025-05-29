from datetime import timedelta

from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NoneCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.critics import AnyDatetimeCritic, DatetimeOrNoneCritic
from arcade_google.tools import find_time_slots_when_everyone_is_free

rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def get_free_slots_eval_suite() -> EvalSuite:
    """Create an evaluation suite for free slots Calendar tool."""
    suite = EvalSuite(
        name="Calendar Tools Evaluation",
        system_message=(
            "You are an AI assistant that can manage calendars and events using the provided tools. "
            "The first day of a week is Monday and the last day is Sunday. "
            "Today is Thursday, March 6, 2025 (2025-03-06). "
            "This week started on Monday, March 3, 2025 (2025-03-03) and ends on Sunday, March 9, 2025 (2025-03-09). "
            "Last week started on Monday, February 24, 2025 (2025-02-24) and ended on Sunday, March 2, 2025 (2025-03-02). "
            "Next week starts on Monday, March 10, 2025 (2025-03-10) and ends on Sunday, March 16, 2025 (2025-03-16). "
            "This month started on March 1, 2025 (2025-03-01) and ends on March 31, 2025 (2025-03-31). "
            "Last month started on February 1, 2025 (2025-02-01) and ended on February 28, 2025 (2025-02-28). "
            "Next month starts on April 1, 2025 (2025-04-01) and ends on April 30, 2025 (2025-04-30). "
            "This quarter started on January 1, 2025 (2025-01-01) and ends on March 31, 2025 (2025-03-31). "
            "Last quarter started on December 1, 2024 (2024-12-01) and ended on December 31, 2024 (2024-12-31). "
            "Next quarter starts on April 1, 2025 (2025-04-01) and ends on June 30, 2025 (2025-06-30). "
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get free slots for the next 5 days",
        user_message=("At what times am I free in the next 5 days?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-06",
                    "end_date": "2025-03-11",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeOrNoneCritic(
                critic_field="start_date", weight=0.35, tolerance=timedelta(days=1)
            ),
            DatetimeCritic(critic_field="end_date", weight=0.35, tolerance=timedelta(days=1)),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots for the next 10 days",
        user_message=("At what times am I free in the next 10 days?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-06",
                    "end_date": "2025-03-16",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeOrNoneCritic(
                critic_field="start_date", weight=0.35, tolerance=timedelta(days=1)
            ),
            DatetimeCritic(critic_field="end_date", weight=0.35, tolerance=timedelta(days=1)),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots this week",
        user_message=("At what times am I free this week?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    # Models sometimes will consider today as the start range, other times it will
                    # consider last Monday. The question is ambiguous, so we allow both.
                    "start_date": ["2025-03-03", "2025-03-06"],
                    "end_date": "2025-03-09",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            AnyDatetimeCritic(critic_field="start_date", weight=0.35),
            BinaryCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots next week",
        user_message=("At what times am I free next week?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-10",
                    "end_date": "2025-03-16",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            BinaryCritic(critic_field="start_date", weight=0.35),
            BinaryCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots today",
        user_message=("At what times am I free today?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-06",
                    "end_date": "2025-03-06",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeOrNoneCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots today",
        user_message=("At what times am I free tonight before 10 PM?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-06",
                    "end_date": "2025-03-06",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "22:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeOrNoneCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots this weekend",
        user_message=("At what times am I free this weekend?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-08",
                    "end_date": "2025-03-09",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots this month",
        user_message=("At what times am I free this month?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": ["2025-03-06", "2025-03-01"],
                    "end_date": "2025-03-31",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            AnyDatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots next month",
        user_message=("At what times am I free next month?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-30",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots last week",
        user_message=("At what times was I free last week?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-02-24",
                    "end_date": "2025-03-02",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots next quarter",
        user_message=("At what times am I free next quarter?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-04-01",
                    "end_date": "2025-06-30",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots in the next 30 days",
        user_message=("At what times am I free in the next 30 days?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-03-06",
                    "end_date": "2025-04-05",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeOrNoneCritic(
                critic_field="start_date", weight=0.35, tolerance=timedelta(days=1)
            ),
            DatetimeCritic(critic_field="end_date", weight=0.35, tolerance=timedelta(days=1)),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots in April",
        user_message=("At what times am I free in April?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-04-01",
                    "end_date": "2025-04-30",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots for a specific email address",
        user_message=("Is johndoe@example.com free some time tomorrow?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": ["johndoe@example.com"],
                    "start_date": "2025-03-07",
                    "end_date": "2025-03-07",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="email_addresses", weight=0.30),
            DatetimeCritic(critic_field="start_date", weight=0.25),
            DatetimeCritic(critic_field="end_date", weight=0.25),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots for a specific email address",
        user_message=(
            "I need to schedule a meeting with johndoe@example.com tomorrow. When are both of us free?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": ["johndoe@example.com"],
                    "start_date": "2025-03-07",
                    "end_date": "2025-03-07",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="email_addresses", weight=0.3),
            DatetimeCritic(critic_field="start_date", weight=0.25),
            DatetimeCritic(critic_field="end_date", weight=0.25),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get free slots for a specific email address",
        user_message=(
            "I need to schedule a meeting with johndoe@example.com tomorrow morning. When are both of us free?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": ["johndoe@example.com"],
                    "start_date": "2025-03-07",
                    "end_date": "2025-03-07",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "12:00",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="email_addresses", weight=0.2),
            DatetimeCritic(critic_field="start_date", weight=0.2),
            DatetimeCritic(critic_field="end_date", weight=0.2),
            BinaryCritic(critic_field="start_time_boundary", weight=0.2),
            BinaryCritic(critic_field="end_time_boundary", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get free slots for a specific date range",
        user_message=("At what times am I free between 2025-04-27 and 2025-04-29?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_time_slots_when_everyone_is_free,
                args={
                    "email_addresses": None,
                    "start_date": "2025-04-27",
                    "end_date": "2025-04-29",
                    "start_time_boundary": "08:00",
                    "end_time_boundary": "18:00",
                },
            )
        ],
        critics=[
            NoneCritic(critic_field="email_addresses", weight=0.1),
            DatetimeCritic(critic_field="start_date", weight=0.35),
            DatetimeCritic(critic_field="end_date", weight=0.35),
            BinaryCritic(critic_field="start_time_boundary", weight=0.1),
            BinaryCritic(critic_field="end_time_boundary", weight=0.1),
        ],
    )

    return suite

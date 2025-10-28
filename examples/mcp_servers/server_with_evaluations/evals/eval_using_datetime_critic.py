from datetime import timedelta

from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import server_with_evaluations
from server_with_evaluations.tools import calculate_time_until_event, get_meeting_reminder

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()

# Add all of the tools in the server_with_evaluations module to the catalog
catalog.add_module(server_with_evaluations)


@tool_eval()
def server_with_evaluations_datetime_eval_suite() -> EvalSuite:
    """
    Create an evaluation suite for datetime tools using DatetimeCritic.

    DatetimeCritic is useful when:
    - Dealing with time-based operations that may have slight variations
    - Evaluating meeting scheduling and reminder systems
    - Testing time difference calculations where exact precision isn't critical
    - Scenarios where timezone handling or clock drift might affect results
    """
    suite = EvalSuite(
        name="Datetime Tools Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant for managing meetings and schedules.",
        rubric=rubric,
    )

    suite.add_case(
        name="Calculate time remaining until meeting",
        user_message=(
            "How long until the meeting on 2025-10-15T14:30:00? "
            "Current time is around 2025-10-15T13:45:00 give or take a minute"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=calculate_time_until_event,
                args={
                    "event_datetime": "2025-10-15T14:30:00",
                    "from_datetime": "2025-10-15T13:45:00",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="from_datetime", weight=0.5),
            DatetimeCritic(
                critic_field="event_datetime",
                weight=0.5,
                tolerance=timedelta(seconds=60),
                max_difference=timedelta(hours=1),
            ),
        ],
    )

    suite.add_case(
        name="Get 15-minute reminder for upcoming appointment",
        user_message="Get 15-minute reminder for my upcoming appointment around 2025-10-15T09:00:00+00:00",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_meeting_reminder,
                args={
                    "event_datetime": "2025-10-15T09:00:00+00:00",
                    "reminder_minutes": 15,
                },
            )
        ],
        critics=[
            DatetimeCritic(
                critic_field="event_datetime",
                weight=0.5,
                tolerance=timedelta(seconds=600),
                max_difference=timedelta(hours=1),
            ),
            BinaryCritic(critic_field="reminder_minutes", weight=0.5),
        ],
    )

    return suite

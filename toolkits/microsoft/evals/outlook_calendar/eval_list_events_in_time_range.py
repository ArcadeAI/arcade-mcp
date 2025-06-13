from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_calendar import list_events_in_time_range

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(list_events_in_time_range, "Microsoft")


@tool_eval()
def outlook_calendar_list_events_in_time_range_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Calendar list events tool."""
    suite = EvalSuite(
        name="Outlook Calendar List Events Evaluation",
        system_message=(
            "You are an AI that has access to tools to view and manage calendar events. "
            "The current time date and time is Friday, April 25, 2025, 5:18 PM PST."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List events in time range",
        user_message="what are my meetings on monday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_events_in_time_range,
                args={
                    "start_date_time": "2025-04-28T00:00:00",
                    "end_date_time": "2025-04-28T23:59:59",
                },
            )
        ],
        critics=[
            DatetimeCritic(critic_field="start_date_time", weight=0.5),
            DatetimeCritic(critic_field="end_date_time", weight=0.5),
        ],
    )

    suite.add_case(
        name="List events in time range with limit",
        user_message=(
            "get my first 10 meetings for the next work-week through thursday, "
            "starting tuesday (mon is holiday)"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_events_in_time_range,
                args={
                    "start_date_time": "2025-04-29T00:00:00",
                    "end_date_time": "2025-05-01T23:59:59",
                    "limit": 10,
                },
            )
        ],
        critics=[
            DatetimeCritic(critic_field="start_date_time", weight=0.3),
            DatetimeCritic(critic_field="end_date_time", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.4),
        ],
    )

    return suite

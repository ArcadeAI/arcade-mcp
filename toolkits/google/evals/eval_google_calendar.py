from arcade_google.tools.calendar import create_event, list_events
from arcade_google.tools.models import EventVisibility, TimeSlot, Day

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_tools([create_event, list_events])


@tool_eval()
def calendar_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Calendar tools."""
    suite = EvalSuite(
        name="Calendar Tools Evaluation",
        system_message="You are an AI assistant that can create and list events using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create calendar event",
        user_message="Create a meeting for 'Team Meeting' for next thursday from 11:45pm to 12:15am. Invite johndoe@example.com",
        expected_tool_calls=[
            ExpectedToolCall(
                name="CreateEvent",
                args={
                    "summary": "Team Meeting",
                    "start_date": Day.NEXT_THURSDAY,
                    "start_time": TimeSlot._2345,
                    "end_date": Day.NEXT_FRIDAY,
                    "end_time": TimeSlot._0015,
                    "calendar_id": "primary",
                    "attendee_emails": ["johndoe@example.com"],
                    "description": None,
                    "location": None,
                    "visibility": EventVisibility.DEFAULT,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="summary", weight=0.15),
            BinaryCritic(critic_field="start_date", weight=0.15),
            BinaryCritic(critic_field="start_time", weight=0.15),
            BinaryCritic(critic_field="end_date", weight=0.15),
            BinaryCritic(critic_field="end_time", weight=0.15),
            BinaryCritic(critic_field="attendee_emails", weight=0.15),
            BinaryCritic(critic_field="description", weight=0.1),
        ],
    )

    suite.add_case(
        name="List calendar events",
        user_message="List all my events for next week",
        expected_tool_calls=[
            ExpectedToolCall(
                name="list_events",
                args={
                    "time_min": Day.NEXT_MONDAY.to_date().isoformat() + "T00:00:00Z",
                    "time_max": Day.NEXT_SUNDAY.to_date().isoformat() + "T23:59:59Z",
                    "calendar_id": "primary",
                    "max_results": None,
                    "order_by": None,
                    "single_events": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="time_min", weight=0.2),
            BinaryCritic(critic_field="time_max", weight=0.2),
            BinaryCritic(critic_field="calendar_id", weight=0.2),
            BinaryCritic(critic_field="single_events", weight=0.2),
        ],
    )

    return suite

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_calendar import create_event

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(create_event, "Microsoft")


@tool_eval()
def outlook_calendar_create_event_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Calendar create event tool."""
    suite = EvalSuite(
        name="Outlook Calendar Create Event Evaluation",
        system_message=(
            "You are an AI that has access to tools to view and manage calendar events. "
            "The current time date and time is April 25, 2025, 5:18 PM PST."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create virtual event",
        user_message=(
            "schedule a virtual team meeting 'Standup' tomorrow at 3pm for 1 hour. "
            "john@example.com and sarah@example.com need to be there"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_event,
                args={
                    "subject": "Standup",
                    "start_date_time": "2025-04-26T15:00:00",
                    "end_date_time": "2025-04-26T16:00:00",
                    "attendee_emails": ["john@example.com", "sarah@example.com"],
                    "is_online_meeting": True,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 5),
            BinaryCritic(critic_field="start_date_time", weight=1 / 5),
            BinaryCritic(critic_field="end_date_time", weight=1 / 5),
            BinaryCritic(critic_field="attendee_emails", weight=1 / 5),
            BinaryCritic(critic_field="is_online_meeting", weight=1 / 5),
        ],
    )

    suite.add_case(
        name="Create event with physical location and virtual link",
        user_message=(
            "schedule a team meeting 'All hands' tomorrow at 3pm for 1 hour. "
            "john@example.com and sarah@example.com need to be there. "
            "The meeting will be in Conference Room A, but there will be a virtual link "
            "for those who cannot attend in person."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_event,
                args={
                    "subject": "All hands",
                    "start_date_time": "2025-04-26T15:00:00",
                    "end_date_time": "2025-04-26T16:00:00",
                    "location": "Conference Room A",
                    "attendee_emails": ["john@example.com", "sarah@example.com"],
                    "is_online_meeting": True,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 6),
            BinaryCritic(critic_field="start_date_time", weight=1 / 6),
            BinaryCritic(critic_field="end_date_time", weight=1 / 6),
            SimilarityCritic(critic_field="location", weight=1 / 6),
            BinaryCritic(critic_field="attendee_emails", weight=1 / 6),
            BinaryCritic(critic_field="is_online_meeting", weight=1 / 6),
        ],
    )

    return suite

from datetime import timedelta

from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.models import EventVisibility, SendUpdatesOptions
from arcade_google.tools import (
    create_event,
    delete_event,
    list_calendars,
    list_events,
    update_event,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)

history_after_list_events = [
    {"role": "user", "content": "do i have any events on my calendar for today?"},
    {
        "role": "assistant",
        "content": "Please go to this URL and authorize the action: \n[Link](https://accounts.google.com/o/oauth2/v2/auth?)",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_uHdRlr4z7sFm39ZrPsE5wcdT",
                "type": "function",
                "function": {
                    "name": "Google_ListEvents",
                    "arguments": '{"min_end_datetime":"2024-09-26T00:00:00-07:00","max_start_datetime":"2024-09-27T00:00:00-07:00"}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"events_count": 3, "events": [{"creator": {"email": "john@example.com", "self": true}, "description": "1:1 meeting with Joe", "end": {"dateTime": "2024-09-26T00:15:00-07:00", "timeZone": "America/Los_Angeles"}, "eventType": "default", "htmlLink": "https://www.google.com/calendar/event?eid=01234", "id": "10009199283838467", "location": "622 Rainbow Ave, South San Francisco, CA 94080, USA", "organizer": {"email": "john@example.com", "self": true}, "start": {"dateTime": "2024-09-25T23:15:00-07:00", "timeZone": "America/Los_Angeles"}, "summary": "1:1 meeting"}, {"attendees": [{"email": "joe@example.com", "responseStatus": "accepted"}], "creator": {"email": "john@example.com", "self": true}, "description": "This is just a test", "end": {"dateTime": "2024-09-26T14:00:00-07:00", "timeZone": "America/Los_Angeles"}, "eventType": "default", "htmlLink": "https://www.google.com/calendar/event?eid=OXB2OGFwcmZraWk1N234324", "id": "00099992228181818181", "organizer": {"email": "john@example.com", "self": true}, "start": {"dateTime": "2024-09-26T12:00:00-07:00", "timeZone": "America/Los_Angeles"}, "summary": "API test"}, {"attendees": [{"email": "henry@example.com", "responseStatus": "needsAction"}], "creator": {"email": "john@example.com", "self": true}, "end": {"dateTime": "2024-09-26T17:00:00-07:00", "timeZone": "America/Los_Angeles"}, "eventType": "default", "htmlLink": "https://www.google.com/calendar/event?eid=Z3I1ZzE4b324534556", "id": "gr5g18lf88tfpp3vkareukkc7g", "location": "611 Rainbow Road", "organizer": {"email": "john@example.com", "self": true}, "start": {"dateTime": "2024-09-26T15:00:00-07:00", "timeZone": "America/Los_Angeles"}, "summary": "Focus Time", "visibility": "public"}]}',
        "tool_call_id": "call_uHdRlr4z7sFm39ZrPsE5wcdT",
        "name": "Google_ListEvents",
    },
    {
        "role": "assistant",
        "content": "Yes, you have three events on your calendar for today:\n\n1. **Event:** Test2\n   - **Time:** 23:15 - 00:15 (PST)\n   - **Location:** 611 Gateway Blvd, South San Francisco, CA 94080, USA\n   - **Description:** 1:1 meeting with Joe\n  2. **Event:** API Test\n   - **Time:** 12:00 - 14:00 (PST)\n  **Description:** This is just a test\n   - [View Event](https://www.google.com/calendar/event?eid=OXB2OGFwcmZraWk1NGUwa24xaTNya2lvZDggZXJpY0BhcmNhZGUtYWkuY29t)\n\n3. **Event:** Focus Time\n   - **Time:** 15:00 - 17:00 (PST)\n   - **Location:** 611 Rainbow Road\n   - **Visibility:** Public\n   - [View Event](https://www.google.com/calendar/event?eid=Z3I1ZzE4bGY4OHRmcHAzdmthcmV1a2tjN2cgZXJpY0BhcmNhZGUtYWkuY29t)\n\nIf you need more details or help with anything else, feel free to ask!",
    },
]


@tool_eval()
def calendar_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Calendar tools."""
    suite = EvalSuite(
        name="Calendar Tools Evaluation",
        system_message=(
            "You are an AI assistant that can create, list, update, and delete events using the provided tools. Today is 2024-09-26"
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Cases for list_calendars
    suite.add_case(
        name="List Calendars",
        user_message=("What calendars do I have?"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_calendars,
                args={},
            )
        ],
        critics=[],
    )

    # Cases for create_event
    suite.add_case(
        name="Create calendar event",
        user_message=(
            "Create a meeting for 'Team Meeting' starting on September 26, 2024, from 11:45pm to 12:15am. Invite johndoe@example.com"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_event,
                args={
                    "summary": "Team Meeting",
                    "start_datetime": "2024-09-26T23:45:00",
                    "end_datetime": "2024-09-27T00:15:00",
                    "calendar_id": "primary",
                    "attendee_emails": ["johndoe@example.com"],
                    "visibility": EventVisibility.DEFAULT,
                    "description": "Team Meeting",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="summary", weight=0.2),
            DatetimeCritic(
                critic_field="start_datetime", weight=0.2, tolerance=timedelta(seconds=10)
            ),
            DatetimeCritic(
                critic_field="end_datetime", weight=0.2, tolerance=timedelta(seconds=10)
            ),
            BinaryCritic(critic_field="attendee_emails", weight=0.2),
            BinaryCritic(critic_field="description", weight=0.1),
            BinaryCritic(critic_field="location", weight=0.1),
        ],
    )

    # Cases for list_events
    suite.add_case(
        name="List calendar events",
        user_message="Do I have any events on my calendar today?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_events,
                args={
                    "min_end_datetime": "2024-09-26T00:00:00",
                    "max_start_datetime": "2024-09-27T00:00:00",
                    "calendar_id": "primary",
                    "max_results": 10,
                },
            )
        ],
        critics=[
            DatetimeCritic(
                critic_field="min_end_datetime", weight=0.3, tolerance=timedelta(hours=1)
            ),
            DatetimeCritic(
                critic_field="max_start_datetime", weight=0.3, tolerance=timedelta(hours=1)
            ),
            BinaryCritic(critic_field="calendar_id", weight=0.2),
            BinaryCritic(critic_field="max_results", weight=0.2),
        ],
    )

    # Cases for update_event
    suite.add_case(
        name="Update a calendar event",
        user_message=(
            "Oh no! I can't make it to the API Test since I have lunch with an old friend at that time. "
            "Change my meeting tomorrow at 3pm to 4pm. Let everyone know."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_event,
                args={
                    "event_id": "00099992228181818181",
                    "updated_start_datetime": "2024-09-27T16:00:00",
                    "updated_end_datetime": "2024-09-27T18:00:00",
                    "updated_calendar_id": "primary",
                    "updated_summary": "API Test",
                    "updated_description": "API Test",
                    "updated_location": "611 Gateway Blvd",
                    "updated_visibility": EventVisibility.DEFAULT,
                    "attendee_emails_to_add": None,
                    "attendee_emails_to_remove": None,
                    "send_updates": SendUpdatesOptions.ALL,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="event_id", weight=0.4),
            DatetimeCritic(
                critic_field="updated_start_datetime", weight=0.2, tolerance=timedelta(minutes=15)
            ),
            DatetimeCritic(
                critic_field="updated_end_datetime",
                weight=0.2,
                tolerance=timedelta(minutes=15),
            ),
            BinaryCritic(critic_field="send_updates", weight=0.2),
        ],
        additional_messages=history_after_list_events,
    )

    # Cases for delete_event
    suite.add_case(
        name="Delete a calendar event",
        user_message=(
            "I don't need to have focus time today. Please delete it from my calendar. Don't send any notifications."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=delete_event,
                args={
                    "event_id": "gr5g18lf88tfpp3vkareukkc7g",
                    "calendar_id": "primary",
                    "send_updates": SendUpdatesOptions.NONE,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="event_id", weight=0.6),
            BinaryCritic(critic_field="calendar_id", weight=0.2),
            BinaryCritic(critic_field="send_updates", weight=0.2),
        ],
        additional_messages=history_after_list_events,
    )

    return suite

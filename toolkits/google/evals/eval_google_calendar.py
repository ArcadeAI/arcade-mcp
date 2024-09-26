import arcade_google
from arcade_google.tools.calendar import create_event, delete_event, list_events, update_event
from arcade_google.tools.models import Day, EventVisibility, TimeSlot

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    tool_eval,
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
                    "arguments": '{"max_day":"today","max_time_slot":"23:45","min_day":"today","min_time_slot":"00:00"}',
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
        system_message="You are an AI assistant that can create and list events using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Cases for create_event
    suite.add_case(
        name="Create calendar event",
        user_message="Create a meeting for 'Team Meeting' starting next thursday from 11:45pm to 12:15am. Invite johndoe@example.com",
        expected_tool_calls=[
            (
                create_event,
                {
                    "summary": "Team Meeting",
                    "start_date": Day.NEXT_THURSDAY.value,
                    "start_time": TimeSlot._2345.value,
                    "end_date": Day.NEXT_FRIDAY.value,
                    "end_time": TimeSlot._0015.value,
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

    # Cases for list_events
    suite.add_case(
        name="List calendar events",
        user_message="Do I have any events on my calendar today?",
        expected_tool_calls=[
            (
                list_events,
                {
                    "min_day": Day.TODAY.value,
                    "min_time_slot": TimeSlot._0000.value,
                    "max_day": Day.TOMORROW.value,
                    "max_time_slot": TimeSlot._0000.value,
                    "calendar_id": "primary",
                    "event_types": None,
                    "max_results": 10,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="min_day", weight=0.1),
            BinaryCritic(critic_field="min_time_slot", weight=0.1),
            BinaryCritic(critic_field="max_day", weight=0.1),
            BinaryCritic(critic_field="max_time_slot", weight=0.1),
            BinaryCritic(critic_field="calendar_id", weight=0.1),
            BinaryCritic(critic_field="event_types", weight=0.1),
            BinaryCritic(critic_field="max_results", weight=0.1),
        ],
    )

    # Cases for update_event
    suite.add_case(
        name="Update a calendar event",
        user_message="Oh no! I cant make it to the API Test since i have lunch with an old friend at that time. Change the meeting to 3pm to 4pm please.",
        expected_tool_calls=[
            (
                update_event,
                {
                    "event_id": "00099992228181818181",
                    "updated_start_day": Day.TODAY.value,
                    "updated_start_time": TimeSlot._1500.value,
                    "updated_end_day": Day.TODAY.value,
                    "updated_end_time": TimeSlot._1600.value,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="event_id", weight=0.2),
            BinaryCritic(critic_field="updated_start_day", weight=0.1),
            BinaryCritic(critic_field="updated_start_time", weight=0.1),
            BinaryCritic(critic_field="updated_end_day", weight=0.1),
            BinaryCritic(critic_field="updated_end_time", weight=0.1),
        ],
        additional_messages=history_after_list_events,
    )

    # Cases for delete_event
    suite.add_case(
        name="Delete a calendar event",
        user_message="I don't need to have focus time today. Please delete it from my calendar. Don't send any notifications.",
        expected_tool_calls=[
            (
                delete_event,
                {
                    "event_id": "gr5g18lf88tfpp3vkareukkc7g",
                    "calendar_id": "primary",
                    "send_updates": "none",
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

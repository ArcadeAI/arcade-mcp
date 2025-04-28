get_event_additional_messages = [
    {"role": "system", "content": "Today is 2025-04-22, Tuesday."},
    {"role": "user", "content": "show me my meetings for today"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_def456",
                "type": "function",
                "function": {
                    "name": "Microsoft_ListEventsInTimeRange",
                    "arguments": '{"start_date_time":"2025-04-22T00:00:00","end_date_time":"2025-04-22T23:59:59"}',  # noqa: E501
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"events":[{"attendees":[{"email":"john@example.com","name":"John Smith"},{"email":"alice@example.com","name":"Alice Johnson"}],"body":"Quarterly review meeting","end":{"date_time":"2025-04-22T15:00:00.0000000","time_zone":"Pacific Standard Time"},"has_attachments":true,"id":"AAMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMBAFuxokOLZRtDncM4","importance":"high","is_all_day":false,"is_cancelled":false,"is_online_meeting":true,"is_organizer":true,"location":"Online","online_meeting_url":"https://teams.microsoft.com/l/meetup-join/meeting_id","organizer":{"email":"user@example.com","name":"User Name"},"start":{"date_time":"2025-04-22T14:00:00.0000000","time_zone":"Pacific Standard Time"},"subject":"Q1 Review","web_link":"https://outlook.office365.com/owa/?itemid=AAMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMBAFuxokOLZRtDncM4&exvsurl=1&path=/calendar/item"}],"num_events":1}',  # noqa: E501
        "tool_call_id": "call_def456",
        "name": "Microsoft_ListEventsInTimeRange",
    },
    {
        "role": "assistant",
        "content": "You have 1 meeting scheduled for today:\n\n1. **Q1 Review** - Today, 2:00 PM - 3:00 PM\n   Location: Online\n   Attendees: John Smith, Alice Johnson\n   This is a high importance meeting with attachments.",  # noqa: E501
    },
]

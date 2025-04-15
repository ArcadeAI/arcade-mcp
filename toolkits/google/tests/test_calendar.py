from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from arcade.sdk import ToolAuthorizationContext, ToolContext
from arcade.sdk.errors import RetryableToolError, ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google.models import EventVisibility, SendUpdatesOptions
from arcade_google.tools import (
    create_event,
    delete_event,
    find_time_slots_when_everyone_is_free,
    list_events,
    update_event,
)


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.mark.asyncio
@patch("arcade_google.tools.calendar.build")
async def test_create_event(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the calendar's time zone
    mock_service.calendars().get().execute.return_value = {"timeZone": "America/Los_Angeles"}

    # Case: HttpError during event creation
    mock_service.events().insert().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await create_event(
            context=mock_context,
            summary="Test Event",
            start_datetime="2024-12-31T15:30:00",
            end_datetime="2024-12-31T17:30:00",
            description="Test Description",
            location="Test Location",
            visibility=EventVisibility.PRIVATE,
            attendee_emails=["test@example.com"],
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.calendar.build")
async def test_list_events(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    # Mock the calendar's time zone
    mock_service.calendars().get().execute.return_value = {"timeZone": "America/Los_Angeles"}

    # Mock the events list response
    mock_events_list_response = {
        "items": [
            {
                "creator": {"email": "example@arcade-ai.com", "self": True},
                "end": {"dateTime": "2024-09-27T01:00:00-07:00", "timeZone": "America/Los_Angeles"},
                "eventType": "default",
                "htmlLink": "https://www.google.com/calendar/event?eid=event1",
                "id": "event1",
                "organizer": {"email": "example@arcade-ai.com", "self": True},
                "start": {
                    "dateTime": "2024-09-27T00:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "summary": "Event 1",
            },
            {
                "creator": {"email": "example@arcade-ai.com", "self": True},
                "end": {"dateTime": "2024-09-27T17:00:00-07:00", "timeZone": "America/Los_Angeles"},
                "eventType": "default",
                "htmlLink": "https://www.google.com/calendar/event?eid=event2",
                "id": "event2",
                "organizer": {"email": "example@arcade-ai.com", "self": True},
                "start": {
                    "dateTime": "2024-09-27T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "summary": "Event 2",
            },
        ]
    }
    expected_tool_response = {
        "events_count": len(mock_events_list_response["items"]),
        "events": mock_events_list_response["items"],
    }
    mock_service.events().list().execute.return_value = mock_events_list_response
    response = await list_events(
        context=mock_context,
        min_end_datetime="2024-09-15T09:00:00",
        max_start_datetime="2024-09-16T17:00:00",
    )
    assert response == expected_tool_response

    # Case: HttpError during events listing
    mock_service.events().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_events(
            context=mock_context,
            min_end_datetime="2024-09-15T09:00:00",
            max_start_datetime="2024-09-16T17:00:00",
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.calendar.build")
async def test_update_event(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock retrieval of the event
    mock_service.events().get().execute.side_effect = HttpError(
        resp=MagicMock(status=404),
        content=b'{"error": {"message": "Event not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await update_event(
            context=mock_context,
            event_id="1234567890",
            updated_start_datetime="2024-12-31T00:15:00",
            updated_end_datetime="2024-12-31T01:15:00",
            updated_summary="Updated Event",
            updated_description="Updated Description",
            updated_location="Updated Location",
            updated_visibility=EventVisibility.PRIVATE,
            attendee_emails_to_add=["test@example.com"],
            attendee_emails_to_remove=["test@example2.com"],
            send_updates=SendUpdatesOptions.ALL,
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.calendar.build")
async def test_delete_event(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.events().delete().execute.side_effect = HttpError(
        resp=MagicMock(status=404),
        content=b'{"error": {"message": "Event not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await delete_event(
            context=mock_context,
            event_id="nonexistent_event",
            send_updates=SendUpdatesOptions.ALL,
        )


@pytest.mark.asyncio
@patch("arcade_google.utils.get_now")
@patch("arcade_google.tools.calendar.build")
async def test_find_free_slots_happiest_path_single_user(mock_build, mock_get_now, mock_context):
    calendar_service = MagicMock()
    oauth_service = MagicMock()

    mock_get_now.return_value = datetime(
        2025, 3, 10, 9, 25, 0, tzinfo=ZoneInfo("America/Los_Angeles")
    )
    mock_build.side_effect = [oauth_service, calendar_service]

    oauth_service.userinfo().get().execute.return_value = {
        "email": "example@arcade.dev",
    }

    calendar_service.freebusy().query().execute.return_value = {
        "calendars": {
            "example@arcade.dev": {"busy": []},
        }
    }

    calendar_service.calendars().get().execute.return_value = {
        "timeZone": "America/Los_Angeles",
    }

    response = await find_time_slots_when_everyone_is_free(
        context=mock_context,
        email_addresses=["example@arcade.dev"],
        start_date="2025-03-10",
        end_date="2025-03-11",
        start_time_boundary="08:00",
        end_time_boundary="18:00",
    )

    assert response == {
        "free_slots": [
            {
                "start": {
                    "datetime": "2025-03-10T09:25:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T18:00:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-11T08:00:00-07:00",
                    "weekday": "Tuesday",
                },
                "end": {
                    "datetime": "2025-03-11T18:00:00-07:00",
                    "weekday": "Tuesday",
                },
            },
        ],
        "timezone": "America/Los_Angeles",
    }


@pytest.mark.asyncio
@patch("arcade_google.utils.get_now")
@patch("arcade_google.tools.calendar.build")
async def test_find_free_slots_happiest_path_single_user_with_busy_times(
    mock_build, mock_get_now, mock_context
):
    calendar_service = MagicMock()
    oauth_service = MagicMock()

    mock_get_now.return_value = datetime(
        2025, 3, 10, 9, 25, 0, tzinfo=ZoneInfo("America/Los_Angeles")
    )
    mock_build.side_effect = [oauth_service, calendar_service]

    oauth_service.userinfo().get().execute.return_value = {
        "email": "example@arcade.dev",
    }

    calendar_service.freebusy().query().execute.return_value = {
        "calendars": {
            "example@arcade.dev": {
                "busy": [
                    {
                        "start": "2025-03-10T11:00:00-07:00",
                        "end": "2025-03-10T12:00:00-07:00",
                    },
                    {
                        "start": "2025-03-10T14:15:00-07:00",
                        "end": "2025-03-10T14:30:00-07:00",
                    },
                ]
            },
        }
    }

    calendar_service.calendars().get().execute.return_value = {
        "timeZone": "America/Los_Angeles",
    }

    response = await find_time_slots_when_everyone_is_free(
        context=mock_context,
        email_addresses=["example@arcade.dev"],
        start_date="2025-03-10",
        end_date="2025-03-11",
        start_time_boundary="08:00",
        end_time_boundary="18:00",
    )

    assert response == {
        "free_slots": [
            {
                "start": {
                    "datetime": "2025-03-10T09:25:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T11:00:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-10T12:00:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T14:15:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-10T14:30:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T18:00:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-11T08:00:00-07:00",
                    "weekday": "Tuesday",
                },
                "end": {
                    "datetime": "2025-03-11T18:00:00-07:00",
                    "weekday": "Tuesday",
                },
            },
        ],
        "timezone": "America/Los_Angeles",
    }


@pytest.mark.asyncio
@patch("arcade_google.utils.get_now")
@patch("arcade_google.tools.calendar.build")
async def test_find_free_slots_happiest_path_multiple_users_with_busy_times(
    mock_build, mock_get_now, mock_context
):
    calendar_service = MagicMock()
    oauth_service = MagicMock()

    mock_get_now.return_value = datetime(
        2025, 3, 10, 9, 25, 0, tzinfo=ZoneInfo("America/Los_Angeles")
    )
    mock_build.side_effect = [oauth_service, calendar_service]

    oauth_service.userinfo().get().execute.return_value = {
        "email": "example@arcade.dev",
    }

    calendar_service.freebusy().query().execute.return_value = {
        "calendars": {
            "example@arcade.dev": {
                "busy": [
                    {
                        "start": "2025-03-10T11:00:00-07:00",
                        "end": "2025-03-10T12:00:00-07:00",
                    },
                    {
                        "start": "2025-03-10T14:15:00-07:00",
                        "end": "2025-03-10T14:30:00-07:00",
                    },
                ]
            },
            "example2@arcade.dev": {
                "busy": [
                    {
                        "start": "2025-03-10T11:30:00-07:00",
                        "end": "2025-03-10T12:45:00-07:00",
                    },
                    {
                        "start": "2025-03-11T06:00:00-07:00",
                        "end": "2025-03-11T07:00:00-07:00",
                    },
                ]
            },
        }
    }

    calendar_service.calendars().get().execute.return_value = {
        "timeZone": "America/Los_Angeles",
    }

    response = await find_time_slots_when_everyone_is_free(
        context=mock_context,
        email_addresses=["example@arcade.dev", "example2@arcade.dev"],
        start_date="2025-03-10",
        end_date="2025-03-11",
        start_time_boundary="08:00",
        end_time_boundary="18:00",
    )

    assert response == {
        "free_slots": [
            {
                "start": {
                    "datetime": "2025-03-10T09:25:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T11:00:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-10T12:45:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T14:15:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-10T14:30:00-07:00",
                    "weekday": "Monday",
                },
                "end": {
                    "datetime": "2025-03-10T18:00:00-07:00",
                    "weekday": "Monday",
                },
            },
            {
                "start": {
                    "datetime": "2025-03-11T08:00:00-07:00",
                    "weekday": "Tuesday",
                },
                "end": {
                    "datetime": "2025-03-11T18:00:00-07:00",
                    "weekday": "Tuesday",
                },
            },
        ],
        "timezone": "America/Los_Angeles",
    }


@pytest.mark.asyncio
@patch("arcade_google.utils.get_now")
@patch("arcade_google.tools.calendar.build")
async def test_find_free_slots_with_google_calendar_error_not_found(
    mock_build, mock_get_now, mock_context
):
    calendar_service = MagicMock()
    oauth_service = MagicMock()

    mock_get_now.return_value = datetime(
        2025, 3, 10, 9, 25, 0, tzinfo=ZoneInfo("America/Los_Angeles")
    )
    mock_build.side_effect = [oauth_service, calendar_service]

    oauth_service.userinfo().get().execute.return_value = {
        "email": "example@arcade.dev",
    }

    calendar_service.freebusy().query().execute.return_value = {
        "calendars": {
            "example@arcade.dev": {
                "busy": [
                    {
                        "start": "2025-03-10T11:00:00-07:00",
                        "end": "2025-03-10T12:00:00-07:00",
                    },
                    {
                        "start": "2025-03-10T14:15:00-07:00",
                        "end": "2025-03-10T14:30:00-07:00",
                    },
                ]
            },
            "example2@arcade.dev": {
                "errors": [
                    {
                        "reason": "notFound",
                        "domain": "calendar",
                    }
                ]
            },
        }
    }

    calendar_service.calendars().get().execute.return_value = {
        "timeZone": "America/Los_Angeles",
    }

    with pytest.raises(RetryableToolError):
        await find_time_slots_when_everyone_is_free(
            context=mock_context,
            email_addresses=["example@arcade.dev", "example2@arcade.dev"],
            start_date="2025-03-10",
            end_date="2025-03-11",
            start_time_boundary="08:00",
            end_time_boundary="18:00",
        )

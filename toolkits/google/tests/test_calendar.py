from unittest.mock import MagicMock, patch

import pytest
from arcade.sdk import ToolAuthorizationContext, ToolContext
from arcade.sdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google.tools.calendar import create_event, delete_event, list_events, update_event
from arcade_google.tools.models import EventVisibility, SendUpdatesOptions


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

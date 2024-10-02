from unittest.mock import MagicMock, patch

import pytest
from arcade_google.tools.calendar import create_event, delete_event, list_events, update_event
from arcade_google.tools.models import Day, EventVisibility, SendUpdatesOptions, TimeSlot
from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolAuthorizationContext, ToolContext


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

    # Case: HttpError
    mock_service.events().insert().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await create_event(
            context=mock_context,
            summary="Test Event",
            start_date=Day.TODAY,
            start_time=TimeSlot._1615,
            end_date=Day.TODAY,
            end_time=TimeSlot._1715,
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

    # Case: min time is after max time. list_events tool should swap the times and still return the events
    mock_events_list_response = {
        "items": [
            {
                "creator": {"email": "example@arcade-ai.com", "self": True},
                "end": {"dateTime": "2024-09-27T01:00:00-07:00", "timeZone": "America/Los_Angeles"},
                "eventType": "default",
                "htmlLink": "https://www.google.com/calendar/event?eid=N2pmYjZ0ZmNnMGNydG5scmhkY2JvZWc4OGIgZXJpY0BhcmNhZGUtYWku",
                "id": "7jfb6tfcg0crtnlrhdcboeg88b",
                "organizer": {"email": "example@arcade-ai.com", "self": True},
                "start": {
                    "dateTime": "2024-09-27T00:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "summary": "teST",
            },
            {
                "creator": {"email": "example@arcade-ai.com", "self": True},
                "end": {"dateTime": "2024-09-27T17:00:00-07:00", "timeZone": "America/Los_Angeles"},
                "eventType": "default",
                "htmlLink": "https://www.google.com/calendar/event?eid=MjZvYnRoc2xtMWMzbG5mdG10bzk4cDcxaGMgZXJpY0BhcmNhZGUtYWku",
                "id": "26obthslm1c3lnftmto98p71hc",
                "organizer": {"email": "example@arcade-ai.com", "self": True},
                "start": {
                    "dateTime": "2024-09-27T14:00:00-07:00",
                    "timeZone": "America/Los_Angeles",
                },
                "summary": "New Event",
            },
        ]
    }
    expected_tool_response = {
        "events_count": len(mock_events_list_response["items"]),
        "events": mock_events_list_response["items"],
    }
    mock_service.events().list().execute.return_value = mock_events_list_response
    message = await list_events(
        context=mock_context,
        min_day=Day.TODAY,
        min_time_slot=TimeSlot._1615,
        max_day=Day.TODAY,
        max_time_slot=TimeSlot._1515,
    )
    assert message == expected_tool_response

    # Case: HttpError
    mock_service.events().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_events(
            context=mock_context,
            min_day=Day.TODAY,
            min_time_slot=TimeSlot._1615,
            max_day=Day.TOMORROW,
            max_time_slot=TimeSlot._1815,
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.calendar.build")
async def test_update_event(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.events().update().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Event not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await update_event(
            context=mock_context,
            event_id="1234567890",
            updated_start_day=Day.NEXT_FRIDAY,
            updated_start_time=TimeSlot._0015,
            updated_end_day=Day.NEXT_FRIDAY,
            updated_end_time=TimeSlot._0115,
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
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Event not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await delete_event(
            context=mock_context,
            event_id="nonexistent_event",
        )

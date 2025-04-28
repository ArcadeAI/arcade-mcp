import pytest
from msgraph.generated.models.attendee import Attendee as GraphAttendee
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone as GraphDateTimeTimeZone
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.event import Event as GraphEvent
from msgraph.generated.models.location import Location as GraphLocation
from msgraph.generated.models.recipient import Recipient as GraphRecipient
from msgraph.generated.models.response_status import ResponseStatus as GraphResponseStatus
from msgraph.generated.models.response_type import ResponseType as GraphResponseType

from arcade_microsoft.outlook_calendar.models import (
    Attendee,
    DateTimeTimeZone,
    Event,
    Organizer,
    ResponseStatus,
)


class DummyBody:
    def __init__(self, content):
        self.content = content


class DummyEventType:
    def __init__(self, value):
        self.value = value


class DummyImportance:
    def __init__(self, value):
        self.value = value


class DummyFreeBusyStatus:
    def __init__(self, value):
        self.value = value


class DummyResponseType:
    def __init__(self, value):
        self.value = value


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (
            {"name": "John Doe", "address": "john.doe@example.com", "response": "accepted"},
            {"name": "John Doe", "address": "john.doe@example.com", "response": "accepted"},
        ),
        (
            {"name": "", "address": "anonymous@example.com", "response": "tentativelyAccepted"},
            {"name": "", "address": "anonymous@example.com", "response": "tentativelyAccepted"},
        ),
        (
            {"name": None, "address": None, "response": "none"},
            {"name": "", "address": "", "response": "none"},
        ),
    ],
)
def test_attendee_conversion(input_data, expected):
    sdk_attendee = GraphAttendee()
    sdk_attendee.email_address = GraphEmailAddress()
    sdk_attendee.email_address.name = input_data["name"]
    sdk_attendee.email_address.address = input_data["address"]
    sdk_attendee.status = GraphResponseStatus()
    sdk_attendee.status.response = GraphResponseType(input_data["response"])

    # Test from_sdk method
    attendee = Attendee.from_sdk(sdk_attendee)
    assert attendee.name == expected["name"]
    assert attendee.address == expected["address"]
    assert attendee.response == expected["response"]

    # Test to_dict method
    dict_result = attendee.to_dict()
    assert dict_result == expected

    # Test to_sdk method
    sdk_result = attendee.to_sdk()
    assert sdk_result.email_address.name == expected["name"]
    assert sdk_result.email_address.address == expected["address"]
    assert sdk_result.status.response == GraphResponseType(expected["response"])


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (
            {"name": "Jane Smith", "address": "jane.smith@example.com"},
            {"name": "Jane Smith", "address": "jane.smith@example.com"},
        ),
        (
            {"name": "", "address": "unknown@example.com"},
            {"name": "", "address": "unknown@example.com"},
        ),
        ({"name": None, "address": None}, {"name": "", "address": ""}),
    ],
)
def test_organizer_conversion(input_data, expected):
    sdk_organizer = GraphRecipient()
    sdk_organizer.email_address = GraphEmailAddress()
    sdk_organizer.email_address.name = input_data["name"]
    sdk_organizer.email_address.address = input_data["address"]

    # Test from_sdk method
    organizer = Organizer.from_sdk(sdk_organizer)
    assert organizer.name == expected["name"]
    assert organizer.address == expected["address"]

    # Test to_dict method
    dict_result = organizer.to_dict()
    assert dict_result == expected

    # Test to_sdk method
    sdk_result = organizer.to_sdk()
    assert sdk_result.email_address.name == expected["name"]
    assert sdk_result.email_address.address == expected["address"]


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (
            {"date_time": "2023-05-10T14:00:00", "time_zone": "Pacific Standard Time"},
            {"dateTime": "2023-05-10T14:00:00", "timeZone": "Pacific Standard Time"},
        ),
        ({"date_time": "", "time_zone": "UTC"}, {"dateTime": "", "timeZone": "UTC"}),
        ({"date_time": None, "time_zone": None}, {"dateTime": "", "timeZone": ""}),
    ],
)
def test_date_time_time_zone_conversion(input_data, expected):
    sdk_date_time = GraphDateTimeTimeZone()
    sdk_date_time.date_time = input_data["date_time"]
    sdk_date_time.time_zone = input_data["time_zone"]

    # Test from_sdk method
    date_time_tz = DateTimeTimeZone.from_sdk(sdk_date_time)
    assert date_time_tz.date_time == (input_data["date_time"] or "")
    assert date_time_tz.time_zone == (input_data["time_zone"] or "")

    # Test to_dict method
    dict_result = date_time_tz.to_dict()
    assert dict_result == expected

    # Test to_sdk method
    sdk_result = date_time_tz.to_sdk()
    assert sdk_result.date_time == date_time_tz.date_time
    assert sdk_result.time_zone == date_time_tz.time_zone


@pytest.mark.parametrize(
    "input_data, expected",
    [
        ({"response": "accepted"}, {"response": "accepted"}),
        ({"response": "declined"}, {"response": "declined"}),
        ({"response": "none"}, {"response": "none"}),
    ],
)
def test_response_status_conversion(input_data, expected):
    sdk_response_status = GraphResponseStatus()
    sdk_response_status.response = GraphResponseType(input_data["response"])

    # Test from_sdk method
    response_status = ResponseStatus.from_sdk(sdk_response_status)
    assert response_status.response == expected["response"]

    # Test to_dict method
    dict_result = response_status.to_dict()
    assert dict_result == expected

    # Test to_sdk method
    sdk_result = response_status.to_sdk()
    assert sdk_result.response == GraphResponseType(expected["response"])


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (
            {
                "body_content": "<p>Team <b>Meeting</b></p>",
                "has_attachments": True,
                "importance": "high",
                "is_all_day": False,
                "is_cancelled": False,
                "is_draft": False,
                "is_online_meeting": True,
                "is_organizer": True,
                "location": "Conference Room A",
                "online_meeting_url": "https://teams.microsoft.com/l/meetup-join/123",
                "id": "event-123",
                "show_as": "busy",
                "subject": "Weekly Team Sync",
                "type": "singleInstance",
                "web_link": "https://outlook.office.com/calendar/item/123",
                "attendees": [
                    {"name": "Alice", "address": "alice@example.com", "response": "accepted"},
                    {
                        "name": "Bob",
                        "address": "bob@example.com",
                        "response": "tentativelyAccepted",
                    },
                ],
                "organizer": {"name": "Manager", "address": "manager@example.com"},
                "start": {"date_time": "2023-05-10T10:00:00", "time_zone": "Eastern Standard Time"},
                "end": {"date_time": "2023-05-10T11:00:00", "time_zone": "Eastern Standard Time"},
                "response_status": {"response": "accepted"},
            },
            {
                "body": "Team Meeting",
                "has_attachments": True,
                "importance": "high",
                "is_all_day": False,
                "is_cancelled": False,
                "is_draft": False,
                "is_online_meeting": True,
                "is_organizer": True,
                "location": "Conference Room A",
                "online_meeting_url": "https://teams.microsoft.com/l/meetup-join/123",
                "id": "event-123",
                "show_as": "busy",
                "subject": "Weekly Team Sync",
                "type": "singleInstance",
                "web_link": "https://outlook.office.com/calendar/item/123",
                "event_id": "event-123",
                "attendees": [
                    {"name": "Alice", "address": "alice@example.com", "response": "accepted"},
                    {
                        "name": "Bob",
                        "address": "bob@example.com",
                        "response": "tentativelyAccepted",
                    },
                ],
                "organizer": {"name": "Manager", "address": "manager@example.com"},
                "start": {"dateTime": "2023-05-10T10:00:00", "timeZone": "Eastern Standard Time"},
                "end": {"dateTime": "2023-05-10T11:00:00", "timeZone": "Eastern Standard Time"},
                "response_status": {"response": "accepted"},
            },
        ),
        (
            {
                "body_content": "<p>All day <i>event</i> description</p>",
                "has_attachments": False,
                "importance": "normal",
                "is_all_day": True,
                "is_cancelled": True,
                "is_draft": True,
                "is_online_meeting": False,
                "is_organizer": False,
                "location": "",
                "online_meeting_url": "",
                "id": "event-456",
                "show_as": "free",
                "subject": "Company Holiday",
                "type": "occurrence",
                "web_link": "https://outlook.office.com/calendar/item/456",
                "attendees": [],
                "organizer": {"name": "HR Department", "address": "hr@example.com"},
                "start": {"date_time": "2023-07-04T00:00:00", "time_zone": "UTC"},
                "end": {"date_time": "2023-07-05T00:00:00", "time_zone": "UTC"},
                "response_status": {"response": "notResponded"},
            },
            {
                "body": "All day event description",
                "has_attachments": False,
                "importance": "normal",
                "is_all_day": True,
                "is_cancelled": True,
                "is_draft": True,
                "is_online_meeting": False,
                "is_organizer": False,
                "location": "",
                "online_meeting_url": "",
                "id": "event-456",
                "show_as": "free",
                "subject": "Company Holiday",
                "type": "occurrence",
                "web_link": "https://outlook.office.com/calendar/item/456",
                "event_id": "event-456",
                "attendees": [],
                "organizer": {"name": "HR Department", "address": "hr@example.com"},
                "start": {"dateTime": "2023-07-04T00:00:00", "timeZone": "UTC"},
                "end": {"dateTime": "2023-07-05T00:00:00", "timeZone": "UTC"},
                "response_status": {"response": "notResponded"},
            },
        ),
    ],
)
def test_event_conversion(input_data, expected):
    def make_graph_attendee(attendee_data):
        attendee = GraphAttendee()
        attendee.email_address = GraphEmailAddress()
        attendee.email_address.name = attendee_data.get("name", "")
        attendee.email_address.address = attendee_data.get("address", "")
        attendee.status = GraphResponseStatus()
        attendee.status.response = GraphResponseType(attendee_data.get("response", ""))
        return attendee

    def make_graph_organizer(organizer_data):
        organizer = GraphRecipient()
        organizer.email_address = GraphEmailAddress()
        organizer.email_address.name = organizer_data.get("name", "")
        organizer.email_address.address = organizer_data.get("address", "")
        return organizer

    def make_graph_date_time(date_time_data):
        date_time = GraphDateTimeTimeZone()
        date_time.date_time = date_time_data.get("date_time", "")
        date_time.time_zone = date_time_data.get("time_zone", "")
        return date_time

    sdk_event = GraphEvent()
    sdk_event.body = DummyBody(input_data["body_content"])
    sdk_event.has_attachments = input_data["has_attachments"]
    sdk_event.importance = DummyImportance(input_data["importance"])
    sdk_event.is_all_day = input_data["is_all_day"]
    sdk_event.is_cancelled = input_data["is_cancelled"]
    sdk_event.is_draft = input_data["is_draft"]
    sdk_event.is_online_meeting = input_data["is_online_meeting"]
    sdk_event.is_organizer = input_data["is_organizer"]
    sdk_event.location = GraphLocation(display_name=input_data["location"])
    sdk_event.online_meeting_url = input_data["online_meeting_url"]
    sdk_event.id = input_data["id"]
    sdk_event.show_as = DummyFreeBusyStatus(input_data["show_as"])
    sdk_event.subject = input_data["subject"]
    sdk_event.type = DummyEventType(input_data["type"])
    sdk_event.web_link = input_data["web_link"]
    sdk_event.attendees = [make_graph_attendee(a) for a in input_data["attendees"]]
    sdk_event.organizer = make_graph_organizer(input_data["organizer"])
    sdk_event.start = make_graph_date_time(input_data["start"])
    sdk_event.end = make_graph_date_time(input_data["end"])
    sdk_event.response_status = GraphResponseStatus()
    sdk_event.response_status.response = GraphResponseType(
        input_data["response_status"]["response"]
    )

    # Test from_sdk method
    event = Event.from_sdk(sdk_event)
    assert event.body == expected["body"]
    assert event.has_attachments == expected["has_attachments"]
    assert event.importance == expected["importance"]
    assert event.is_all_day == expected["is_all_day"]
    assert event.is_cancelled == expected["is_cancelled"]
    assert event.is_draft == expected["is_draft"]
    assert event.is_online_meeting == expected["is_online_meeting"]
    assert event.is_organizer == expected["is_organizer"]
    assert event.location == expected["location"]
    assert event.online_meeting_url == expected["online_meeting_url"]
    assert event.id == expected["id"]
    assert event.show_as == expected["show_as"]
    assert event.subject == expected["subject"]
    assert event.type == expected["type"]
    assert event.web_link == expected["web_link"]
    assert event.event_id == expected["event_id"]
    assert len(event.attendees) == len(expected["attendees"])
    for i, attendee in enumerate(event.attendees):
        assert attendee.name == expected["attendees"][i]["name"]
        assert attendee.address == expected["attendees"][i]["address"]
        assert attendee.response == expected["attendees"][i]["response"]
    if event.start:
        assert event.start.date_time == expected["start"]["dateTime"]
        assert event.start.time_zone == expected["start"]["timeZone"]
    if event.end:
        assert event.end.date_time == expected["end"]["dateTime"]
        assert event.end.time_zone == expected["end"]["timeZone"]
    if event.organizer:
        assert event.organizer.name == expected["organizer"]["name"]
        assert event.organizer.address == expected["organizer"]["address"]
    if event.response_status:
        assert event.response_status.response == expected["response_status"]["response"]

    # Test to_dict method
    dict_result = event.to_dict()
    assert dict_result["body"] == expected["body"]
    assert dict_result["subject"] == expected["subject"]
    assert dict_result["event_id"] == expected["event_id"]

    # Test to_sdk method
    sdk_result = event.to_sdk()
    assert sdk_result.subject == event.subject
    assert sdk_result.is_all_day == event.is_all_day
    assert sdk_result.location.display_name == event.location
    assert len(sdk_result.attendees) == len(event.attendees)

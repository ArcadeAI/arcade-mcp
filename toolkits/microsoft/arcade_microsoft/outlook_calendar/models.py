import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup
from msgraph.generated.models.attendee import Attendee as GraphAttendee
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone as GraphDateTimeTimeZone
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.event import Event as GraphEvent
from msgraph.generated.models.event_type import EventType as GraphEventType
from msgraph.generated.models.free_busy_status import FreeBusyStatus as GraphFreeBusyStatus
from msgraph.generated.models.importance import Importance as GraphImportance
from msgraph.generated.models.item_body import ItemBody as GraphItemBody
from msgraph.generated.models.location import Location as GraphLocation
from msgraph.generated.models.recipient import Recipient as GraphRecipient
from msgraph.generated.models.response_status import ResponseStatus as GraphResponseStatus
from msgraph.generated.models.response_type import ResponseType as GraphResponseType


@dataclass
class Attendee:
    """An attendee of a calendar event."""

    name: str = ""
    address: str = ""
    response: str = ""

    @classmethod
    def from_sdk(cls, attendee: GraphAttendee) -> "Attendee":
        """Convert a Microsoft Graph SDK Attendee object to an Attendee dataclass."""
        return cls(
            name=attendee.email_address.name
            if attendee.email_address and attendee.email_address.name
            else "",
            address=attendee.email_address.address
            if attendee.email_address and attendee.email_address.address
            else "",
            response=attendee.status.response
            if attendee.status and attendee.status.response
            else "",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "address": self.address,
            "response": self.response,
        }

    def to_sdk(self) -> GraphAttendee:
        """Convert an Attendee dataclass to a Microsoft Graph SDK Attendee object."""
        return GraphAttendee(
            email_address=GraphEmailAddress(name=self.name, address=self.address),
            status=GraphResponseStatus(
                response=GraphResponseType(self.response)
                if self.response
                else GraphResponseType.None_
            ),
        )


@dataclass
class Organizer:
    """The organizer of an event."""

    name: str = ""
    address: str = ""

    @classmethod
    def from_sdk(cls, organizer: GraphRecipient) -> "Organizer":
        """Convert a Microsoft Graph SDK Organizer object to an Organizer dataclass."""
        return cls(
            name=organizer.email_address.name
            if organizer.email_address and organizer.email_address.name
            else "",
            address=organizer.email_address.address
            if organizer.email_address and organizer.email_address.address
            else "",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "address": self.address,
        }

    def to_sdk(self) -> GraphRecipient:
        """Convert an Organizer dataclass to a Microsoft Graph SDK Organizer object."""
        recipient = GraphRecipient(
            email_address=GraphEmailAddress(name=self.name, address=self.address)
        )
        return recipient


@dataclass
class DateTimeTimeZone:
    """Time information for an event."""

    date_time: str = ""
    time_zone: str = ""

    @classmethod
    def from_sdk(cls, date_time_time_zone: GraphDateTimeTimeZone) -> "DateTimeTimeZone":
        """Convert a Microsoft Graph SDK DateTimeTimeZone object to a TimeInfo dataclass."""
        return cls(
            date_time=date_time_time_zone.date_time or "",
            time_zone=date_time_time_zone.time_zone or "",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "dateTime": self.date_time,
            "timeZone": self.time_zone,
        }

    def to_sdk(self) -> GraphDateTimeTimeZone:
        """Convert a TimeInfo dataclass to a Microsoft Graph SDK DateTimeTimeZone object."""
        return GraphDateTimeTimeZone(date_time=self.date_time, time_zone=self.time_zone)


@dataclass
class ResponseStatus:
    """The response status for an event."""

    response: str = ""

    @classmethod
    def from_sdk(cls, response_status: GraphResponseStatus) -> "ResponseStatus":
        """Convert a Microsoft Graph SDK ResponseStatus object to a ResponseStatus dataclass."""
        response_value = (
            str(response_status.response.value)
            if response_status.response and hasattr(response_status.response, "value")
            else ""
        )
        return cls(response=response_value)

    def to_dict(self) -> dict[str, str]:
        return {
            "response": self.response,
        }

    def to_sdk(self) -> GraphResponseStatus:
        """Convert a ResponseStatus dataclass to a Microsoft Graph SDK ResponseStatus object."""
        return GraphResponseStatus(response=GraphResponseType(self.response))


@dataclass
class Event:
    """A calendar event in Outlook."""

    attendees: list[Attendee] = field(default_factory=list)
    body: str = ""
    end: DateTimeTimeZone | None = None
    has_attachments: bool = False
    importance: str = ""
    is_all_day: bool = False
    is_cancelled: bool = False
    is_draft: bool = False
    is_online_meeting: bool = False
    is_organizer: bool = False
    location: str = ""
    online_meeting_url: str = ""
    organizer: Organizer | None = None
    id: str = ""
    response_status: ResponseStatus | None = None
    show_as: str = ""
    start: DateTimeTimeZone | None = None
    subject: str = ""
    type: str = ""
    web_link: str = ""
    event_id: str = ""  # The unique identifier of the event. Read-only.

    @staticmethod
    def _safe_str(value: Any) -> str:
        if not value:
            return ""
        if isinstance(value, bytes | bytearray):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    @staticmethod
    def _safe_bool(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def _parse_body(mime: str) -> str:
        if not mime:
            return ""
        soup = BeautifulSoup(mime, "html.parser")
        text = soup.get_text(separator=" ")
        # Replace multiple newlines with a single newline
        text = re.sub(r"\n+", "\n", text)
        # Replace multiple spaces with a single space
        text = re.sub(r"\s+", " ", text)
        # Replace sequences of dots (likely from horizontal lines) with a single newline
        text = re.sub(r"\.{3,}", "\n---\n", text)
        # Remove leading/trailing whitespace from each line
        text = "\n".join(line.strip() for line in text.split("\n"))
        return text

    @classmethod
    def from_sdk(cls, event: GraphEvent) -> "Event":
        """Convert a Microsoft Graph SDK Event object to an Event dataclass."""
        body_mime = event.body.content if event.body and event.body.content else ""
        body = cls._parse_body(body_mime)

        attendees = [Attendee.from_sdk(a) for a in event.attendees if a] if event.attendees else []
        start = DateTimeTimeZone.from_sdk(event.start) if event.start else None
        end = DateTimeTimeZone.from_sdk(event.end) if event.end else None
        organizer = Organizer.from_sdk(event.organizer) if event.organizer else None
        response_status = (
            ResponseStatus.from_sdk(event.response_status) if event.response_status else None
        )

        return cls(
            attendees=attendees,
            body=body,
            end=end,
            has_attachments=cls._safe_bool(event.has_attachments),
            importance=cls._safe_str(str(event.importance.value)) if event.importance else "",
            is_all_day=cls._safe_bool(event.is_all_day),
            is_cancelled=cls._safe_bool(event.is_cancelled),
            is_draft=cls._safe_bool(event.is_draft),
            is_online_meeting=cls._safe_bool(event.is_online_meeting),
            is_organizer=cls._safe_bool(event.is_organizer),
            location=cls._safe_str(event.location.display_name if event.location else ""),
            online_meeting_url=cls._safe_str(event.online_meeting_url),
            organizer=organizer,
            id=cls._safe_str(event.id),
            response_status=response_status,
            show_as=cls._safe_str(str(event.show_as.value)) if event.show_as else "",
            start=start,
            subject=cls._safe_str(event.subject),
            type=cls._safe_str(str(event.type.value)) if event.type else "",
            web_link=cls._safe_str(event.web_link),
            event_id=cls._safe_str(event.id),
        )

    def to_dict(self) -> dict[str, Any]:
        """Converts the Event dataclass to a dictionary."""
        return {
            "attendees": [attendee.to_dict() for attendee in self.attendees],
            "body": self.body,
            "end": self.end.to_dict() if self.end else None,
            "has_attachments": self.has_attachments,
            "importance": self.importance,
            "is_all_day": self.is_all_day,
            "is_cancelled": self.is_cancelled,
            "is_draft": self.is_draft,
            "is_online_meeting": self.is_online_meeting,
            "is_organizer": self.is_organizer,
            "location": self.location,
            "online_meeting_url": self.online_meeting_url,
            "organizer": self.organizer.to_dict() if self.organizer else None,
            "id": self.id,
            "response_status": self.response_status.to_dict() if self.response_status else None,
            "show_as": self.show_as,
            "start": self.start.to_dict() if self.start else None,
            "subject": self.subject,
            "type": self.type,
            "web_link": self.web_link,
            "event_id": self.event_id,
        }

    def to_sdk(self) -> GraphEvent:
        """Convert an Event dataclass to a Microsoft Graph SDK Event object."""
        return GraphEvent(
            attendees=[attendee.to_sdk() for attendee in self.attendees],
            body=GraphItemBody(content=self.body),
            end=self.end.to_sdk() if self.end else None,
            has_attachments=self.has_attachments,
            importance=GraphImportance(self.importance) if self.importance else None,
            is_all_day=self.is_all_day,
            is_cancelled=self.is_cancelled,
            is_draft=self.is_draft,
            is_online_meeting=self.is_online_meeting,
            is_organizer=self.is_organizer,
            location=GraphLocation(display_name=self.location),
            online_meeting_url=self.online_meeting_url,
            organizer=self.organizer.to_sdk() if self.organizer else None,
            id=self.id,
            response_status=self.response_status.to_sdk() if self.response_status else None,
            show_as=GraphFreeBusyStatus(self.show_as) if self.show_as else None,
            start=self.start.to_sdk() if self.start else None,
            subject=self.subject,
            type=GraphEventType(self.type) if self.type else None,
            web_link=self.web_link,
        )

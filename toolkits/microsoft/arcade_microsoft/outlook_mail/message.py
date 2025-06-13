import re
from dataclasses import dataclass, field
from typing import Any, cast

from bs4 import BeautifulSoup
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message as GraphMessage
from msgraph.generated.models.recipient import Recipient as GraphRecipient


@dataclass
class Recipient:
    """A recipient of an email message."""

    email_address: str = ""
    name: str = ""

    @classmethod
    def from_sdk(cls, recipient: GraphRecipient) -> "Recipient":
        """Convert a Microsoft Graph SDK Recipient object to a Recipient dataclass."""
        address = (
            recipient.email_address.address
            if recipient and recipient.email_address and recipient.email_address.address
            else ""
        )
        name = (
            recipient.email_address.name
            if recipient and recipient.email_address and recipient.email_address.name
            else ""
        )
        return cls(email_address=address, name=name)

    def to_dict(self) -> dict[str, str]:
        return {"email_address": self.email_address, "name": self.name}

    def to_sdk(self) -> GraphRecipient:
        """Converts the Recipient dataclass to a Microsoft Graph SDK Recipient object."""
        recipient = GraphRecipient()
        email_address = EmailAddress()
        email_address.address = self.email_address
        email_address.name = self.name
        recipient.email_address = email_address
        return recipient


@dataclass
class Message:
    """An email message in Outlook."""

    bcc_recipients: list[Recipient] = field(default_factory=list)
    cc_recipients: list[Recipient] = field(default_factory=list)
    reply_to: list[Recipient] = field(default_factory=list)
    to_recipients: list[Recipient] = field(default_factory=list)
    from_: Recipient = field(default_factory=Recipient)
    subject: str = ""
    body: str = ""
    conversation_id: str = ""
    conversation_index: str = ""
    flag: dict[str, str] = field(default_factory=dict)
    has_attachments: bool = False
    importance: str = ""
    is_read: bool = False
    received_date_time: str = ""
    web_link: str = ""
    is_draft: bool = True
    message_id: str = ""  # The unique identifier of the email message. Read-only.

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
        # Remove leading/trailing whitespace from each line
        text = "\n".join(line.strip() for line in text.split("\n"))

        return text

    @staticmethod
    def _parse_importance(value: Any) -> str:
        return cast(str, value.value) if getattr(value, "value", None) else ""

    @staticmethod
    def _parse_flag(flag: Any) -> dict[str, str]:
        if not flag:
            return {"flag_status": "", "due_date_time": ""}
        status = flag.flag_status.value if getattr(flag, "flag_status", None) else ""
        due = ""
        if getattr(flag, "due_date_time", None) and getattr(flag.due_date_time, "date_time", None):
            due = Message._safe_str(flag.due_date_time.date_time)
        return {"flag_status": status, "due_date_time": due}

    @classmethod
    def from_sdk(cls, msg: GraphMessage) -> "Message":
        """Convert a Microsoft Graph SDK Message object to a Message dataclass."""
        text = cls._parse_body(msg.body.content if msg.body and msg.body.content else "")
        return cls(
            bcc_recipients=[
                Recipient.from_sdk(recipient) for recipient in msg.bcc_recipients or []
            ],
            cc_recipients=[Recipient.from_sdk(recipient) for recipient in msg.cc_recipients or []],
            reply_to=[Recipient.from_sdk(recipient) for recipient in msg.reply_to or []],
            to_recipients=[Recipient.from_sdk(recipient) for recipient in msg.to_recipients or []],
            from_=Recipient.from_sdk(msg.from_) if msg.from_ else Recipient(),
            subject=cls._safe_str(msg.subject),
            body=text,
            conversation_id=cls._safe_str(msg.conversation_id),
            conversation_index=(
                msg.conversation_index.decode("utf-8", errors="ignore")
                if isinstance(msg.conversation_index, bytes | bytearray)
                else cls._safe_str(msg.conversation_index)
            ),
            flag=cls._parse_flag(msg.flag),
            has_attachments=cls._safe_bool(msg.has_attachments),
            importance=cls._parse_importance(msg.importance),
            is_read=cls._safe_bool(msg.is_read),
            received_date_time=(
                msg.received_date_time.isoformat() if msg.received_date_time else ""
            ),
            web_link=cls._safe_str(msg.web_link),
            is_draft=cls._safe_bool(msg.is_draft),
            message_id=cls._safe_str(msg.id),
        )

    def to_sdk(self) -> GraphMessage:
        """Converts the Message dataclass to a Microsoft Graph SDK Message object."""
        sdk_msg = GraphMessage()
        sdk_msg.subject = self.subject
        body_obj = ItemBody()
        body_obj.content = self.body
        body_obj.content_type = BodyType.Text
        sdk_msg.body = body_obj
        sdk_msg.is_draft = self.is_draft
        sdk_msg.to_recipients = [r.to_sdk() for r in self.to_recipients]
        sdk_msg.cc_recipients = [r.to_sdk() for r in self.cc_recipients]
        sdk_msg.bcc_recipients = [r.to_sdk() for r in self.bcc_recipients]
        sdk_msg.reply_to = [r.to_sdk() for r in self.reply_to]

        return sdk_msg

    def to_dict(self) -> dict[str, Any]:
        """Converts the Message dataclass to a dictionary."""
        return {
            "bcc_recipients": [recipient.to_dict() for recipient in self.bcc_recipients],
            "cc_recipients": [recipient.to_dict() for recipient in self.cc_recipients],
            "reply_to": [recipient.to_dict() for recipient in self.reply_to],
            "to_recipients": [recipient.to_dict() for recipient in self.to_recipients],
            "from": self.from_.to_dict(),
            "subject": self.subject,
            "body": self.body,
            "conversation_id": self.conversation_id,
            "conversation_index": self.conversation_index,
            "flag": self.flag,
            "has_attachments": self.has_attachments,
            "importance": self.importance,
            "is_read": self.is_read,
            "received_date_time": self.received_date_time,
            "web_link": self.web_link,
            "is_draft": self.is_draft,
            "message_id": self.message_id,
        }

    def update_recipient_lists(
        self,
        to_add: list[str] | None = None,
        to_remove: list[str] | None = None,
        cc_add: list[str] | None = None,
        cc_remove: list[str] | None = None,
        bcc_add: list[str] | None = None,
        bcc_remove: list[str] | None = None,
    ) -> None:
        """Update each recipient list of the message.

        This function updates the recipient lists of the message by first adding new recipients
        and then removing existing recipients. Therefore, if an email address is both
        added and removed, then it will not be included in the returned list.
        """
        for attr, add_emails_input, remove_emails_input in (
            ("to_recipients", to_add, to_remove),
            ("cc_recipients", cc_add, cc_remove),
            ("bcc_recipients", bcc_add, bcc_remove),
        ):
            current_recipients = getattr(self, attr) or []
            # Add recipients
            existing_emails = {r.email_address.lower() for r in current_recipients}
            new_additions = [
                Recipient(email_address=email)
                for email in (add_emails_input or [])
                if email.lower() not in existing_emails
            ]
            # Remove recipients
            updated_list = current_recipients + new_additions
            remove_emails = {email.lower() for email in (remove_emails_input or [])}
            updated_list = [
                recipient
                for recipient in updated_list
                if recipient.email_address.lower() not in remove_emails
            ]
            # Update the message's attribute with the new list
            setattr(self, attr, updated_list)

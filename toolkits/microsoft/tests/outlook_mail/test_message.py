import pytest
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.message import Message as GraphMessage
from msgraph.generated.models.recipient import Recipient as GraphRecipient

from arcade_microsoft.outlook_mail.message import Message, Recipient


# Dummy classes to simulate SDK objects
class DummyBody:
    def __init__(self, content):
        self.content = content


class DummyFlagStatus:
    def __init__(self, value):
        self.value = value


class DummyImportance:
    def __init__(self, value):
        self.value = value


class DummyDueDateTime:
    def __init__(self, date_time):
        self.date_time = date_time


class DummyFlag:
    def __init__(self, flag_status, due_date_time):
        self.flag_status = DummyFlagStatus(flag_status)
        self.due_date_time = DummyDueDateTime(due_date_time)


class DummyDateTime:
    def __init__(self, date_str):
        self.date_str = date_str

    def isoformat(self):
        return self.date_str


def make_graph_recipient(rec_data):
    recipient = GraphRecipient()
    recipient.email_address = GraphEmailAddress()
    recipient.email_address.address = rec_data["email_address"]
    recipient.email_address.name = rec_data.get("name", "")
    return recipient


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (
            {
                "body_content": "<p>Hello <b>world</b></p>",
                "subject": "Test subject",
                "conversation_id": "conv-1",
                "conversation_index": "conv-index",
                "flag_status": "flagged",
                "due_date_time": "2021-01-01T10:00:00",
                "has_attachments": False,
                "importance": "high",
                "is_read": True,
                "received_date_time": "2021-01-02T00:00:00",
                "web_link": "http://example.com",
                "is_draft": False,
                "message_id": "1234",
                "to_recipients": [{"email_address": "to@example.com", "name": "ToName"}],
                "cc_recipients": [{"email_address": "cc@example.com", "name": "CcName"}],
                "bcc_recipients": [{"email_address": "bcc@example.com", "name": "BccName"}],
                "reply_to": [{"email_address": "reply@example.com", "name": "ReplyName"}],
                "from_": {"email_address": "from@example.com", "name": "FromName"},
                "conversation_index_bytes": False,
            },
            {
                "body": "Hello world",
                "subject": "Test subject",
                "conversation_id": "conv-1",
                "conversation_index": "conv-index",
                "flag": {"flag_status": "flagged", "due_date_time": "2021-01-01T10:00:00"},
                "has_attachments": False,
                "importance": "high",
                "is_read": True,
                "received_date_time": "2021-01-02T00:00:00",
                "web_link": "http://example.com",
                "is_draft": False,
                "message_id": "1234",
                "to_recipients": [{"email_address": "to@example.com", "name": "ToName"}],
                "cc_recipients": [{"email_address": "cc@example.com", "name": "CcName"}],
                "bcc_recipients": [{"email_address": "bcc@example.com", "name": "BccName"}],
                "reply_to": [{"email_address": "reply@example.com", "name": "ReplyName"}],
                "from_": {"email_address": "from@example.com", "name": "FromName"},
            },
        ),
        (
            {
                "body_content": "<p>Sample <i>email</i> message</p>",
                "subject": "Another subject",
                "conversation_id": "conv-2",
                "conversation_index": b"byte-index",
                "flag_status": "notFlaged",
                "due_date_time": "",
                "has_attachments": False,
                "importance": "low",
                "is_read": False,
                "received_date_time": "",
                "web_link": "",
                "is_draft": True,
                "message_id": "5678",
                "to_recipients": [{"email_address": "user1@example.com", "name": "User1"}],
                "cc_recipients": [],
                "bcc_recipients": [],
                "reply_to": [],
                "from_": {"email_address": "sender@example.com", "name": "Sender"},
                "conversation_index_bytes": True,
            },
            {
                "body": "Sample email message",
                "subject": "Another subject",
                "conversation_id": "conv-2",
                "conversation_index": "byte-index",
                "flag": {"flag_status": "notFlaged", "due_date_time": ""},
                "has_attachments": False,
                "importance": "low",
                "is_read": False,
                "received_date_time": "",
                "web_link": "",
                "is_draft": True,
                "message_id": "5678",
                "to_recipients": [{"email_address": "user1@example.com", "name": "User1"}],
                "cc_recipients": [],
                "bcc_recipients": [],
                "reply_to": [],
                "from_": {"email_address": "sender@example.com", "name": "Sender"},
            },
        ),
    ],
)
def test_message_conversion(input_data, expected):
    # Set up sdk message
    sdk_message = GraphMessage()
    sdk_message.body = (
        DummyBody(input_data["body_content"]) if "body_content" in input_data else None
    )
    sdk_message.subject = input_data["subject"]
    sdk_message.conversation_id = input_data["conversation_id"]
    sdk_message.conversation_index = input_data["conversation_index"]
    sdk_message.flag = (
        DummyFlag(input_data["flag_status"], input_data["due_date_time"])
        if "flag_status" in input_data
        else None
    )
    sdk_message.has_attachments = input_data["has_attachments"]
    sdk_message.importance = DummyImportance(input_data["importance"])
    sdk_message.is_read = input_data["is_read"]
    sdk_message.received_date_time = (
        DummyDateTime(input_data["received_date_time"])
        if input_data["received_date_time"]
        else None
    )
    sdk_message.web_link = input_data["web_link"]
    sdk_message.is_draft = input_data["is_draft"]
    sdk_message.id = input_data["message_id"]
    sdk_message.to_recipients = [make_graph_recipient(r) for r in input_data["to_recipients"]]
    sdk_message.cc_recipients = [make_graph_recipient(r) for r in input_data["cc_recipients"]]
    sdk_message.bcc_recipients = [make_graph_recipient(r) for r in input_data["bcc_recipients"]]
    sdk_message.reply_to = [make_graph_recipient(r) for r in input_data["reply_to"]]
    sdk_message.from_ = make_graph_recipient(input_data["from_"])

    # Convert to Arcade Message type
    message = Message.from_sdk(sdk_message)

    # Ensure conversion is correct
    assert message.body == expected["body"], "Body conversion mismatch"
    assert message.subject == expected["subject"]
    assert message.conversation_id == expected["conversation_id"]
    assert message.conversation_index == expected["conversation_index"]
    assert message.flag == expected["flag"]
    assert message.has_attachments == expected["has_attachments"]
    assert message.importance == expected["importance"]
    assert message.is_read == expected["is_read"]
    assert message.received_date_time == expected["received_date_time"]
    assert message.web_link == expected["web_link"]
    assert message.is_draft == expected["is_draft"]
    assert message.message_id == expected["message_id"]
    assert message.from_.email_address == expected["from_"]["email_address"]
    assert message.from_.name == expected["from_"]["name"]

    def check_recipient_list(actual, exp_list):
        assert len(actual) == len(exp_list)
        for rec, exp in zip(actual, exp_list, strict=False):
            assert rec.email_address == exp["email_address"]
            assert rec.name == exp["name"]

    check_recipient_list(message.to_recipients, expected["to_recipients"])
    check_recipient_list(message.cc_recipients, expected["cc_recipients"])
    check_recipient_list(message.bcc_recipients, expected["bcc_recipients"])
    check_recipient_list(message.reply_to, expected["reply_to"])


@pytest.mark.parametrize(
    "initial, add_params, expected_to_recipients",
    [
        # Add a "To" recipient
        (
            {"to_recipients": []},
            {"to_add": ["new@example.com"]},
            [{"email_address": "new@example.com", "name": ""}],
        ),
        # Add a "To" recipient that already exists
        (
            {"to_recipients": [{"email_address": "dup@example.com", "name": ""}]},
            {"to_add": ["dup@example.com"]},
            [
                {"email_address": "dup@example.com", "name": ""},
            ],
        ),
        # Remove a "To" recipient
        (
            {
                "to_recipients": [
                    {"email_address": "a@example.com", "name": "A"},
                    {"email_address": "b@example.com", "name": "B"},
                ]
            },
            {"to_remove": ["a@example.com"]},
            [{"email_address": "b@example.com", "name": "B"}],
        ),
        # Add and remove a "To" recipient
        (
            {"to_recipients": [{"email_address": "c@example.com", "name": "C"}]},
            {"to_add": ["d@example.com", "c@example.com"], "to_remove": ["c@example.com"]},
            [{"email_address": "d@example.com", "name": ""}],
        ),
    ],
)
def test_update_recipient_lists(initial, add_params, expected_to_recipients):
    msg = Message()
    msg.to_recipients = [
        Recipient(email_address=r["email_address"], name=r.get("name", ""))
        for r in initial.get("to_recipients", [])
    ]
    msg.update_recipient_lists(
        to_add=add_params.get("to_add"), to_remove=add_params.get("to_remove")
    )
    result = [r.to_dict() for r in msg.to_recipients]
    assert result == expected_to_recipients, f"Expected {expected_to_recipients}, got {result}"

from base64 import urlsafe_b64encode
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext
from arcade_tdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google.models import GmailReplyToWhom
from arcade_google.tools import (
    delete_draft_email,
    get_thread,
    list_draft_emails,
    list_emails,
    list_emails_by_header,
    list_threads,
    reply_to_email,
    search_threads,
    send_draft_email,
    send_email,
    trash_email,
    update_draft_email,
    write_draft_email,
)
from arcade_google.utils import (
    build_reply_body,
    parse_draft_email,
    parse_multipart_email,
    parse_plain_text_email,
)


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_send_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    result = await send_email(
        context=mock_context,
        subject="Test Subject",
        body="Test Body",
        recipient="test@example.com",
    )

    assert isinstance(result, dict)
    assert "id" in result
    assert "thread_id" in result
    assert "subject" in result
    assert "body" in result

    # Test http error
    mock_service.users().messages().send().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid recipient"}}',
    )

    with pytest.raises(ToolExecutionError):
        await send_email(
            context=mock_context,
            subject="Test Subject",
            body="Test Body",
            recipient="invalid@example.com",
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_write_draft_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    result = await write_draft_email(
        context=mock_context,
        subject="Test Draft Subject",
        body="Test Draft Body",
        recipient="draft@example.com",
    )

    assert isinstance(result, dict)
    assert "id" in result
    assert "thread_id" in result
    assert "subject" in result
    assert "body" in result

    # Test http error
    mock_service.users().drafts().create().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await write_draft_email(
            context=mock_context,
            subject="Test Draft Subject",
            body="Test Draft Body",
            recipient="draft@example.com",
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_update_draft_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    result = await update_draft_email(
        context=mock_context,
        draft_email_id="draft123",
        subject="Updated Subject",
        body="Updated Body",
        recipient="updated@example.com",
    )

    assert isinstance(result, dict)
    assert "id" in result
    assert "thread_id" in result
    assert "subject" in result
    assert "body" in result

    # Test http error
    mock_service.users().drafts().update().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Draft not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await update_draft_email(
            context=mock_context,
            draft_email_id="nonexistent_draft",
            subject="Updated Subject",
            body="Updated Body",
            recipient="updated@example.com",
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_send_draft_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    result = await send_draft_email(context=mock_context, email_id="draft456")

    assert isinstance(result, dict)
    assert "id" in result
    assert "thread_id" in result
    assert "subject" in result
    assert "body" in result

    # Test http error
    mock_service.users().drafts().send().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Draft not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await send_draft_email(context=mock_context, email_id="nonexistent_draft")


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_delete_draft_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    result = await delete_draft_email(context=mock_context, draft_email_id="draft789")

    assert "Draft email with ID" in result
    assert "deleted successfully" in result

    # Test http error
    mock_service.users().drafts().delete().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Draft not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await delete_draft_email(context=mock_context, draft_email_id="nonexistent_draft")


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
@patch("arcade_google.tools.gmail.parse_draft_email")
async def test_get_draft_emails(mock_parse_draft_email, mock_build, mock_context):
    # Setup test data
    mock_drafts_list_response = {
        "drafts": [
            {
                "id": "r9999999999999999999",
                "message": {"id": "0000000000000000", "threadId": "0000000000000000"},
            }
        ],
        "resultSizeEstimate": 1,
    }
    mock_drafts_get_response = {
        "id": "r9999999999999999999",
        "message": {
            "id": "0000000000000000",
            "threadId": "0000000000000000",
            "labelIds": ["DRAFT"],
            "snippet": "Hello! This is a test. Best regards, John",
            "payload": {
                "partId": "",
                "mimeType": "text/plain",
                "filename": "",
                "headers": [
                    {"name": "to", "value": "test@arcade-ai.com"},
                    {"name": "subject", "value": "New Draft"},
                    {"name": "Date", "value": "Mon, 16 Sep 2024 13:02:10 -0400"},
                    {"name": "From", "value": "john-doe@arcade-ai.com"},
                ],
                "body": {
                    "size": 41,
                    "data": "SGVsbG8hIFRoaXMgaXMgYSB0ZXN0LgoKQmVzdCByZWdhcmRzLApCb2I=",
                },
            },
            "sizeEstimate": 453,
            "historyId": "7061",
            "internalDate": "1726506130000",
        },
    }

    # Setup mocking
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the response from the Gmail list drafts API
    mock_service.users().drafts().list().execute.return_value = mock_drafts_list_response

    # Mock the response from the Gmail get drafts API
    mock_service.users().drafts().get().execute.return_value = mock_drafts_get_response

    # Mock the parse_draft_email function since parse_draft_email doesn't accept object of type MagicMock
    mock_parse_draft_email.return_value = parse_draft_email(mock_drafts_get_response)

    # Test happy path
    result = await list_draft_emails(context=mock_context, n_drafts=2)

    assert isinstance(result, dict)
    assert "emails" in result
    assert len(result["emails"]) == 1
    assert all("id" in draft and "subject" in draft for draft in result["emails"])

    # Test http error
    mock_service.users().drafts().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_draft_emails(context=mock_context, n_drafts=2)


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
@patch("arcade_google.tools.gmail.parse_plain_text_email")
async def test_search_emails_by_header(mock_parse_plain_text_email, mock_build, mock_context):
    # Setup test data
    mock_messages_list_response = {
        "messages": [
            {"id": "191fbc8ddce0f433", "threadId": "191fbc8ddce0f433"},
            {"id": "191fbc0ea11efa90", "threadId": "191fbc0ea11efa90"},
        ],
        "nextPageToken": "00755945214480102915",
        "resultSizeEstimate": 201,
    }
    mock_messages_get_response = {
        "id": "191f2cf4d24bf23d",
        "threadId": "191f2cf4d24bf23d",
        "labelIds": ["UNREAD", "IMPORTANT", "CATEGORY_UPDATES", "INBOX"],
        "snippet": "Hey User, Your personal access token (classic) &quot;ArcadeAI&quot; with admin:enterprise, admin:gpg_key, admin:org, admin:org_hook, admin:public_key, admin:repo_hook, admin:ssh_signing_key,",
        "payload": {
            "partId": "",
            "mimeType": "text/plain",
            "filename": "",
            "headers": [
                {"name": "Delivered-To", "value": "example@arcade-ai.com"},
                {"name": "Date", "value": "Sat, 14 Sep 2024 16:12:37 -0700"},
                {"name": "From", "value": "GitHub \u003cnoreply@github.com\u003e"},
                {"name": "To", "value": "example@arcade-ai.com"},
                {
                    "name": "Subject",
                    "value": "[GitHub] Your personal access token (classic) has expired",
                },
            ],
            "body": {
                "size": 605,
                "data": "SGV5IEBFcmljR3VzdGluLA0KDQpZb3VyIHBlcnNvbmFsIGFjY2VzcyB0b2tlbiAoY2xhc3NpYykgIkFyY2FkZUFJIiB3aXRoIGFkbWluOmVudGVycHJpc2UsIGFkbWluOmdwZ19rZXksIGFkbWluOm9yZywgYWRtaW46b3JnX2hvb2ssIGFkbWluOnB1YmxpY19rZXksIGFkbWluOnJlcG9faG9vaywgYWRtaW46c3NoX3NpZ25pbmdfa2V5LCBhdWRpdF9sb2csIGNvZGVzcGFjZSwgY29waWxvdCwgZGVsZXRlOnBhY2thZ2VzLCBkZWxldGVfcmVwbywgZ2lzdCwgbm90aWZpY2F0aW9ucywgcHJvamVjdCwgcmVwbywgdXNlciwgd29ya2Zsb3csIHdyaXRlOmRpc2N1c3Npb24sIGFuZCB3cml0ZTpwYWNrYWdlcyBzY29wZXMgaGFzIGV4cGlyZWQuDQoNCklmIHRoaXMgdG9rZW4gaXMgc3RpbGwgbmVlZGVkLCB2aXNpdCBodHRwczovL2dpdGh1Yi5jb20vc2V0dGluZ3MvdG9rZW5zLzE3MTM2OTg2MTMvcmVnZW5lcmF0ZSB0byBnZW5lcmF0ZSBhbiBlcXVpdmFsZW50Lg0KDQpJZiB5b3UgcnVuIGludG8gcHJvYmxlbXMsIHBsZWFzZSBjb250YWN0IHN1cHBvcnQgYnkgdmlzaXRpbmcgaHR0cHM6Ly9naXRodWIuY29tL2NvbnRhY3QNCg0KVGhhbmtzLA0KVGhlIEdpdEh1YiBUZWFtDQo=",
            },
        },
        "sizeEstimate": 4512,
        "historyId": "5508",
        "internalDate": "1726355557000",
    }

    # Setup mocking
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the response from the Gmail list messages API
    mock_service.users().messages().list().execute.return_value = mock_messages_list_response

    # Mock the response from the Gmail get messages API
    mock_service.users().messages().get().execute.return_value = mock_messages_get_response

    # Mock the parse_plain_text_email function since parse_plain_text_email doesn't accept object of type MagicMock
    mock_parse_plain_text_email.return_value = parse_plain_text_email(mock_messages_get_response)

    # Test happy path
    result = await list_emails_by_header(
        context=mock_context, sender="noreply@github.com", max_results=2
    )

    assert isinstance(result, dict)
    assert "emails" in result
    assert len(result["emails"]) == 2
    assert all("id" in email and "subject" in email for email in result["emails"])

    # Test http error
    mock_service.users().messages().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_emails_by_header(
            context=mock_context, sender="noreply@github.com", max_results=2
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
@patch("arcade_google.tools.gmail.parse_plain_text_email")
async def test_get_emails(mock_parse_plain_text_email, mock_build, mock_context):
    # Setup test data
    mock_messages_list_response = {
        "messages": [
            {"id": "191fbc8ddce0f433", "threadId": "191fbc8ddce0f433"},
        ],
        "nextPageToken": "00755945214480102915",
        "resultSizeEstimate": 1,
    }
    mock_messages_get_response = {
        "id": "191f2cf4d24bf23d",
        "threadId": "191f2cf4d24bf23d",
        "labelIds": ["UNREAD", "IMPORTANT", "CATEGORY_UPDATES", "INBOX"],
        "snippet": "Hey User, Your personal access token (classic) &quot;ArcadeAI&quot; with admin:enterprise, admin:gpg_key, admin:org, admin:org_hook, admin:public_key, admin:repo_hook, admin:ssh_signing_key,",
        "payload": {
            "partId": "",
            "mimeType": "text/plain",
            "filename": "",
            "headers": [
                {"name": "Delivered-To", "value": "example@arcade-ai.com"},
                {"name": "Date", "value": "Sat, 14 Sep 2024 16:12:37 -0700"},
                {"name": "From", "value": "GitHub \u003cnoreply@github.com\u003e"},
                {"name": "To", "value": "example@arcade-ai.com"},
                {
                    "name": "Subject",
                    "value": "[GitHub] Your personal access token (classic) has expired",
                },
            ],
            "body": {
                "size": 605,
                "data": "SGV5IEBFcmljR3VzdGluLA0KDQpZb3VyIHBlcnNvbmFsIGFjY2VzcyB0b2tlbiAoY2xhc3NpYykgIkFyY2FkZUFJIiB3aXRoIGFkbWluOmVudGVycHJpc2UsIGFkbWluOmdwZ19rZXksIGFkbWluOm9yZywgYWRtaW46b3JnX2hvb2ssIGFkbWluOnB1YmxpY19rZXksIGFkbWluOnJlcG9faG9vaywgYWRtaW46c3NoX3NpZ25pbmdfa2V5LCBhdWRpdF9sb2csIGNvZGVzcGFjZSwgY29waWxvdCwgZGVsZXRlOnBhY2thZ2VzLCBkZWxldGVfcmVwbywgZ2lzdCwgbm90aWZpY2F0aW9ucywgcHJvamVjdCwgcmVwbywgdXNlciwgd29ya2Zsb3csIHdyaXRlOmRpc2N1c3Npb24sIGFuZCB3cml0ZTpwYWNrYWdlcyBzY29wZXMgaGFzIGV4cGlyZWQuDQoNCklmIHRoaXMgdG9rZW4gaXMgc3RpbGwgbmVlZGVkLCB2aXNpdCBodHRwczovL2dpdGh1Yi5jb20vc2V0dGluZ3MvdG9rZW5zLzE3MTM2OTg2MTMvcmVnZW5lcmF0ZSB0byBnZW5lcmF0ZSBhbiBlcXVpdmFsZW50Lg0KDQpJZiB5b3UgcnVuIGludG8gcHJvYmxlbXMsIHBsZWFzZSBjb250YWN0IHN1cHBvcnQgYnkgdmlzaXRpbmcgaHR0cHM6Ly9naXRodWIuY29tL2NvbnRhY3QNCg0KVGhhbmtzLA0KVGhlIEdpdEh1YiBUZWFtDQo=",
            },
        },
        "sizeEstimate": 4512,
        "historyId": "5508",
        "internalDate": "1726355557000",
    }

    # Setup mocking
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock the response from the Gmail list messages API
    mock_service.users().messages().list().execute.return_value = mock_messages_list_response

    # Mock the Gmail get messages API
    mock_service.users().messages().get().execute.return_value = mock_messages_get_response

    # Mock the parse_plain_text_email function since parse_plain_text_email doesn't accept object of type MagicMock
    mock_parse_plain_text_email.return_value = parse_plain_text_email(mock_messages_get_response)

    # Test happy path
    result = await list_emails(context=mock_context, n_emails=1)

    assert isinstance(result, dict)
    assert "emails" in result
    assert len(result["emails"]) == 1
    assert "id" in result["emails"][0]
    assert "subject" in result["emails"][0]
    assert "date" in result["emails"][0]
    assert "body" in result["emails"][0]

    # Test http error
    mock_service.users().messages().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_emails(context=mock_context, n_emails=1)


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_trash_email(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Test happy path
    email_id = "123456"
    result = await trash_email(context=mock_context, email_id=email_id)

    assert isinstance(result, dict)
    assert "id" in result
    assert "thread_id" in result
    assert "subject" in result
    assert "body" in result

    # Test http error
    mock_service.users().messages().trash().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Email not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await trash_email(context=mock_context, email_id="nonexistent_email")


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_search_threads(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Setup mock response data
    mock_threads_list_response = {
        "threads": [
            {
                "id": "thread1",
                "snippet": "Thread snippet 1",
            },
            {
                "id": "thread2",
                "snippet": "Thread snippet 2",
            },
        ],
        "nextPageToken": "next_token_123",
        "resultSizeEstimate": 2,
    }

    # Mock the Gmail API threads().list() method
    mock_service.users().threads().list().execute.return_value = mock_threads_list_response

    # Test happy path
    result = await search_threads(
        context=mock_context,
        sender="test@example.com",
        max_results=2,
    )

    assert isinstance(result, dict)
    assert "threads" in result
    assert len(result["threads"]) == 2
    assert result["threads"][0]["id"] == "thread1"
    assert "next_page_token" in result

    # Test error handling
    mock_service.users().threads().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await search_threads(
            context=mock_context,
            sender="test@example.com",
            max_results=2,
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_list_threads(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Setup mock response data
    mock_threads_list_response = {
        "threads": [
            {
                "id": "thread1",
                "snippet": "Thread snippet 1",
            },
            {
                "id": "thread2",
                "snippet": "Thread snippet 2",
            },
        ],
        "nextPageToken": "next_token_123",
        "resultSizeEstimate": 2,
    }

    # Mock the Gmail API threads().list() method
    mock_service.users().threads().list().execute.return_value = mock_threads_list_response

    # Test happy path
    result = await list_threads(
        context=mock_context,
        max_results=2,
    )

    assert isinstance(result, dict)
    assert "threads" in result
    assert len(result["threads"]) == 2
    assert result["threads"][0]["id"] == "thread1"
    assert "next_page_token" in result

    # Test error handling
    mock_service.users().threads().list().execute.side_effect = HttpError(
        resp=MagicMock(status=400),
        content=b'{"error": {"message": "Invalid request"}}',
    )

    with pytest.raises(ToolExecutionError):
        await list_threads(
            context=mock_context,
            max_results=2,
        )


@pytest.mark.asyncio
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_get_thread(mock_build, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Setup mock response data
    mock_thread_get_response = {
        "id": "thread1",
        "messages": [
            {
                "id": "message1",
                "snippet": "Message snippet 1",
            },
            {
                "id": "message2",
                "snippet": "Message snippet 2",
            },
        ],
    }

    # Mock the Gmail API threads().get() method
    mock_service.users().threads().get().execute.return_value = mock_thread_get_response

    # Test happy path
    result = await get_thread(
        context=mock_context,
        thread_id="thread1",
    )

    assert isinstance(result, dict)
    assert "id" in result
    assert result["id"] == "thread1"
    assert "messages" in result
    assert len(result["messages"]) == 2
    assert result["messages"][0]["id"] == "message1"

    # Test error handling
    mock_service.users().threads().get().execute.side_effect = HttpError(
        resp=MagicMock(status=404),
        content=b'{"error": {"message": "Thread not found"}}',
    )

    with pytest.raises(ToolExecutionError):
        await get_thread(
            context=mock_context,
            thread_id="invalid_thread",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply_to_whom, expected_to, expected_cc",
    [
        (
            GmailReplyToWhom.EVERY_RECIPIENT,
            "sender@example.com, to1@example.com, to2@example.com",
            "cc1@example.com, cc2@example.com",
        ),
        (
            GmailReplyToWhom.ONLY_THE_SENDER,
            "sender@example.com",
            "",
        ),
    ],
)
@patch("arcade_google.tools.gmail._build_gmail_service")
async def test_reply_to_email(mock_build, reply_to_whom, expected_to, expected_cc, mock_context):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    original_message = {
        "id": "id123456",
        "threadId": "thread123456",
        "payload": {
            "headers": [
                {"name": "Message-ID", "value": "id123456"},
                {"name": "Subject", "value": "test"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "to1@example.com, to2@example.com, test@example.com"},
                {"name": "Cc", "value": "cc1@example.com, cc2@example.com"},
                {"name": "References", "value": "thread123456"},
            ],
        },
    }

    mock_service.users().getProfile().execute.return_value = {"emailAddress": "test@example.com"}
    mock_service.users().messages().get().execute.return_value = original_message

    result = await reply_to_email(
        context=mock_context,
        body="test",
        reply_to_message_id="id123456",
        reply_to_whom=reply_to_whom,
    )

    assert isinstance(result, dict)
    assert "url" in result

    replying_to = parse_multipart_email(original_message)
    expected_body = build_reply_body("test", replying_to)

    expected_message = EmailMessage()
    expected_message.set_content(expected_body)
    expected_message["To"] = expected_to
    expected_message["Subject"] = "Re: test"
    if expected_cc:
        expected_message["Cc"] = expected_cc
    expected_message["In-Reply-To"] = "id123456"
    expected_message["References"] = "id123456, thread123456"

    mock_service.users().messages().send.assert_called_once_with(
        userId="me",
        body={
            "raw": urlsafe_b64encode(expected_message.as_bytes()).decode(),
            "threadId": "thread123456",
        },
    )


def test_parse_multipart_email_full():
    """
    Test parsing a multipart email with both plain text and HTML bodies.
    """
    email_data = {
        "id": "email123",
        "threadId": "thread123",
        "labelIds": ["INBOX", "UNREAD"],
        "historyId": "history123",
        "snippet": "This is a test email.",
        "payload": {
            "headers": [
                {"name": "To", "value": "recipient@example.com"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Test Email"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 10:00:00 -0000"},
            ],
            "body": {"size": 100, "data": "VGhpcyBpcyBhIHRlc3QgZW1haWwu"},
        },
    }

    with (
        patch("arcade_google.utils._get_email_plain_text_body") as mock_plain,
        patch("arcade_google.utils._get_email_html_body") as mock_html,
        patch("arcade_google.utils._clean_email_body") as mock_clean,
    ):
        # Mock the helper functions
        mock_plain.return_value = "This is a test email."
        mock_html.return_value = "<p>This is a test email.</p>"
        mock_clean.return_value = "This is a test email."

        result = parse_multipart_email(email_data)

        assert result["id"] == "email123"
        assert result["thread_id"] == "thread123"
        assert result["label_ids"] == ["INBOX", "UNREAD"]
        assert result["snippet"] == "This is a test email."
        assert result["to"] == "recipient@example.com"
        assert result["from"] == "sender@example.com"
        assert result["subject"] == "Test Email"
        assert result["date"] == "Mon, 1 Jan 2024 10:00:00 -0000"
        assert result["plain_text_body"] == "This is a test email."
        assert result["html_body"] == "<p>This is a test email.</p>"


def test_parse_multipart_email_plain_only():
    """
    Test parsing an email with only a plain text body.
    """
    email_data = {
        "id": "email456",
        "threadId": "thread456",
        "labelIds": ["INBOX"],
        "historyId": "history456",
        "snippet": "Plain text only email.",
        "payload": {
            "headers": [
                {"name": "To", "value": "recipient2@example.com"},
                {"name": "From", "value": "sender2@example.com"},
                {"name": "Subject", "value": "Plain Text Email"},
                {"name": "Date", "value": "Tue, 2 Feb 2024 11:00:00 -0000"},
            ],
            "body": {"size": 150, "data": "UGxhaW4gdGV4dCBvbmx5IGVtYWlsLg=="},
        },
    }

    with (
        patch("arcade_google.utils._get_email_plain_text_body") as mock_plain,
        patch("arcade_google.utils._get_email_html_body") as mock_html,
        patch("arcade_google.utils._clean_email_body") as mock_clean,
    ):
        # Mock the helper functions
        mock_plain.return_value = "Plain text only email."
        mock_html.return_value = None
        mock_clean.return_value = "Plain text only email."

        result = parse_multipart_email(email_data)

        assert result["id"] == "email456"
        assert result["thread_id"] == "thread456"
        assert result["label_ids"] == ["INBOX"]
        assert result["snippet"] == "Plain text only email."
        assert result["to"] == "recipient2@example.com"
        assert result["from"] == "sender2@example.com"
        assert result["subject"] == "Plain Text Email"
        assert result["date"] == "Tue, 2 Feb 2024 11:00:00 -0000"
        assert result["plain_text_body"] == "Plain text only email."
        assert result["html_body"] == ""


def test_parse_multipart_email_html_only():
    """
    Test parsing an email with only an HTML body.
    """
    email_data = {
        "id": "email789",
        "threadId": "thread789",
        "labelIds": ["SENT"],
        "historyId": "history789",
        "snippet": "HTML only email.",
        "payload": {
            "headers": [
                {"name": "To", "value": "recipient3@example.com"},
                {"name": "From", "value": "sender3@example.com"},
                {"name": "Subject", "value": "HTML Email"},
                {"name": "Date", "value": "Wed, 3 Mar 2024 12:00:00 -0000"},
            ],
            "body": {"size": 200, "data": "PGh0bWw+VGhpcyBpcyBIVE1MIGVtYWlsLjwvaHRtbD4="},
        },
    }

    with (
        patch("arcade_google.utils._get_email_plain_text_body") as mock_plain,
        patch("arcade_google.utils._get_email_html_body") as mock_html,
        patch("arcade_google.utils._clean_email_body") as mock_clean,
    ):
        # Mock the helper functions
        mock_plain.return_value = None
        mock_html.return_value = "<html>This is HTML email.</html>"
        mock_clean.return_value = "This is HTML email."

        result = parse_multipart_email(email_data)

        assert result["id"] == "email789"
        assert result["thread_id"] == "thread789"
        assert result["label_ids"] == ["SENT"]
        assert result["snippet"] == "HTML only email."
        assert result["to"] == "recipient3@example.com"
        assert result["from"] == "sender3@example.com"
        assert result["subject"] == "HTML Email"
        assert result["date"] == "Wed, 3 Mar 2024 12:00:00 -0000"
        assert result["plain_text_body"] == "This is HTML email."
        assert result["html_body"] == "<html>This is HTML email.</html>"


def test_parse_multipart_email_missing_payload():
    """
    Test parsing an email with missing payload.
    """
    email_data = {
        "id": "email000",
        "threadId": "thread000",
        "labelIds": ["INBOX"],
        "historyId": "history000",
        "snippet": "Missing payload email.",
        # 'payload' key is missing
    }

    result = parse_multipart_email(email_data)

    # Since payload is missing, headers and bodies should be default or empty
    assert result["id"] == "email000"
    assert result["thread_id"] == "thread000"
    assert result["label_ids"] == ["INBOX"]
    assert result["snippet"] == "Missing payload email."
    assert result["to"] == ""
    assert result["from"] == ""
    assert result["subject"] == ""
    assert result["date"] == ""
    assert result["plain_text_body"] == ""
    assert result["html_body"] == ""


def test_parse_multipart_email_missing_headers():
    """
    Test parsing an email with missing headers in the payload.
    """
    email_data = {
        "id": "email111",
        "threadId": "thread111",
        "labelIds": ["INBOX"],
        "historyId": "history111",
        "snippet": "Missing headers email.",
        "payload": {
            # 'headers' key is missing
            "body": {"size": 100, "data": "VGltZWw="}
        },
    }

    with (
        patch("arcade_google.utils._get_email_plain_text_body") as mock_plain,
        patch("arcade_google.utils._get_email_html_body") as mock_html,
        patch("arcade_google.utils._clean_email_body") as mock_clean,
    ):
        # Mock the helper functions
        mock_plain.return_value = "Timeel"
        mock_html.return_value = "<p>Timeel</p>"
        mock_clean.return_value = "Timeel"

        result = parse_multipart_email(email_data)

    assert result["id"] == "email111"
    assert result["thread_id"] == "thread111"
    assert result["label_ids"] == ["INBOX"]
    assert result["snippet"] == "Missing headers email."
    assert result["to"] == ""
    assert result["from"] == ""
    assert result["subject"] == ""
    assert result["date"] == ""
    assert result["plain_text_body"] == "Timeel"
    assert result["html_body"] == "<p>Timeel</p>"


def test_parse_multipart_email_missing_fields():
    """
    Test parsing an email with some missing fields in headers.
    """
    email_data = {
        "id": "email222",
        "threadId": "thread222",
        "labelIds": ["INBOX"],
        "historyId": "history222",
        "snippet": "Missing some headers.",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender4@example.com"},
                {"name": "Subject", "value": "Partial Headers"},
                # 'To' and 'Date' headers are missing
            ],
            "body": {"size": 100, "data": "TWlzc2luZyBzb21lIGhlYWRlcnMu"},
        },
    }

    with (
        patch("arcade_google.utils._get_email_plain_text_body") as mock_plain,
        patch("arcade_google.utils._get_email_html_body") as mock_html,
        patch("arcade_google.utils._clean_email_body") as mock_clean,
    ):
        # Mock the helper functions
        mock_plain.return_value = "Missing some headers."
        mock_html.return_value = None
        mock_clean.return_value = "Missing some headers."

        result = parse_multipart_email(email_data)

    assert result["id"] == "email222"
    assert result["thread_id"] == "thread222"
    assert result["label_ids"] == ["INBOX"]
    assert result["snippet"] == "Missing some headers."
    assert result["to"] == ""
    assert result["from"] == "sender4@example.com"
    assert result["subject"] == "Partial Headers"
    assert result["date"] == ""
    assert result["plain_text_body"] == "Missing some headers."
    assert result["html_body"] == ""


def test_parse_multipart_email_empty():
    """
    Test parsing an empty email data.
    """
    email_data = {}

    result = parse_multipart_email(email_data)

    assert result["id"] == ""
    assert result["thread_id"] == ""
    assert result["label_ids"] == []
    assert result["snippet"] == ""
    assert result["to"] == ""
    assert result["from"] == ""
    assert result["subject"] == ""
    assert result["date"] == ""
    assert result["plain_text_body"] == ""
    assert result["html_body"] == ""


def test_parse_multipart_email_invalid_payload_structure():
    """
    Test parsing an email with an invalid payload structure.
    """
    email_data = {
        "id": "email333",
        "threadId": "thread333",
        "labelIds": ["INBOX"],
        "historyId": "history333",
        "snippet": "Invalid payload structure.",
        "payload": {
            "headers": "This should be a list, not a string",
            "body": {"size": 100, "data": "SW52YWxpZCBwYXlsb2Fk"},
        },
    }

    with pytest.raises(TypeError):
        parse_multipart_email(email_data)

import base64
import json
from email.message import EmailMessage
from email.mime.text import MIMEText
from typing import Annotated, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from arcade.sdk.errors import RetryableToolError
from arcade_google.tools.utils import (
    DateRange,
    build_query_string,
    fetch_messages,
    get_draft_url,
    get_email_in_trash_url,
    get_sent_email_url,
    parse_draft_email,
    parse_email,
)


# Email sending tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
)
async def send_email(
    context: ToolContext,
    subject: Annotated[str, "The subject of the email"],
    body: Annotated[str, "The body of the email"],
    recipient: Annotated[str, "The recipient of the email"],
    cc: Annotated[Optional[list[str]], "CC recipients of the email"] = None,
    bcc: Annotated[Optional[list[str]], "BCC recipients of the email"] = None,
) -> Annotated[str, "A confirmation message with the sent email ID and URL"]:
    """
    Send an email using the Gmail API.
    """

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    message = EmailMessage()
    message.set_content(body)
    message["To"] = recipient
    message["Subject"] = subject
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)

    # Encode the message in base64
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create the email
    email = {"raw": encoded_message}

    # Send the email
    sent_message = service.users().messages().send(userId="me", body=email).execute()
    return f"Email with ID {sent_message['id']} sent: {get_sent_email_url(sent_message['id'])}"


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
)
async def send_draft_email(
    context: ToolContext, email_id: Annotated[str, "The ID of the draft to send"]
) -> Annotated[str, "A confirmation message with the sent email ID and URL"]:
    """
    Send a draft email using the Gmail API.
    """

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    # Send the draft email
    sent_message = service.users().drafts().send(userId="me", body={"id": email_id}).execute()

    # Construct the URL to the sent email
    return (
        f"Draft email with ID {sent_message['id']} sent: {get_sent_email_url(sent_message['id'])}"
    )


# Draft Management Tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.compose"],
    )
)
async def write_draft_email(
    context: ToolContext,
    subject: Annotated[str, "The subject of the draft email"],
    body: Annotated[str, "The body of the draft email"],
    recipient: Annotated[str, "The recipient of the draft email"],
    cc: Annotated[Optional[list[str]], "CC recipients of the draft email"] = None,
    bcc: Annotated[Optional[list[str]], "BCC recipients of the draft email"] = None,
) -> Annotated[str, "A confirmation message with the draft email ID and URL"]:
    """
    Compose a new email draft using the Gmail API.
    """
    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    message = MIMEText(body)
    message["to"] = recipient
    message["subject"] = subject
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create the draft
    draft = {"message": {"raw": raw_message}}

    draft_message = service.users().drafts().create(userId="me", body=draft).execute()
    return (
        f"Draft email with ID {draft_message['id']} created: {get_draft_url(draft_message['id'])}"
    )


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.compose"],
    )
)
async def update_draft_email(
    context: ToolContext,
    draft_email_id: Annotated[str, "The ID of the draft email to update."],
    subject: Annotated[str, "The subject of the draft email"],
    body: Annotated[str, "The body of the draft email"],
    recipient: Annotated[str, "The recipient of the draft email"],
    cc: Annotated[Optional[list[str]], "CC recipients of the draft email"] = None,
    bcc: Annotated[Optional[list[str]], "BCC recipients of the draft email"] = None,
) -> Annotated[str, "A confirmation message with the updated draft email ID and URL"]:
    """
    Update an existing email draft using the Gmail API.
    """

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    message = MIMEText(body)
    message["to"] = recipient
    message["subject"] = subject
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Update the draft
    draft = {"id": draft_email_id, "message": {"raw": raw_message}}

    updated_draft_message = (
        service.users().drafts().update(userId="me", id=draft_email_id, body=draft).execute()
    )
    return f"Draft email with ID {updated_draft_message['id']} updated: {get_draft_url(updated_draft_message['id'])}"


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.compose"],
    )
)
async def delete_draft_email(
    context: ToolContext,
    draft_email_id: Annotated[str, "The ID of the draft email to delete"],
) -> Annotated[str, "A confirmation message indicating successful deletion"]:
    """
    Delete a draft email using the Gmail API.
    """

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    # Delete the draft
    service.users().drafts().delete(userId="me", id=draft_email_id).execute()
    return f"Draft email with ID {draft_email_id} deleted successfully."


# Email Management Tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
)
async def trash_email(
    context: ToolContext, email_id: Annotated[str, "The ID of the email to trash"]
) -> Annotated[str, "A confirmation message with the trashed email ID and URL"]:
    """
    Move an email to the trash folder using the Gmail API.
    """

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    # Trash the email
    service.users().messages().trash(userId="me", id=email_id).execute()

    return f"Email with ID {email_id} trashed successfully: {get_email_in_trash_url(email_id)}"


# Draft Search Tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_draft_emails(
    context: ToolContext,
    n_drafts: Annotated[int, "Number of draft emails to read"] = 5,
) -> Annotated[str, "A JSON string containing a list of draft email details and their IDs"]:
    """
    Lists draft emails in the user's draft mailbox using the Gmail API.
    """
    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    listed_drafts = service.users().drafts().list(userId="me").execute()

    if not listed_drafts:
        return {"emails": []}

    draft_ids = [draft["id"] for draft in listed_drafts.get("drafts", [])][:n_drafts]

    emails = []
    for draft_id in draft_ids:
        try:
            draft_data = service.users().drafts().get(userId="me", id=draft_id).execute()
            draft_details = parse_draft_email(draft_data)
            if draft_details:
                emails.append(draft_details)
        except Exception as e:
            print(f"Error reading draft email {draft_id}: {e}")

    return json.dumps({"emails": emails})


# Email Search Tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_emails_by_header(
    context: ToolContext,
    sender: Annotated[Optional[str], "The name or email address of the sender of the email"] = None,
    recipient: Annotated[Optional[str], "The name or email address of the recipient"] = None,
    subject: Annotated[Optional[str], "Words to find in the subject of the email"] = None,
    body: Annotated[Optional[str], "Words to find in the body of the email"] = None,
    date_range: Annotated[Optional[DateRange], "The date range of the email"] = None,
    limit: Annotated[Optional[int], "The maximum number of emails to return"] = 25,
) -> Annotated[
    str, "A JSON string containing a list of email details matching the search criteria"
]:
    """
    Search for emails by header using the Gmail API.
    At least one of the following parametersMUST be provided: sender, recipient, subject, body.
    """
    if not any([sender, recipient, subject, body]):
        raise RetryableToolError(
            message="At least one of sender, recipient, subject, or body must be provided.",
            developer_message="At least one of sender, recipient, subject, or body must be provided.",
        )

    query = build_query_string(sender, recipient, subject, body, date_range)

    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))
    messages = fetch_messages(service, query, limit)

    if not messages:
        return json.dumps({"emails": []})

    emails = process_messages(service, messages)
    return json.dumps({"emails": emails})


def process_messages(service, messages):
    emails = []
    for msg in messages:
        try:
            email_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            email_details = parse_email(email_data)
            emails += [email_details] if email_details else []
        except HttpError as e:
            print(f"Error reading email {msg['id']}: {e}")
    return emails


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_emails(
    context: ToolContext,
    n_emails: Annotated[int, "Number of emails to read"] = 5,
) -> Annotated[str, "A JSON string containing a list of email details"]:
    """
    Read emails from a Gmail account and extract plain text content.
    """
    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    messages = service.users().messages().list(userId="me").execute().get("messages", [])

    if not messages:
        return {"emails": []}

    emails = []
    for msg in messages[:n_emails]:
        try:
            email_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            email_details = parse_email(email_data)
            if email_details:
                emails.append(email_details)
        except Exception as e:
            print(f"Error reading email {msg['id']}: {e}")

    return json.dumps({"emails": emails})

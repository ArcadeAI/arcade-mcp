import base64
import datetime
from enum import Enum
import json
from email.mime.text import MIMEText
from typing import Annotated, Optional
from arcade.core.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_gmail.tools.utils import parse_email
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google


@tool(
    requires_auth=Google(
        scope=["https://www.googleapis.com/auth/gmail.compose"],
    )
)
async def write_draft(
    context: ToolContext,
    subject: Annotated[str, "The subject of the email"],
    body: Annotated[str, "The body of the email"],
    recipient: Annotated[str, "The recipient of the email"],
) -> Annotated[str, "The URL of the draft"]:
    """Compose a new email draft."""

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    message = MIMEText(body)
    message["to"] = recipient
    message["subject"] = subject

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create the draft
    draft = {"message": {"raw": raw_message}}

    draft_message = service.users().drafts().create(userId="me", body=draft).execute()
    return f"Draft created: {get_draft_url(draft_message['id'])}"


def get_draft_url(draft_id):
    return f"https://mail.google.com/mail/u/0/#drafts/{draft_id}"


class DateRange(Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"

    def to_date_query(self):
        today = datetime.datetime.now()
        result = "after:"
        comparison_date = today

        if self == DateRange.YESTERDAY:
            comparison_date = today - datetime.timedelta(days=1)
        elif self == DateRange.LAST_7_DAYS:
            comparison_date = today - datetime.timedelta(days=7)
        elif self == DateRange.LAST_30_DAYS:
            comparison_date = today - datetime.timedelta(days=30)
        elif self == DateRange.THIS_MONTH:
            comparison_date = today.replace(day=1)
        elif self == DateRange.LAST_MONTH:
            comparison_date = (
                today.replace(day=1) - datetime.timedelta(days=1)
            ).replace(day=1)
        elif self == DateRange.THIS_YEAR:
            comparison_date = today.replace(month=1, day=1)
        elif self == DateRange.LAST_MONTH:
            comparison_date = (
                today.replace(month=1, day=1) - datetime.timedelta(days=1)
            ).replace(month=1, day=1)

        return result + comparison_date.strftime("%Y/%m/%d")


@tool(
    requires_auth=Google(
        scope=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def search_emails_by_header(
    context: ToolContext,
    sender: Annotated[
        Optional[str], "The name or email address of the sender of the email"
    ] = None,
    recipient: Annotated[
        Optional[str], "The name or email address of the recipient"
    ] = None,
    subject: Annotated[
        Optional[str], "Words to find in the subject of the email"
    ] = None,
    body: Annotated[Optional[str], "Words to find in the body of the email"] = None,
    date_range: Annotated[Optional[DateRange], "The date range of the email"] = None,
    limit: Annotated[Optional[int], "The maximum number of emails to return"] = 25,
) -> Annotated[str, "A list of email details in JSON format"]:
    """Search for emails by header.
    One of the following MUST be provided: sender, recipient, subject, body."""

    if not any([sender, recipient, subject, body]):
        raise ValueError(
            "At least one of sender, recipient, subject, or body must be provided."
        )

    # Set up the Gmail API client
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    # Build the query string
    query = []
    if sender:
        query.append(f"from:{sender}")
    if recipient:
        query.append(f"to:{recipient}")
    if subject:
        query.append(f"subject:{subject}")
    if body:
        query.append(body)
    if date_range:
        query.append(date_range.to_date_query())

    query_string = " ".join(query)

    try:
        # Perform the search
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query_string, maxResults=limit or 100)
            .execute()
        )
        messages = response.get("messages", [])

        if not messages:
            return json.dumps({"emails": []})

        emails = []
        for msg in messages:
            try:
                email_data = (
                    service.users().messages().get(userId="me", id=msg["id"]).execute()
                )
                email_details = parse_email(email_data)
                if email_details:
                    emails.append(email_details)
            except HttpError as e:
                print(f"Error reading email {msg['id']}: {e}")

        return json.dumps({"emails": emails})

    except HttpError as e:
        raise ToolExecutionError(
            "Error searching emails",
            developer_message=f"Gmail API Error: {e}",
        )


@tool(
    requires_auth=Google(
        scope=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def get_emails(
    context: ToolContext,
    n_emails: Annotated[int, "Number of emails to read"] = 5,
) -> Annotated[str, "A list of email details in JSON format"]:
    """
    Read emails from a Gmail account and extract plain text content.

    Args:
        context (ToolContext): The context containing authorization information.
        n_emails (int): Number of emails to read (default: 5).

    Returns:
        Dict[str, List[Dict[str, str]]]: A dictionary containing a list of email details.
    """
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    try:
        messages = (
            service.users().messages().list(userId="me").execute().get("messages", [])
        )

        if not messages:
            return {"emails": []}

        emails = []
        for msg in messages[:n_emails]:
            try:
                email_data = (
                    service.users().messages().get(userId="me", id=msg["id"]).execute()
                )
                email_details = parse_email(email_data)
                if email_details:
                    emails.append(email_details)
            except Exception as e:
                print(f"Error reading email {msg['id']}: {e}")

        return json.dumps({"emails": emails})

    except Exception as e:
        print(f"Error reading emails: {e}")
        return "Error reading emails"

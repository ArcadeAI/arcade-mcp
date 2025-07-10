import logging
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.mime.text import MIMEText
from enum import Enum
from typing import Any

from arcade_tdk import ToolContext
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from arcade_gmail.enums import (
    GmailAction,
    GmailReplyToWhom,
)
from arcade_gmail.exceptions import GmailServiceError, GmailToolError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class DateRange(Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"

    def to_date_query(self) -> str:
        today = datetime.now()
        result = "after:"
        comparison_date = today

        if self == DateRange.YESTERDAY:
            comparison_date = today - timedelta(days=1)
        elif self == DateRange.LAST_7_DAYS:
            comparison_date = today - timedelta(days=7)
        elif self == DateRange.LAST_30_DAYS:
            comparison_date = today - timedelta(days=30)
        elif self == DateRange.THIS_MONTH:
            comparison_date = today.replace(day=1)
        elif self == DateRange.LAST_MONTH:
            comparison_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif self == DateRange.THIS_YEAR:
            comparison_date = today.replace(month=1, day=1)
        elif self == DateRange.LAST_MONTH:
            comparison_date = (today.replace(month=1, day=1) - timedelta(days=1)).replace(
                month=1, day=1
            )

        return result + comparison_date.strftime("%Y/%m/%d")


def build_email_message(
    recipient: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    replying_to: dict[str, Any] | None = None,
    action: GmailAction = GmailAction.SEND,
) -> dict[str, Any]:
    if replying_to:
        body = build_reply_body(body, replying_to)

    message: EmailMessage | MIMEText

    if action == GmailAction.SEND:
        message = EmailMessage()
        message.set_content(body)
    elif action == GmailAction.DRAFT:
        message = MIMEText(body)

    message["To"] = recipient
    message["Subject"] = subject

    if cc:
        message["Cc"] = ",".join(cc)
    if bcc:
        message["Bcc"] = ",".join(bcc)
    if replying_to:
        message["In-Reply-To"] = replying_to["header_message_id"]
        message["References"] = f"{replying_to['header_message_id']}, {replying_to['references']}"

    encoded_message = urlsafe_b64encode(message.as_bytes()).decode()

    data = {"raw": encoded_message}

    if replying_to:
        data["threadId"] = replying_to["thread_id"]

    return data


def _build_gmail_service(context: ToolContext) -> Any:
    """
    Private helper function to build and return the Gmail service client.

    Args:
        context (ToolContext): The context containing authorization details.

    Returns:
        googleapiclient.discovery.Resource: An authorized Gmail API service instance.
    """
    try:
        credentials = Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        )
    except Exception as e:
        raise GmailServiceError(message="Failed to build Gmail service.", developer_message=str(e))

    return build("gmail", "v1", credentials=credentials)


def build_gmail_query_string(
    sender: str | None = None,
    recipient: str | None = None,
    subject: str | None = None,
    body: str | None = None,
    date_range: DateRange | None = None,
    label: str | None = None,
) -> str:
    """Helper function to build a query string
    for Gmail list_emails_by_header and search_threads tools.
    """
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
    if label:
        query.append(f"label:{label}")
    return " ".join(query)


def get_label_ids(service: Any, label_names: list[str]) -> dict[str, str]:
    """
    Retrieve label IDs for given label names.
    Returns a dictionary mapping label names to their IDs.

    Args:
        service: Authenticated Gmail API service instance.
        label_names: List of label names to retrieve IDs for.

    Returns:
        A dictionary mapping found label names to their corresponding IDs.
    """
    try:
        # Fetch all existing labels from Gmail
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
    except Exception as e:
        raise GmailToolError(message="Failed to list labels.", developer_message=str(e)) from e

    # Create a mapping from label names to their IDs
    label_id_map = {label["name"]: label["id"] for label in labels}

    found_labels = {}
    for name in label_names:
        label_id = label_id_map.get(name)
        if label_id:
            found_labels[name] = label_id
        else:
            logger.warning(f"Label '{name}' does not exist")

    return found_labels


def fetch_messages(service: Any, query_string: str, limit: int) -> list[dict[str, Any]]:
    """
    Helper function to fetch messages from Gmail API for the list_emails_by_header tool.
    """
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query_string, maxResults=limit or 100)
        .execute()
    )
    return response.get("messages", [])  # type: ignore[no-any-return]


def remove_none_values(params: dict) -> dict:
    """
    Remove None values from a dictionary.
    :param params: The dictionary to clean
    :return: A new dictionary with None values removed
    """
    return {k: v for k, v in params.items() if v is not None}


def build_reply_recipients(
    replying_to: dict[str, Any], current_user_email_address: str, reply_to_whom: GmailReplyToWhom
) -> str:
    if reply_to_whom == GmailReplyToWhom.ONLY_THE_SENDER:
        recipients = [replying_to["from"]]
    elif reply_to_whom == GmailReplyToWhom.EVERY_RECIPIENT:
        recipients = [replying_to["from"], *replying_to["to"].split(",")]
    else:
        raise ValueError(f"Unsupported reply_to_whom value: {reply_to_whom}")

    recipients = [
        email_address.strip()
        for email_address in recipients
        if email_address.strip().lower() != current_user_email_address.lower().strip()
    ]

    return ", ".join(recipients)


def get_draft_url(draft_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#drafts/{draft_id}"


def get_sent_email_url(sent_email_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#sent/{sent_email_id}"


def get_email_details(service: Any, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Retrieves full message data for each message ID in the given list and extracts email details.

    :param service: Authenticated Gmail API service instance.
    :param messages: A list of dictionaries, each representing a message with an 'id' key.
    :return: A list of dictionaries, each containing parsed email details.
    """

    emails = []
    for msg in messages:
        try:
            # Fetch the full message data from Gmail using the message ID
            email_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            # Parse the raw email data into a structured form
            email_details = parse_plain_text_email(email_data)
            # Only add the details if parsing was successful
            if email_details:
                emails.append(email_details)
        except Exception as e:
            # Log any errors encountered while trying to fetch or parse a message
            raise GmailToolError(
                message=f"Error reading email {msg['id']}.", developer_message=str(e)
            )
    return emails


def get_email_in_trash_url(email_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#trash/{email_id}"


def parse_draft_email(draft_email_data: dict[str, Any]) -> dict[str, str]:
    """
    Parse draft email data and extract relevant information.

    Args:
        draft_email_data (Dict[str, Any]): Raw draft email data from Gmail API.

    Returns:
        dict[str, str]: Parsed draft email details
    """
    message = draft_email_data.get("message", {})
    payload = message.get("payload", {})
    headers = {d["name"].lower(): d["value"] for d in payload.get("headers", [])}

    body_data = _get_email_plain_text_body(payload)

    return {
        "id": draft_email_data.get("id", ""),
        "thread_id": draft_email_data.get("threadId", ""),
        "from": headers.get("from", ""),
        "date": headers.get("internaldate", ""),
        "subject": headers.get("subject", ""),
        "body": _clean_email_body(body_data) if body_data else "",
    }


def _clean_email_body(body: str | None) -> str:
    """
    Remove HTML tags and clean up email body text while preserving most content.

    Args:
        body (str): The raw email body text.

    Returns:
        str: Cleaned email body text.
    """
    if not body:
        return ""

    try:
        # Remove HTML tags using BeautifulSoup
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(separator=" ")

        # Clean up the text
        cleaned_text = _clean_text(text)

        return cleaned_text.strip()
    except Exception:
        logger.exception("Error cleaning email body")
        return body


def _get_email_plain_text_body(payload: dict[str, Any]) -> str | None:
    """
    Extract email body from payload, handling 'multipart/alternative' parts.

    Args:
        payload (Dict[str, Any]): Email payload data.

    Returns:
        str | None: Decoded email body or None if not found.
    """
    # Direct body extraction
    if "body" in payload and payload["body"].get("data"):
        return _clean_email_body(urlsafe_b64decode(payload["body"]["data"]).decode())

    # Handle multipart and alternative parts
    return _clean_email_body(_extract_plain_body(payload.get("parts", [])))


def _extract_plain_body(parts: list) -> str | None:
    """
    Recursively extract the email body from parts, handling both plain text and HTML.

    Args:
        parts (List[Dict[str, Any]]): List of email parts.

    Returns:
        str | None: Decoded and cleaned email body or None if not found.
    """
    for part in parts:
        mime_type = part.get("mimeType")

        if mime_type == "text/plain" and "data" in part.get("body", {}):
            return urlsafe_b64decode(part["body"]["data"]).decode()

        elif mime_type.startswith("multipart/"):
            subparts = part.get("parts", [])
            body = _extract_plain_body(subparts)
            if body:
                return body

    return _extract_html_body(parts)


def _extract_html_body(parts: list) -> str | None:
    """
    Recursively extract the email body from parts, handling only HTML.

    Args:
        parts (List[Dict[str, Any]]): List of email parts.

    Returns:
        str | None: Decoded and cleaned email body or None if not found.
    """
    for part in parts:
        mime_type = part.get("mimeType")

        if mime_type == "text/html" and "data" in part.get("body", {}):
            html_content = urlsafe_b64decode(part["body"]["data"]).decode()
            return html_content

        elif mime_type.startswith("multipart/"):
            subparts = part.get("parts", [])
            body = _extract_html_body(subparts)
            if body:
                return body

    return None


def _clean_text(text: str) -> str:
    """
    Clean up the text while preserving most content.

    Args:
        text (str): The input text.

    Returns:
        str: Cleaned text.
    """
    # Replace multiple newlines with a single newline
    text = re.sub(r"\n+", "\n", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace from each line
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text


def parse_plain_text_email(email_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse email data and extract relevant information.
    Only returns the plain text body.

    Args:
        email_data (dict[str, Any]): Raw email data from Gmail API.

    Returns:
        dict[str, str]: Parsed email details
    """
    payload = email_data.get("payload", {})
    headers = {d["name"].lower(): d["value"] for d in payload.get("headers", [])}

    body_data = _get_email_plain_text_body(payload)

    email_details = {
        "id": email_data.get("id", ""),
        "thread_id": email_data.get("threadId", ""),
        "label_ids": email_data.get("labelIds", []),
        "history_id": email_data.get("historyId", ""),
        "snippet": email_data.get("snippet", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "from": headers.get("from", ""),
        "reply_to": headers.get("reply-to", ""),
        "in_reply_to": headers.get("in-reply-to", ""),
        "references": headers.get("references", ""),
        "header_message_id": headers.get("message-id", ""),
        "date": headers.get("date", ""),
        "subject": headers.get("subject", ""),
        "body": body_data or "",
    }

    return email_details


def build_reply_body(body: str, replying_to: dict[str, Any]) -> str:
    attribution = f"On {replying_to['date']}, {replying_to['from']} wrote:"
    lines = replying_to["plain_text_body"].split("\n")
    quoted_plain = "\n".join([f"> {line}" for line in lines])
    return f"{body}\n\n{attribution}\n\n{quoted_plain}"


def parse_multipart_email(email_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse email data and extract relevant information.
    Returns the plain text and HTML body along with the images.

    Args:
        email_data (Dict[str, Any]): Raw email data from Gmail API.

    Returns:
        dict[str, Any]: Parsed email details
    """

    payload = email_data.get("payload", {})
    headers = {d["name"].lower(): d["value"] for d in payload.get("headers", [])}

    # Extract different parts of the email
    plain_text_body = _get_email_plain_text_body(payload)
    html_body = _get_email_html_body(payload)

    email_details = {
        "id": email_data.get("id", ""),
        "thread_id": email_data.get("threadId", ""),
        "label_ids": email_data.get("labelIds", []),
        "history_id": email_data.get("historyId", ""),
        "snippet": email_data.get("snippet", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "from": headers.get("from", ""),
        "reply_to": headers.get("reply-to", ""),
        "in_reply_to": headers.get("in-reply-to", ""),
        "references": headers.get("references", ""),
        "header_message_id": headers.get("message-id", ""),
        "date": headers.get("date", ""),
        "subject": headers.get("subject", ""),
        "plain_text_body": plain_text_body or _clean_email_body(html_body),
        "html_body": html_body or "",
    }

    return email_details


def _get_email_html_body(payload: dict[str, Any]) -> str | None:
    """
    Extract email html body from payload, handling 'multipart/alternative' parts.

    Args:
        payload (Dict[str, Any]): Email payload data.

    Returns:
        str | None: Decoded email body or None if not found.
    """
    # Direct body extraction
    if "body" in payload and payload["body"].get("data"):
        return urlsafe_b64decode(payload["body"]["data"]).decode()

    # Handle multipart and alternative parts
    return _extract_html_body(payload.get("parts", []))

import logging
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, cast
from zoneinfo import ZoneInfo

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from arcade_google.constants import (
    DEFAULT_SEARCH_CONTACTS_LIMIT,
    DEFAULT_SHEET_COLUMN_COUNT,
    DEFAULT_SHEET_ROW_COUNT,
)
from arcade_google.exceptions import GmailToolError, GoogleServiceError
from arcade_google.models import (
    CellData,
    CellExtendedValue,
    CellFormat,
    CellValue,
    Corpora,
    Day,
    GmailAction,
    GmailReplyToWhom,
    GridData,
    GridProperties,
    NumberFormat,
    NumberFormatType,
    OrderBy,
    RowData,
    Sheet,
    SheetDataInput,
    SheetProperties,
    TimeSlot,
)

## Set up basic configuration for logging to the console with DEBUG level and a specific format.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def parse_datetime(datetime_str: str, time_zone: str) -> datetime:
    """
    Parse a datetime string in ISO 8601 format and ensure it is timezone-aware.

    Args:
        datetime_str (str): The datetime string to parse. Expected format: 'YYYY-MM-DDTHH:MM:SS'.
        time_zone (str): The timezone to apply if the datetime string is naive.

    Returns:
        datetime: A timezone-aware datetime object.

    Raises:
        ValueError: If the datetime string is not in the correct format.
    """
    datetime_str = datetime_str.upper().strip().rstrip("Z")
    try:
        dt = datetime.fromisoformat(datetime_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(time_zone))
    except ValueError as e:
        raise ValueError(
            f"Invalid datetime format: '{datetime_str}'. "
            "Expected ISO 8601 format, e.g., '2024-12-31T15:30:00'."
        ) from e
    return dt


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


def build_reply_body(body: str, replying_to: dict[str, Any]) -> str:
    attribution = f"On {replying_to['date']}, {replying_to['from']} wrote:"
    lines = replying_to["plain_text_body"].split("\n")
    quoted_plain = "\n".join([f"> {line}" for line in lines])
    return f"{body}\n\n{attribution}\n\n{quoted_plain}"


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
        raise GoogleServiceError(message="Failed to build Gmail service.", developer_message=str(e))

    return build("gmail", "v1", credentials=credentials)


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


def _get_email_images(payload: dict[str, Any]) -> list[str] | None:
    """
    Extract the email images from an email payload.

    Args:
        payload (Dict[str, Any]): Email payload data.

    Returns:
        list[str] | None: List of decoded image contents or None if none found.
    """
    images = []
    for part in payload.get("parts", []):
        mime_type = part.get("mimeType")

        if mime_type.startswith("image/") and "data" in part.get("body", {}):
            image_content = part["body"]["data"]
            images.append(image_content)

        elif mime_type.startswith("multipart/"):
            subparts = part.get("parts", [])
            subimages = _get_email_images(subparts)
            if subimages:
                images.extend(subimages)

    if images:
        return images

    return None


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


def _update_datetime(day: Day | None, time: TimeSlot | None, time_zone: str) -> dict | None:
    """
    Update the datetime for a Google Calendar event.

    Args:
        day (Day | None): The day of the event.
        time (TimeSlot | None): The time of the event.
        time_zone (str): The time zone of the event.

    Returns:
        dict | None: The updated datetime for the event.
    """
    if day and time:
        dt = datetime.combine(day.to_date(time_zone), time.to_time())
        return {"dateTime": dt.isoformat(), "timeZone": time_zone}
    return None


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


# Drive utils
def build_drive_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Drive service object.
    """
    auth_token = auth_token or ""
    return build("drive", "v3", credentials=Credentials(auth_token))


def build_files_list_query(
    mime_type: str,
    document_contains: list[str] | None = None,
    document_not_contains: list[str] | None = None,
) -> str:
    query = [f"(mimeType = '{mime_type}' and trashed = false)"]

    if isinstance(document_contains, str):
        document_contains = [document_contains]

    if isinstance(document_not_contains, str):
        document_not_contains = [document_not_contains]

    if document_contains:
        for keyword in document_contains:
            name_contains = keyword.replace("'", "\\'")
            full_text_contains = keyword.replace("'", "\\'")
            keyword_query = (
                f"(name contains '{name_contains}' or fullText contains '{full_text_contains}')"
            )
            query.append(keyword_query)

    if document_not_contains:
        for keyword in document_not_contains:
            name_not_contains = keyword.replace("'", "\\'")
            full_text_not_contains = keyword.replace("'", "\\'")
            keyword_query = (
                f"(name not contains '{name_not_contains}' and "
                f"fullText not contains '{full_text_not_contains}')"
            )
            query.append(keyword_query)

    return " and ".join(query)


def build_files_list_params(
    mime_type: str,
    page_size: int,
    order_by: list[OrderBy],
    pagination_token: str | None,
    include_shared_drives: bool,
    search_only_in_shared_drive_id: str | None,
    include_organization_domain_documents: bool,
    document_contains: list[str] | None = None,
    document_not_contains: list[str] | None = None,
) -> dict[str, Any]:
    query = build_files_list_query(
        mime_type=mime_type,
        document_contains=document_contains,
        document_not_contains=document_not_contains,
    )

    params = {
        "q": query,
        "pageSize": page_size,
        "orderBy": ",".join([item.value for item in order_by]),
        "pageToken": pagination_token,
    }

    if (
        include_shared_drives
        or search_only_in_shared_drive_id
        or include_organization_domain_documents
    ):
        params["includeItemsFromAllDrives"] = "true"
        params["supportsAllDrives"] = "true"

    if search_only_in_shared_drive_id:
        params["driveId"] = search_only_in_shared_drive_id
        params["corpora"] = Corpora.DRIVE.value

    if include_organization_domain_documents:
        params["corpora"] = Corpora.DOMAIN.value

    params = remove_none_values(params)

    return params


def build_file_tree_request_params(
    order_by: list[OrderBy] | None,
    page_token: str | None,
    limit: int | None,
    include_shared_drives: bool,
    restrict_to_shared_drive_id: str | None,
    include_organization_domain_documents: bool,
) -> dict[str, Any]:
    if order_by is None:
        order_by = [OrderBy.MODIFIED_TIME_DESC]
    elif isinstance(order_by, OrderBy):
        order_by = [order_by]

    params = {
        "q": "trashed = false",
        "corpora": Corpora.USER.value,
        "pageToken": page_token,
        "fields": (
            "files(id, name, parents, mimeType, driveId, size, createdTime, modifiedTime, owners)"
        ),
        "orderBy": ",".join([item.value for item in order_by]),
    }

    if limit:
        params["pageSize"] = str(limit)

    if (
        include_shared_drives
        or restrict_to_shared_drive_id
        or include_organization_domain_documents
    ):
        params["includeItemsFromAllDrives"] = "true"
        params["supportsAllDrives"] = "true"

    if restrict_to_shared_drive_id:
        params["driveId"] = restrict_to_shared_drive_id
        params["corpora"] = Corpora.DRIVE.value

    if include_organization_domain_documents:
        params["corpora"] = Corpora.DOMAIN.value

    return params


def build_file_tree(files: dict[str, Any]) -> dict[str, Any]:
    file_tree: dict[str, Any] = {}

    for file in files.values():
        owners = file.get("owners", [])
        if owners:
            owners = [
                {"name": owner.get("displayName", ""), "email": owner.get("emailAddress", "")}
                for owner in owners
            ]
            file["owners"] = owners

        if "size" in file:
            file["size"] = {"value": int(file["size"]), "unit": "bytes"}

        # Although "parents" is a list, a file can only have one parent
        try:
            parent_id = file["parents"][0]
            del file["parents"]
        except (KeyError, IndexError):
            parent_id = None

        # Determine the file's Drive ID
        if "driveId" in file:
            drive_id = file["driveId"]
            del file["driveId"]
        # If a shared drive id is not present, the file is in "My Drive"
        else:
            drive_id = "My Drive"

        if drive_id not in file_tree:
            file_tree[drive_id] = []

        # Root files will have the Drive's id as the parent. If the parent id is not in the files
        # list, the file must be at drive's root
        if parent_id not in files:
            file_tree[drive_id].append(file)

        # Associate the file with its parent
        else:
            if "children" not in files[parent_id]:
                files[parent_id]["children"] = []
            files[parent_id]["children"].append(file)

    return file_tree


# Docs utils
def build_docs_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Drive service object.
    """
    auth_token = auth_token or ""
    return build("docs", "v1", credentials=Credentials(auth_token))


def parse_rfc3339_datetime_str(dt_str: str, tz: timezone = timezone.utc) -> datetime:
    """
    Parse an RFC3339 datetime string into a timezone-aware datetime.
    Converts a trailing 'Z' (UTC) into +00:00.
    If the parsed datetime is naive, assume it is in the provided timezone.
    """
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """
    Given a list of (start, end) tuples, merge overlapping or adjacent intervals.
    """
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(intervals, key=lambda x: x[0]):
        if not merged:
            merged.append((start, end))
        else:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
    return merged


# Calendar utils


def build_oauth_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build an OAuth2 service object.
    """
    auth_token = auth_token or ""
    return build("oauth2", "v2", credentials=Credentials(auth_token))


def build_calendar_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Calendar service object.
    """
    auth_token = auth_token or ""
    return build("calendar", "v3", credentials=Credentials(auth_token))


def weekday_to_name(weekday: int) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday]


def get_time_boundaries_for_date(
    current_date: date,
    global_start: datetime,
    global_end: datetime,
    start_time_boundary: time,
    end_time_boundary: time,
    tz: ZoneInfo,
) -> tuple[datetime, datetime]:
    """Compute the allowed start and end times for the given day, adjusting for global bounds."""
    day_start_time = datetime.combine(current_date, start_time_boundary).replace(tzinfo=tz)
    day_end_time = datetime.combine(current_date, end_time_boundary).replace(tzinfo=tz)

    if current_date == global_start.date():
        day_start_time = max(day_start_time, global_start)

    if current_date == global_end.date():
        day_end_time = min(day_end_time, global_end)

    return day_start_time, day_end_time


def gather_busy_intervals(
    busy_data: dict[str, Any],
    day_start: datetime,
    day_end: datetime,
    business_tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    """
    Collect busy intervals from all calendars that intersect with the day's business hours.
    Busy intervals are clipped to lie within [day_start, day_end].
    """
    busy_intervals = []
    for calendar in busy_data:
        for slot in busy_data[calendar].get("busy", []):
            slot_start = parse_rfc3339_datetime_str(slot["start"]).astimezone(business_tz)
            slot_end = parse_rfc3339_datetime_str(slot["end"]).astimezone(business_tz)
            if slot_end > day_start and slot_start < day_end:
                busy_intervals.append((max(slot_start, day_start), min(slot_end, day_end)))
    return busy_intervals


def subtract_busy_intervals(
    business_start: datetime,
    business_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
) -> list[dict[str, Any]]:
    """
    Subtract the merged busy intervals from the business hours and return free time slots.
    """
    free_slots = []
    merged_busy = merge_intervals(busy_intervals)

    # If there are no busy intervals, return the entire business window as free.
    if not merged_busy:
        return [
            {
                "start": {
                    "datetime": business_start.isoformat(),
                    "weekday": weekday_to_name(business_start.weekday()),
                },
                "end": {
                    "datetime": business_end.isoformat(),
                    "weekday": weekday_to_name(business_end.weekday()),
                },
            }
        ]

    current_free_start = business_start
    for busy_start, busy_end in merged_busy:
        if current_free_start < busy_start:
            free_slots.append({
                "start": {
                    "datetime": current_free_start.isoformat(),
                    "weekday": weekday_to_name(current_free_start.weekday()),
                },
                "end": {
                    "datetime": busy_start.isoformat(),
                    "weekday": weekday_to_name(busy_start.weekday()),
                },
            })
        current_free_start = max(current_free_start, busy_end)
    if current_free_start < business_end:
        free_slots.append({
            "start": {
                "datetime": current_free_start.isoformat(),
                "weekday": weekday_to_name(current_free_start.weekday()),
            },
            "end": {
                "datetime": business_end.isoformat(),
                "weekday": weekday_to_name(business_end.weekday()),
            },
        })
    return free_slots


def compute_free_time_intersection(
    busy_data: dict[str, Any],
    global_start: datetime,
    global_end: datetime,
    start_time_boundary: time,
    end_time_boundary: time,
    include_weekends: bool,
    tz: ZoneInfo,
) -> list[dict[str, Any]]:
    """
    Returns the free time slots across all calendars within the global bounds,
    ensuring that the global start is not in the past.

    Only considers business days (Monday to Friday) and business hours (08:00-19:00)
    in the provided timezone.
    """
    # Ensure global_start is never in the past relative to now.
    now = get_now(tz)

    if now > global_start:
        global_start = now

    # If after adjusting the start, there's no interval left, return empty.
    if global_start >= global_end:
        return []

    free_slots = []
    current_date = global_start.date()

    while current_date <= global_end.date():
        if not include_weekends and current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        day_start, day_end = get_time_boundaries_for_date(
            current_date=current_date,
            global_start=global_start,
            global_end=global_end,
            start_time_boundary=start_time_boundary,
            end_time_boundary=end_time_boundary,
            tz=tz,
        )

        # Skip if the day's allowed time window is empty.
        if day_start >= day_end:
            current_date += timedelta(days=1)
            continue

        busy_intervals = gather_busy_intervals(busy_data, day_start, day_end, tz)
        free_slots.extend(subtract_busy_intervals(day_start, day_end, busy_intervals))

        current_date += timedelta(days=1)

    return free_slots


def get_now(tz: ZoneInfo | None = None) -> datetime:
    if not tz:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


# Contacts utils
def build_people_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a People service object.
    """
    auth_token = auth_token or ""
    return build("people", "v1", credentials=Credentials(auth_token))


def search_contacts(service: Any, query: str, limit: int | None) -> list[dict[str, Any]]:
    """
    Search the user's contacts in Google Contacts.
    """
    response = (
        service.people()
        .searchContacts(
            query=query,
            pageSize=limit or DEFAULT_SEARCH_CONTACTS_LIMIT,
            readMask=",".join([
                "names",
                "nicknames",
                "emailAddresses",
                "phoneNumbers",
                "addresses",
                "organizations",
                "biographies",
                "urls",
                "userDefined",
            ]),
        )
        .execute()
    )

    return cast(list[dict[str, Any]], response.get("results", []))


# ----------------------------------------------------------------
# Sheets utils
# ----------------------------------------------------------------


def build_sheets_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Sheets service object.
    """
    auth_token = auth_token or ""
    return build("sheets", "v4", credentials=Credentials(auth_token))


def col_to_index(col: str) -> int:
    """Convert a sheet's column string to a 0-indexed column index

    Args:
        col (str): The column string to convert. e.g., "A", "AZ", "QED"

    Returns:
        int: The 0-indexed column index.
    """
    result = 0
    for char in col.upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def index_to_col(index: int) -> str:
    """Convert a 0-indexed column index to its corresponding column string

    Args:
        index (int): The 0-indexed column index to convert.

    Returns:
        str: The column string. e.g., "A", "AZ", "QED"
    """
    result = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        result = chr(rem + ord("A")) + result
    return result


def is_col_greater(col1: str, col2: str) -> bool:
    """Determine if col1 represents a column that comes after col2 in a sheet

    This comparison is based on:
      1. The length of the column string (longer means greater).
      2. Lexicographical comparison if both strings are the same length.

    Args:
        col1 (str): The first column string to compare.
        col2 (str): The second column string to compare.

    Returns:
        bool: True if col1 comes after col2, False otherwise.
    """
    if len(col1) != len(col2):
        return len(col1) > len(col2)
    return col1.upper() > col2.upper()


def compute_sheet_data_dimensions(
    sheet_data_input: SheetDataInput,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Compute the dimensions of a sheet based on the data provided.

    Args:
        sheet_data_input (SheetDataInput):
            The data to compute the dimensions of.

    Returns:
        tuple[tuple[int, int], tuple[int, int]]: The dimensions of the sheet. The first tuple
            contains the row range (start, end) and the second tuple contains the column range
            (start, end).
    """
    max_row = 0
    min_row = 10_000_000  # max number of cells in a sheet
    max_col_str = None
    min_col_str = None

    for key, row in sheet_data_input.data.items():
        try:
            row_num = int(key)
        except ValueError:
            continue
        if row_num > max_row:
            max_row = row_num
        if row_num < min_row:
            min_row = row_num

        if isinstance(row, dict):
            for col in row:
                # Update max column string
                if max_col_str is None or is_col_greater(col, max_col_str):
                    max_col_str = col
                # Update min column string
                if min_col_str is None or is_col_greater(min_col_str, col):
                    min_col_str = col

    max_col_index = col_to_index(max_col_str) if max_col_str is not None else -1
    min_col_index = col_to_index(min_col_str) if min_col_str is not None else 0

    return (min_row, max_row), (min_col_index, max_col_index)


def create_sheet(sheet_data_input: SheetDataInput) -> Sheet:
    """Create a Google Sheet from a dictionary of data.

    Args:
        sheet_data_input (SheetDataInput): The data to create the sheet from.

    Returns:
        Sheet: The created sheet.
    """
    (_, max_row), (min_col_index, max_col_index) = compute_sheet_data_dimensions(sheet_data_input)
    sheet_data = create_sheet_data(sheet_data_input, min_col_index, max_col_index)
    sheet_properties = create_sheet_properties(
        row_count=max(DEFAULT_SHEET_ROW_COUNT, max_row),
        column_count=max(DEFAULT_SHEET_COLUMN_COUNT, max_col_index + 1),
    )

    return Sheet(properties=sheet_properties, data=sheet_data)


def create_sheet_properties(
    sheet_id: int = 1,
    title: str = "Sheet1",
    row_count: int = DEFAULT_SHEET_ROW_COUNT,
    column_count: int = DEFAULT_SHEET_COLUMN_COUNT,
) -> SheetProperties:
    """Create a SheetProperties object

    Args:
        sheet_id (int): The ID of the sheet.
        title (str): The title of the sheet.
        row_count (int): The number of rows in the sheet.
        column_count (int): The number of columns in the sheet.

    Returns:
        SheetProperties: The created sheet properties object.
    """
    return SheetProperties(
        sheetId=sheet_id,
        title=title,
        gridProperties=GridProperties(rowCount=row_count, columnCount=column_count),
    )


def group_contiguous_rows(row_numbers: list[int]) -> list[list[int]]:
    """Groups a sorted list of row numbers into contiguous groups

    A contiguous group is a list of row numbers that are consecutive integers.
    For example, [1,2,3,5,6] is converted to [[1,2,3],[5,6]].

    Args:
        row_numbers (list[int]): The list of row numbers to group.

    Returns:
        list[list[int]]: The grouped row numbers.
    """
    if not row_numbers:
        return []
    groups = []
    current_group = [row_numbers[0]]
    for r in row_numbers[1:]:
        if r == current_group[-1] + 1:
            current_group.append(r)
        else:
            groups.append(current_group)
            current_group = [r]
    groups.append(current_group)
    return groups


def create_cell_data(cell_value: CellValue) -> CellData:
    """
    Create a CellData object based on the type of cell_value.
    """
    if isinstance(cell_value, bool):
        return _create_bool_cell(cell_value)
    elif isinstance(cell_value, int):
        return _create_int_cell(cell_value)
    elif isinstance(cell_value, float):
        return _create_float_cell(cell_value)
    elif isinstance(cell_value, str):
        return _create_string_cell(cell_value)


def _create_formula_cell(cell_value: str) -> CellData:
    cell_val = CellExtendedValue(formulaValue=cell_value)
    return CellData(userEnteredValue=cell_val)


def _create_currency_cell(cell_value: str) -> CellData:
    value_without_symbol = cell_value[1:]
    try:
        num_value = int(value_without_symbol)
        cell_format = CellFormat(
            numberFormat=NumberFormat(type=NumberFormatType.CURRENCY, pattern="$#,##0")
        )
        cell_val = CellExtendedValue(numberValue=num_value)
        return CellData(userEnteredValue=cell_val, userEnteredFormat=cell_format)
    except ValueError:
        try:
            num_value = float(value_without_symbol)  # type: ignore[assignment]
            cell_format = CellFormat(
                numberFormat=NumberFormat(type=NumberFormatType.CURRENCY, pattern="$#,##0.00")
            )
            cell_val = CellExtendedValue(numberValue=num_value)
            return CellData(userEnteredValue=cell_val, userEnteredFormat=cell_format)
        except ValueError:
            return CellData(userEnteredValue=CellExtendedValue(stringValue=cell_value))


def _create_percent_cell(cell_value: str) -> CellData:
    try:
        num_value = float(cell_value[:-1].strip())
        cell_format = CellFormat(
            numberFormat=NumberFormat(type=NumberFormatType.PERCENT, pattern="0.00%")
        )
        cell_val = CellExtendedValue(numberValue=num_value)
        return CellData(userEnteredValue=cell_val, userEnteredFormat=cell_format)
    except ValueError:
        return CellData(userEnteredValue=CellExtendedValue(stringValue=cell_value))


def _create_bool_cell(cell_value: bool) -> CellData:
    return CellData(userEnteredValue=CellExtendedValue(boolValue=cell_value))


def _create_int_cell(cell_value: int) -> CellData:
    cell_format = CellFormat(
        numberFormat=NumberFormat(type=NumberFormatType.NUMBER, pattern="#,##0")
    )
    return CellData(
        userEnteredValue=CellExtendedValue(numberValue=cell_value), userEnteredFormat=cell_format
    )


def _create_float_cell(cell_value: float) -> CellData:
    cell_format = CellFormat(
        numberFormat=NumberFormat(type=NumberFormatType.NUMBER, pattern="#,##0.00")
    )
    return CellData(
        userEnteredValue=CellExtendedValue(numberValue=cell_value), userEnteredFormat=cell_format
    )


def _create_string_cell(cell_value: str) -> CellData:
    if cell_value.startswith("="):
        return _create_formula_cell(cell_value)
    elif cell_value.startswith("$") and len(cell_value) > 1:
        return _create_currency_cell(cell_value)
    elif cell_value.endswith("%") and len(cell_value) > 1:
        return _create_percent_cell(cell_value)

    return CellData(userEnteredValue=CellExtendedValue(stringValue=cell_value))


def create_row_data(
    row_data: dict[str, CellValue], min_col_index: int, max_col_index: int
) -> RowData:
    """Constructs RowData for a single row using the provided row_data.

    Args:
        row_data (dict[str, CellValue]): The data to create the row from.
        min_col_index (int): The minimum column index from the SheetDataInput.
        max_col_index (int): The maximum column index from the SheetDataInput.
    """
    row_cells = []
    for col_idx in range(min_col_index, max_col_index + 1):
        col_letter = index_to_col(col_idx)
        if col_letter in row_data:
            cell_data = create_cell_data(row_data[col_letter])
        else:
            cell_data = CellData(userEnteredValue=CellExtendedValue(stringValue=""))
        row_cells.append(cell_data)
    return RowData(values=row_cells)


def create_sheet_data(
    sheet_data_input: SheetDataInput,
    min_col_index: int,
    max_col_index: int,
) -> list[GridData]:
    """Create grid data from SheetDataInput by grouping contiguous rows and processing cells.

    Args:
        sheet_data_input (SheetDataInput): The data to create the sheet from.
        min_col_index (int): The minimum column index from the SheetDataInput.
        max_col_index (int): The maximum column index from the SheetDataInput.

    Returns:
        list[GridData]: The created grid data.
    """
    row_numbers = list(sheet_data_input.data.keys())
    if not row_numbers:
        return []

    sorted_rows = sorted(row_numbers)
    groups = group_contiguous_rows(sorted_rows)

    sheet_data = []
    for group in groups:
        rows_data = []
        for r in group:
            current_row_data = sheet_data_input.data.get(r, {})
            row = create_row_data(current_row_data, min_col_index, max_col_index)
            rows_data.append(row)
        grid_data = GridData(
            startRow=group[0] - 1,  # convert to 0-indexed
            startColumn=min_col_index,
            rowData=rows_data,
        )
        sheet_data.append(grid_data)

    return sheet_data


def parse_get_spreadsheet_response(api_response: dict) -> dict:
    """
    Parse the get spreadsheet Google Sheets API response into a structured dictionary.
    """
    properties = api_response.get("properties", {})
    sheets = [parse_sheet(sheet) for sheet in api_response.get("sheets", [])]

    return {
        "title": properties.get("title", ""),
        "spreadsheetId": api_response.get("spreadsheetId", ""),
        "spreadsheetUrl": api_response.get("spreadsheetUrl", ""),
        "sheets": sheets,
    }


def parse_sheet(api_sheet: dict) -> dict:
    """
    Parse an individual sheet's data from the Google Sheets 'get spreadsheet'
    API response into a structured dictionary.
    """
    props = api_sheet.get("properties", {})
    grid_props = props.get("gridProperties", {})
    cell_data = convert_api_grid_data_to_dict(api_sheet.get("data", []))

    return {
        "sheetId": props.get("sheetId"),
        "title": props.get("title", ""),
        "rowCount": grid_props.get("rowCount", 0),
        "columnCount": grid_props.get("columnCount", 0),
        "data": cell_data,
    }


def extract_user_entered_cell_value(cell: dict) -> Any:
    """
    Extract the user entered value from a cell's 'userEnteredValue'.

    Args:
        cell (dict): A cell dictionary from the grid data.

    Returns:
        The extracted value if present, otherwise None.
    """
    user_val = cell.get("userEnteredValue", {})
    for key in ["stringValue", "numberValue", "boolValue", "formulaValue"]:
        if key in user_val:
            return user_val[key]

    return ""


def process_row(row: dict, start_column_index: int) -> dict:
    """
    Process a single row from grid data, converting non-empty cells into a dictionary
    that maps column letters to cell values.

    Args:
        row (dict): A row from the grid data.
        start_column_index (int): The starting column index for this row.

    Returns:
        dict: A mapping of column letters to cell values for non-empty cells.
    """
    row_result = {}
    for j, cell in enumerate(row.get("values", [])):
        column_index = start_column_index + j
        column_string = index_to_col(column_index)
        user_entered_cell_value = extract_user_entered_cell_value(cell)
        formatted_cell_value = cell.get("formattedValue", "")

        if user_entered_cell_value != "" or formatted_cell_value != "":
            row_result[column_string] = {
                "userEnteredValue": user_entered_cell_value,
                "formattedValue": formatted_cell_value,
            }

    return row_result


def convert_api_grid_data_to_dict(grids: list[dict]) -> dict:
    """
    Convert a list of grid data dictionaries from the 'get spreadsheet' API
    response into a structured cell dictionary.

    The returned dictionary maps row numbers to sub-dictionaries that map column letters
    (e.g., 'A', 'B', etc.) to their corresponding non-empty cell values.

    Args:
        grids (list[dict]): The list of grid data dictionaries from the API.

    Returns:
        dict: A dictionary mapping row numbers to dictionaries of column letter/value pairs.
            Only includes non-empty rows and non-empty cells.
    """
    result = {}
    for grid in grids:
        start_row = grid.get("startRow", 0)
        start_column = grid.get("startColumn", 0)

        for i, row in enumerate(grid.get("rowData", []), start=1):
            current_row = start_row + i
            row_data = process_row(row, start_column)

            if row_data:
                result[current_row] = row_data

    return dict(sorted(result.items()))


def validate_write_to_cell_params(  # type: ignore[no-any-unimported]
    service: Resource,
    spreadsheet_id: str,
    sheet_name: str,
    column: str,
    row: int,
) -> None:
    """Validates the input parameters for the write to cell tool.

    Args:
        service (Resource): The Google Sheets service.
        spreadsheet_id (str): The ID of the spreadsheet provided to the tool.
        sheet_name (str): The name of the sheet provided to the tool.
        column (str): The column to write to provided to the tool.
        row (int): The row to write to provided to the tool.

    Raises:
        RetryableToolError:
            If the sheet name is not found in the spreadsheet
        ToolExecutionError:
            If the column is not alphabetical
            If the row is not a positive number
            If the row is out of bounds for the sheet
            If the column is out of bounds for the sheet
    """
    if not column.isalpha():
        raise ToolExecutionError(
            message=(
                f"Invalid column name {column}. "
                "It must be a non-empty string containing only letters"
            ),
        )

    if row < 1:
        raise ToolExecutionError(
            message=(f"Invalid row number {row}. It must be a positive integer greater than 0."),
        )

    sheet_properties = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            fields="sheets/properties/title,sheets/properties/gridProperties/rowCount,sheets/properties/gridProperties/columnCount",
        )
        .execute()
    )
    sheet_names = [sheet["properties"]["title"] for sheet in sheet_properties["sheets"]]
    sheet_row_count = sheet_properties["sheets"][0]["properties"]["gridProperties"]["rowCount"]
    sheet_column_count = sheet_properties["sheets"][0]["properties"]["gridProperties"][
        "columnCount"
    ]

    if sheet_name not in sheet_names:
        raise RetryableToolError(
            message=f"Sheet name {sheet_name} not found in spreadsheet with id {spreadsheet_id}",
            additional_prompt_content=f"Sheet names in the spreadsheet: {sheet_names}",
            retry_after_ms=100,
        )

    if row > sheet_row_count:
        raise ToolExecutionError(
            message=(
                f"Row {row} is out of bounds for sheet {sheet_name} "
                f"in spreadsheet with id {spreadsheet_id}. "
                f"Sheet only has {sheet_row_count} rows which is less than the requested row {row}"
            )
        )

    if col_to_index(column) > sheet_column_count:
        raise ToolExecutionError(
            message=(
                f"Column {column} is out of bounds for sheet {sheet_name} "
                f"in spreadsheet with id {spreadsheet_id}. "
                f"Sheet only has {sheet_column_count} columns which "
                f"is less than the requested column {column}"
            )
        )


def parse_write_to_cell_response(response: dict) -> dict:
    return {
        "spreadsheetId": response["spreadsheetId"],
        "sheetTitle": response["updatedData"]["range"].split("!")[0],
        "updatedCell": response["updatedData"]["range"].split("!")[1],
        "value": response["updatedData"]["values"][0][0],
    }

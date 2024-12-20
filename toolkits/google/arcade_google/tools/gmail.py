import base64
from email.message import EmailMessage
from email.mime.text import MIMEText
from typing import Annotated, Any, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from arcade.sdk.errors import RetryableToolError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from arcade_google.tools.utils import (
    DateRange,
    build_query_string,
    fetch_messages,
    get_draft_url,
    get_email_in_trash_url,
    get_sent_email_url,
    parse_draft_email,
    parse_email,
    remove_none_values,
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
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """
    Send an email using the Gmail API.
    """

    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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

    email = parse_email(sent_message)
    email["url"] = get_sent_email_url(sent_message["id"])
    return email


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
)
async def send_draft_email(
    context: ToolContext, email_id: Annotated[str, "The ID of the draft to send"]
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """
    Send a draft email using the Gmail API.
    """

    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

    # Send the draft email
    sent_message = service.users().drafts().send(userId="me", body={"id": email_id}).execute()

    email = parse_email(sent_message)
    email["url"] = get_sent_email_url(sent_message["id"])
    return email


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
) -> Annotated[dict, "A dictionary containing the created draft email details"]:
    """
    Compose a new email draft using the Gmail API.
    """
    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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
    email = parse_draft_email(draft_message)
    email["url"] = get_draft_url(draft_message["id"])
    return email


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
) -> Annotated[dict, "A dictionary containing the updated draft email details"]:
    """
    Update an existing email draft using the Gmail API.
    """

    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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

    email = parse_draft_email(updated_draft_message)
    email["url"] = get_draft_url(updated_draft_message["id"])
    return email


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
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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
) -> Annotated[dict, "A dictionary containing the trashed email details"]:
    """
    Move an email to the trash folder using the Gmail API.
    """

    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

    # Trash the email
    trashed_email = service.users().messages().trash(userId="me", id=email_id).execute()

    email = parse_email(trashed_email)
    email["url"] = get_email_in_trash_url(trashed_email["id"])
    return email


# Draft Search Tools
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_draft_emails(
    context: ToolContext,
    n_drafts: Annotated[int, "Number of draft emails to read"] = 5,
) -> Annotated[dict, "A dictionary containing a list of draft email details"]:
    """
    Lists draft emails in the user's draft mailbox using the Gmail API.
    """
    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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

    return {"emails": emails}


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
    limit: Annotated[int, "The maximum number of emails to return"] = 25,
) -> Annotated[
    dict, "A dictionary containing a list of email details matching the search criteria"
]:
    """
    Search for emails by header using the Gmail API.
    At least one of the following parameters MUST be provided: sender, recipient, subject, body.
    """
    if not any([sender, recipient, subject, body]):
        raise RetryableToolError(
            message="At least one of sender, recipient, subject, or body must be provided.",
            developer_message=(
                "At least one of sender, recipient, subject, or body must be provided."
            ),
        )

    query = build_query_string(sender, recipient, subject, body, date_range)

    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )
    messages = fetch_messages(service, query, limit)

    if not messages:
        return {"emails": []}

    emails = process_messages(service, messages)
    return {"emails": emails}


def process_messages(service: Any, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
) -> Annotated[dict, "A dictionary containing a list of email details"]:
    """
    Read emails from a Gmail account and extract plain text content.
    """
    # Set up the Gmail API client
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

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

    return {"emails": emails}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def search_threads(
    context: ToolContext,
    page_token: Annotated[
        Optional[str], "Page token to retrieve a specific page of results in the list"
    ] = None,
    max_results: Annotated[int, "The maximum number of threads to return"] = 10,
    include_spam_trash: Annotated[bool, "Whether to include spam and trash in the results"] = False,
    label_ids: Annotated[Optional[list[str]], "The IDs of labels to filter by"] = None,
    sender: Annotated[Optional[str], "The name or email address of the sender of the email"] = None,
    recipient: Annotated[Optional[str], "The name or email address of the recipient"] = None,
    subject: Annotated[Optional[str], "Words to find in the subject of the email"] = None,
    body: Annotated[Optional[str], "Words to find in the body of the email"] = None,
    date_range: Annotated[Optional[DateRange], "The date range of the email"] = None,
) -> Annotated[dict, "A dictionary containing a list of thread details"]:
    """Search for threads in the user's mailbox"""
    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

    query = (
        build_query_string(sender, recipient, subject, body, date_range)
        if any([sender, recipient, subject, body, date_range])
        else None
    )

    params = {
        "userId": "me",
        "maxResults": min(max_results, 500),
        "pageToken": page_token,
        "includeSpamTrash": include_spam_trash,
        "labelIds": label_ids,
        "q": query,
    }
    params = remove_none_values(params)

    threads: list[dict[str, Any]] = []
    next_page_token = None
    # Paginate through thread pages until we have the desired number of threads
    while len(threads) < max_results:
        response = service.users().threads().list(**params).execute()

        threads.extend(response.get("threads", []))
        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        params["pageToken"] = next_page_token
        params["maxResults"] = min(max_results - len(threads), 500)

    return {
        "threads": threads,
        "num_threads": len(threads),
        "next_page_token": next_page_token,
    }


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_threads(
    context: ToolContext,
    page_token: Annotated[
        Optional[str], "Page token to retrieve a specific page of results in the list"
    ] = None,
    max_results: Annotated[int, "The maximum number of threads to return"] = 10,
    include_spam_trash: Annotated[bool, "Whether to include spam and trash in the results"] = False,
) -> Annotated[dict, "A dictionary containing a list of thread details"]:
    """List threads in the user's mailbox."""
    threads: dict[str, Any] = await search_threads(
        context, page_token, max_results, include_spam_trash
    )
    return threads


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def get_thread(
    context: ToolContext,
    thread_id: Annotated[str, "The ID of the thread to retrieve"],
    metadata_headers: Annotated[
        Optional[list[str]], "When given and format is METADATA, only include headers specified."
    ] = None,
) -> Annotated[dict, "A dictionary containing the thread details"]:
    """Get the specified thread by ID."""
    params = {
        "userId": "me",
        "id": thread_id,
        "format": "full",
        "metadataHeaders": metadata_headers,
    }
    params = remove_none_values(params)

    service = build(
        "gmail",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )
    thread = service.users().threads().get(**params).execute()
    thread["messages"] = [parse_email(message) for message in thread.get("messages", [])]

    return dict(thread)

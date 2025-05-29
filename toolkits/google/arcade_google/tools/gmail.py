import base64
from email.mime.text import MIMEText
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google
from arcade_tdk.errors import RetryableToolError
from googleapiclient.errors import HttpError

from arcade_google.constants import GMAIL_DEFAULT_REPLY_TO
from arcade_google.exceptions import GmailToolError
from arcade_google.models import GmailAction, GmailReplyToWhom
from arcade_google.utils import (
    DateRange,
    _build_gmail_service,
    build_email_message,
    build_gmail_query_string,
    build_reply_recipients,
    fetch_messages,
    get_draft_url,
    get_email_details,
    get_email_in_trash_url,
    get_label_ids,
    get_sent_email_url,
    parse_draft_email,
    parse_multipart_email,
    parse_plain_text_email,
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
    cc: Annotated[list[str] | None, "CC recipients of the email"] = None,
    bcc: Annotated[list[str] | None, "BCC recipients of the email"] = None,
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """
    Send an email using the Gmail API.
    """
    service = _build_gmail_service(context)
    email = build_email_message(recipient, subject, body, cc, bcc)

    sent_message = service.users().messages().send(userId="me", body=email).execute()

    email = parse_plain_text_email(sent_message)
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

    service = _build_gmail_service(context)

    # Send the draft email
    sent_message = service.users().drafts().send(userId="me", body={"id": email_id}).execute()

    email = parse_plain_text_email(sent_message)
    email["url"] = get_sent_email_url(sent_message["id"])
    return email


# Note: in the Gmail UI, a user can customize the recipient and cc fields before replying.
# We decided not to support this feature, since we'd need a way for LLMs to tell apart between
# adding or removing recipients/cc, or replacing with an entirely new list of addresses,
# which would make the tool more complex to call.
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
)
async def reply_to_email(
    context: ToolContext,
    body: Annotated[str, "The body of the email"],
    reply_to_message_id: Annotated[str, "The ID of the message to reply to"],
    reply_to_whom: Annotated[
        GmailReplyToWhom,
        "Whether to reply to every recipient (including cc) or only to the original sender. "
        f"Defaults to '{GMAIL_DEFAULT_REPLY_TO}'.",
    ] = GMAIL_DEFAULT_REPLY_TO,
    bcc: Annotated[list[str] | None, "BCC recipients of the email"] = None,
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """
    Send a reply to an email message.
    """
    if isinstance(reply_to_whom, str):
        reply_to_whom = GmailReplyToWhom(reply_to_whom)

    service = _build_gmail_service(context)

    current_user = service.users().getProfile(userId="me").execute()

    try:
        replying_to_email = (
            service.users().messages().get(userId="me", id=reply_to_message_id).execute()
        )
    except HttpError as e:
        raise RetryableToolError(
            message=f"Could not retrieve the message with id {reply_to_message_id}.",
            developer_message=(
                f"Could not retrieve the message with id {reply_to_message_id}. "
                f"Reason: '{e.reason}'. Error details: '{e.error_details}'"
            ),
        ) from e

    replying_to_email = parse_multipart_email(replying_to_email)

    recipients = build_reply_recipients(
        replying_to_email, current_user["emailAddress"], reply_to_whom
    )

    email = build_email_message(
        recipient=recipients,
        subject=f"Re: {replying_to_email['subject']}",
        body=body,
        cc=None
        if reply_to_whom == GmailReplyToWhom.ONLY_THE_SENDER
        else replying_to_email["cc"].split(","),
        bcc=bcc,
        replying_to=replying_to_email,
    )

    sent_message = service.users().messages().send(userId="me", body=email).execute()

    email = parse_plain_text_email(sent_message)
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
    cc: Annotated[list[str] | None, "CC recipients of the draft email"] = None,
    bcc: Annotated[list[str] | None, "BCC recipients of the draft email"] = None,
) -> Annotated[dict, "A dictionary containing the created draft email details"]:
    """
    Compose a new email draft using the Gmail API.
    """
    # Set up the Gmail API client
    service = _build_gmail_service(context)

    draft = {
        "message": build_email_message(recipient, subject, body, cc, bcc, action=GmailAction.DRAFT)
    }

    draft_message = service.users().drafts().create(userId="me", body=draft).execute()
    email = parse_draft_email(draft_message)
    email["url"] = get_draft_url(draft_message["id"])
    return email


# Note: in the Gmail UI, a user can customize the recipient and cc fields before replying.
# We decided not to support this feature, since we'd need a way for LLMs to tell apart between
# adding or removing recipients/cc, or replacing with an entirely new list of addresses,
# which would make the tool more complex to call.
@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.compose"],
    )
)
async def write_draft_reply_email(
    context: ToolContext,
    body: Annotated[str, "The body of the draft reply email"],
    reply_to_message_id: Annotated[str, "The Gmail message ID of the message to draft a reply to"],
    reply_to_whom: Annotated[
        GmailReplyToWhom,
        "Whether to reply to every recipient (including cc) or only to the original sender. "
        f"Defaults to '{GMAIL_DEFAULT_REPLY_TO}'.",
    ] = GMAIL_DEFAULT_REPLY_TO,
    bcc: Annotated[list[str] | None, "BCC recipients of the draft reply email"] = None,
) -> Annotated[dict, "A dictionary containing the created draft reply email details"]:
    """
    Compose a draft reply to an email message.
    """
    if isinstance(reply_to_whom, str):
        reply_to_whom = GmailReplyToWhom(reply_to_whom)

    service = _build_gmail_service(context)

    current_user = service.users().getProfile(userId="me").execute()

    try:
        replying_to_email = (
            service.users().messages().get(userId="me", id=reply_to_message_id).execute()
        )
    except HttpError as e:
        raise RetryableToolError(
            message="Could not retrieve the message to respond to.",
            developer_message=(
                "Could not retrieve the message to respond to. "
                f"Reason: '{e.reason}'. Error details: '{e.error_details}'"
            ),
        )

    replying_to_email = parse_multipart_email(replying_to_email)

    recipients = build_reply_recipients(
        replying_to_email, current_user["emailAddress"], reply_to_whom
    )

    draft_message = {
        "message": build_email_message(
            recipient=recipients,
            subject=f"Re: {replying_to_email['subject']}",
            body=body,
            cc=None
            if reply_to_whom == GmailReplyToWhom.ONLY_THE_SENDER
            else replying_to_email["cc"].split(","),
            bcc=bcc,
            replying_to=replying_to_email,
            action=GmailAction.DRAFT,
        ),
    }

    draft = service.users().drafts().create(userId="me", body=draft_message).execute()

    email = parse_draft_email(draft)
    email["url"] = get_draft_url(draft["id"])
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
    cc: Annotated[list[str] | None, "CC recipients of the draft email"] = None,
    bcc: Annotated[list[str] | None, "BCC recipients of the draft email"] = None,
) -> Annotated[dict, "A dictionary containing the updated draft email details"]:
    """
    Update an existing email draft using the Gmail API.
    """
    service = _build_gmail_service(context)

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
    service = _build_gmail_service(context)

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

    service = _build_gmail_service(context)

    # Trash the email
    trashed_email = service.users().messages().trash(userId="me", id=email_id).execute()

    email = parse_plain_text_email(trashed_email)
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
    service = _build_gmail_service(context)

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
            raise GmailToolError(
                message=f"Error reading draft email {draft_id}.", developer_message=str(e)
            )

    return {"emails": emails}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_emails_by_header(
    context: ToolContext,
    sender: Annotated[str | None, "The name or email address of the sender of the email"] = None,
    recipient: Annotated[str | None, "The name or email address of the recipient"] = None,
    subject: Annotated[str | None, "Words to find in the subject of the email"] = None,
    body: Annotated[str | None, "Words to find in the body of the email"] = None,
    date_range: Annotated[DateRange | None, "The date range of the email"] = None,
    label: Annotated[str | None, "The label name to filter by"] = None,
    max_results: Annotated[int, "The maximum number of emails to return"] = 25,
) -> Annotated[
    dict, "A dictionary containing a list of email details matching the search criteria"
]:
    """
    Search for emails by header using the Gmail API.

    At least one of the following parameters MUST be provided: sender, recipient,
    subject, date_range, label, or body.
    """
    service = _build_gmail_service(context)
    # Ensure at least one search parameter is provided
    if not any([sender, recipient, subject, body, label, date_range]):
        raise RetryableToolError(
            message=(
                "At least one of sender, recipient, subject, body, label, query, "
                "or date_range must be provided."
            ),
            developer_message=(
                "At least one of sender, recipient, subject, body, label, query, "
                "or date_range must be provided."
            ),
        )

    # Check if label is valid
    if label:
        label_ids = get_label_ids(service, [label])

        if not label_ids:
            labels = service.users().labels().list(userId="me").execute().get("labels", [])
            label_names = [label["name"] for label in labels]
            raise RetryableToolError(
                message=f"Invalid label: {label}",
                developer_message=f"Invalid label: {label}",
                additional_prompt_content=f"List of valid labels: {label_names}",
            )

    # Build a Gmail-style query string based on the filters
    query = build_gmail_query_string(sender, recipient, subject, body, date_range, label)

    # Fetch matching messages. This fetches message metadata from Gmail
    messages = fetch_messages(service, query, max_results)

    # If no messages found, return an empty list
    if not messages:
        return {"emails": []}

    # Process each message into a structured email object
    emails = get_email_details(service, messages)

    # Return the list of emails in a dictionary with key "emails"
    return {"emails": emails}


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
    service = _build_gmail_service(context)

    messages = service.users().messages().list(userId="me").execute().get("messages", [])

    if not messages:
        return {"emails": []}

    emails = []
    for msg in messages[:n_emails]:
        try:
            email_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
            email_details = parse_plain_text_email(email_data)
            if email_details:
                emails.append(email_details)
        except Exception as e:
            raise GmailToolError(
                message=f"Error reading email {msg['id']}.", developer_message=str(e)
            )
    return {"emails": emails}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def search_threads(
    context: ToolContext,
    page_token: Annotated[
        str | None, "Page token to retrieve a specific page of results in the list"
    ] = None,
    max_results: Annotated[int, "The maximum number of threads to return"] = 10,
    include_spam_trash: Annotated[bool, "Whether to include spam and trash in the results"] = False,
    label_ids: Annotated[list[str] | None, "The IDs of labels to filter by"] = None,
    sender: Annotated[str | None, "The name or email address of the sender of the email"] = None,
    recipient: Annotated[str | None, "The name or email address of the recipient"] = None,
    subject: Annotated[str | None, "Words to find in the subject of the email"] = None,
    body: Annotated[str | None, "Words to find in the body of the email"] = None,
    date_range: Annotated[DateRange | None, "The date range of the email"] = None,
) -> Annotated[dict, "A dictionary containing a list of thread details"]:
    """Search for threads in the user's mailbox"""
    service = _build_gmail_service(context)

    query = (
        build_gmail_query_string(sender, recipient, subject, body, date_range)
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
        str | None, "Page token to retrieve a specific page of results in the list"
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
) -> Annotated[dict, "A dictionary containing the thread details"]:
    """Get the specified thread by ID."""
    params = {
        "userId": "me",
        "id": thread_id,
        "format": "full",
    }
    params = remove_none_values(params)

    service = _build_gmail_service(context)

    thread = service.users().threads().get(**params).execute()
    thread["messages"] = [parse_plain_text_email(message) for message in thread.get("messages", [])]

    return dict(thread)


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
)
async def change_email_labels(
    context: ToolContext,
    email_id: Annotated[str, "The ID of the email to modify labels for"],
    labels_to_add: Annotated[list[str], "List of label names to add"],
    labels_to_remove: Annotated[list[str], "List of label names to remove"],
) -> Annotated[dict, "List of labels that were added, removed, and not found"]:
    """
    Add and remove labels from an email using the Gmail API.
    """
    service = _build_gmail_service(context)

    add_labels = get_label_ids(service, labels_to_add)
    remove_labels = get_label_ids(service, labels_to_remove)

    invalid_labels = (
        set(labels_to_add + labels_to_remove) - set(add_labels.keys()) - set(remove_labels.keys())
    )

    if invalid_labels:
        # prepare the list of valid labels
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_names = [label["name"] for label in labels]

        # raise a retryable error with the list of valid labels
        raise RetryableToolError(
            message=f"Invalid labels: {invalid_labels}",
            developer_message=f"Invalid labels: {invalid_labels}",
            additional_prompt_content=f"List of valid labels: {label_names}",
        )

    # Prepare the modification body with label IDs.
    body = {
        "addLabelIds": list(add_labels.values()),
        "removeLabelIds": list(remove_labels.values()),
    }

    try:  # Modify the email labels.
        service.users().messages().modify(userId="me", id=email_id, body=body).execute()

    except Exception as e:
        raise GmailToolError(
            message=f"Error modifying labels for email {email_id}", developer_message=str(e)
        )

    # Confirmation JSON with lists for added and removed labels.
    confirmation = {
        "addedLabels": list(add_labels.keys()),
        "removedLabels": list(remove_labels.keys()),
    }

    return {"confirmation": dict(confirmation)}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def list_labels(
    context: ToolContext,
) -> Annotated[dict, "A dictionary containing a list of label details"]:
    """List all the labels in the user's mailbox."""

    service = _build_gmail_service(context)

    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    return {"labels": labels}


@tool(
    requires_auth=Google(
        scopes=["https://www.googleapis.com/auth/gmail.labels"],
    )
)
async def create_label(
    context: ToolContext,
    label_name: Annotated[str, "The name of the label to create"],
) -> Annotated[dict, "The details of the created label"]:
    """Create a new label in the user's mailbox."""

    service = _build_gmail_service(context)
    label = service.users().labels().create(userId="me", body={"name": label_name}).execute()

    return {"label": label}

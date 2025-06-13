from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import ToolExecutionError

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_mail.message import Message, Recipient


@tool(requires_auth=Microsoft(scopes=["Mail.ReadWrite"]))
async def create_draft_email(
    context: ToolContext,
    subject: Annotated[str, "The subject of the draft email to create"],
    body: Annotated[str, "The body of the draft email to create"],
    to_recipients: Annotated[
        list[str], "The email addresses that will be the recipients of the draft email"
    ],
    cc_recipients: Annotated[
        list[str] | None,
        "The email addresses that will be the CC recipients of the draft email.",
    ] = None,
    bcc_recipients: Annotated[
        list[str] | None,
        "The email addresses that will be the BCC recipients of the draft email.",
    ] = None,
) -> Annotated[dict, "A dictionary containing the created email details"]:
    """Compose a new draft email in Outlook"""
    client = get_client(context.get_auth_token_or_empty())

    message = Message(
        subject=subject,
        body=body,
        to_recipients=[Recipient(email_address=email) for email in to_recipients],
        cc_recipients=[Recipient(email_address=email) for email in cc_recipients or []],
        bcc_recipients=[Recipient(email_address=email) for email in bcc_recipients or []],
        is_draft=True,
    ).to_sdk()

    response = await client.me.messages.post(message)
    draft_message = Message.from_sdk(response).to_dict()  # type: ignore[arg-type]

    return draft_message


@tool(requires_auth=Microsoft(scopes=["Mail.ReadWrite"]))
async def update_draft_email(
    context: ToolContext,
    message_id: Annotated[str, "The ID of the draft email to update"],
    subject: Annotated[
        str | None,
        "The new subject of the draft email. If provided, the existing subject will be overwritten",
    ] = None,
    body: Annotated[
        str | None,
        "The new body of the draft email. If provided, the existing body will be overwritten",
    ] = None,
    to_add: Annotated[list[str] | None, "Email addresses to add as 'To' recipients."] = None,
    to_remove: Annotated[
        list[str] | None,
        "Email addresses to remove from the current 'To' recipients.",
    ] = None,
    cc_add: Annotated[
        list[str] | None,
        "Email addresses to add as 'CC' recipients.",
    ] = None,
    cc_remove: Annotated[
        list[str] | None,
        "Email addresses to remove from the current 'CC' recipients.",
    ] = None,
    bcc_add: Annotated[
        list[str] | None,
        "Email addresses to add as 'BCC' recipients.",
    ] = None,
    bcc_remove: Annotated[
        list[str] | None,
        "Email addresses to remove from the current 'BCC' recipients.",
    ] = None,
) -> Annotated[dict, "A dictionary containing the updated email details"]:
    """Update an existing draft email in Outlook.

    This tool overwrites the subject and body of a draft email (if provided),
    and modifies its recipient lists by selectively adding or removing email addresses.

    This tool can update any un-sent email:
        - draft
        - reply-draft
        - reply-all draft
        - forward draft
    """
    client = get_client(context.get_auth_token_or_empty())

    # Get the draft email
    draft_email_sdk = await client.me.messages.by_message_id(message_id).get()

    if draft_email_sdk is None:
        raise ToolExecutionError(message=f"The draft email with ID {message_id} was not found.")

    # Update the draft email
    draft_email = Message.from_sdk(draft_email_sdk)
    draft_email.subject = subject if subject else draft_email.subject
    draft_email.body = body if body else draft_email.body or ""
    draft_email.update_recipient_lists(
        to_add=to_add,
        to_remove=to_remove,
        cc_add=cc_add,
        cc_remove=cc_remove,
        bcc_add=bcc_add,
        bcc_remove=bcc_remove,
    )
    updated_draft_email = await client.me.messages.by_message_id(message_id).patch(
        draft_email.to_sdk()
    )

    return Message.from_sdk(updated_draft_email).to_dict()  # type: ignore[arg-type]

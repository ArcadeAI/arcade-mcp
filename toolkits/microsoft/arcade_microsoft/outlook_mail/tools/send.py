from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_mail._utils import send_reply_email
from arcade_microsoft.outlook_mail.enums import ReplyType
from arcade_microsoft.outlook_mail.message import Message, Recipient


@tool(requires_auth=Microsoft(scopes=["Mail.Send"]))
async def create_and_send_email(
    context: ToolContext,
    subject: Annotated[str, "The subject of the email to create"],
    body: Annotated[str, "The body of the email to create"],
    to_recipients: Annotated[
        list[str], "The email addresses that will be the recipients of the email"
    ],
    cc_recipients: Annotated[
        list[str] | None, "The email addresses that will be the CC recipients of the email."
    ] = None,
    bcc_recipients: Annotated[
        list[str] | None,
        "The email addresses that will be the BCC recipients of the email.",
    ] = None,
) -> Annotated[dict, "A dictionary containing the created email details"]:
    """Create and immediately send a new email in Outlook to the specified recipients"""
    client = get_client(context.get_auth_token_or_empty())
    message = Message(
        subject=subject,
        body=body,
        to_recipients=[Recipient(email_address=email) for email in to_recipients],
        cc_recipients=[Recipient(email_address=email) for email in cc_recipients or []],
        bcc_recipients=[Recipient(email_address=email) for email in bcc_recipients or []],
    ).to_sdk()

    send_mail_request_body = SendMailPostRequestBody(
        message=message,
        save_to_sent_items=True,
    )

    await client.me.send_mail.post(send_mail_request_body)

    return {
        "success": True,
        "message": "Email sent successfully",
    }


@tool(requires_auth=Microsoft(scopes=["Mail.Send"]))
async def send_draft_email(
    context: ToolContext,
    message_id: Annotated[str, "The ID of the draft email to send"],
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """Send an existing draft email in Outlook

    This tool can send any un-sent email:
        - draft
        - reply-draft
        - reply-all draft
        - forward draft
    """
    client = get_client(context.get_auth_token_or_empty())

    await client.me.messages.by_message_id(message_id).send.post()

    return {
        "success": True,
        "message": "Email sent successfully",
    }


@tool(requires_auth=Microsoft(scopes=["Mail.Send"]))
async def reply_to_email(
    context: ToolContext,
    message_id: Annotated[str, "The ID of the email to reply to"],
    body: Annotated[str, "The body of the reply to the email"],
    reply_type: Annotated[
        ReplyType,
        f"Specify {ReplyType.REPLY} to reply only to the sender or "
        f"{ReplyType.REPLY_ALL} to reply to all recipients. "
        f"Defaults to {ReplyType.REPLY}.",
    ] = ReplyType.REPLY,
) -> Annotated[dict, "A dictionary containing the sent email details"]:
    """Reply to an existing email in Outlook.

    Use this tool to reply to the sender or all recipients of the email.
    Specify the reply_type to determine the scope of the reply.
    """
    return await send_reply_email(context, message_id, body, reply_type)

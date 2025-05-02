from arcade_microsoft.outlook_mail.tools import (
    create_and_send_email,
    create_draft_email,
    list_emails,
    list_emails_by_property,
    list_emails_in_folder,
    reply_to_email,
    send_draft_email,
    update_draft_email,
)

__all__ = [
    # Read
    "list_emails",
    "list_emails_by_property",
    "list_emails_in_folder",
    # Send
    "create_and_send_email",
    "send_draft_email",
    "reply_to_email",
    # Write
    "create_draft_email",
    "update_draft_email",
]

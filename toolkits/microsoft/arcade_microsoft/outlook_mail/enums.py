from enum import Enum


class WellKnownFolderNames(str, Enum):
    """Well-known folder names that are created for users by default.
    Instead of using the ID of these folders, you can use the well-known folder names.
    For a list of all well-known folder names, see: https://learn.microsoft.com/en-us/graph/api/resources/mailfolder?view=graph-rest-1.0
    """

    DELETED_ITEMS = "deleteditems"
    DRAFTS = "drafts"
    INBOX = "inbox"
    JUNK_EMAIL = "junkemail"
    SENT_ITEMS = "sentitems"
    STARRED = "starred"
    TODO = "tasks"


class ReplyType(str, Enum):
    """The type of reply to send to an email."""

    REPLY = "reply"
    REPLY_ALL = "reply_all"

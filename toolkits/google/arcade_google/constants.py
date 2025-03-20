import os

from arcade_google.models import GmailReplyToWhom

# The default reply in Gmail is to only the sender. Since Gmail also offers the possibility of
# changing the default to 'reply to all', we support both options through an env variable.
# https://support.google.com/mail/answer/6585?hl=en&sjid=15399867888091633568-SA#null
try:
    GMAIL_DEFAULT_REPLY_TO = GmailReplyToWhom(
        # Values accepted are defined in the arcade_google.tools.models.GmailReplyToWhom Enum
        os.getenv("ARCADE_GMAIL_DEFAULT_REPLY_TO", GmailReplyToWhom.ONLY_THE_SENDER.value).lower()
    )
except ValueError as e:
    raise ValueError(
        "Invalid value for ARCADE_GMAIL_DEFAULT_REPLY_TO: "
        f"'{os.getenv('ARCADE_GMAIL_DEFAULT_REPLY_TO')}'. Expected one of "
        f"{list(GmailReplyToWhom.__members__.keys())}"
    ) from e


DEFAULT_SEARCH_CONTACTS_LIMIT = 30

DEFAULT_SHEET_ROW_COUNT = 1000
DEFAULT_SHEET_COLUMN_COUNT = 26

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


class EmailFilterProperty(str, Enum):
    """The property to filter the emails by."""

    # Basic properties
    SUBJECT = "subject"
    CONVERSATION_ID = "conversationId"
    RECEIVED_DATE_TIME = "receivedDateTime"
    SENDER = "sender/emailAddress/address"


class FilterOperator(str, Enum):
    """The operator to use for the filter.

    For a full list of possible operators, see: https://learn.microsoft.com/en-us/graph/filter-query-parameter?tabs=http#operators-and-functions-supported-in-filter-expressions
    """

    # Equality operators
    EQUAL = "eq"  # example: $filter=conversationId eq 'hello'
    NOT_EQUAL = "ne"  # example: $filter=subject ne 'hello'

    # Relational operators
    GREATER_THAN = "gt"  # example: $filter=receivedDateTime gt 2024-01-01
    GREATER_THAN_OR_EQUAL_TO = "ge"  # example: $filter=receivedDateTime ge 2024-01-01
    LESS_THAN = "lt"  # example: $filter=receivedDateTime lt 2024-01-01
    LESS_THAN_OR_EQUAL_TO = "le"  # example: $filter=receivedDateTime le 2024-01-01

    # Functions
    STARTS_WITH = "startsWith"  # example: $filter=startsWith(subject, 'hello')
    ENDS_WITH = "endsWith"  # example: $filter=endsWith(subject, 'hello')
    CONTAINS = "contains"  # example: $filter=contains(subject, 'hello')

    def is_operator(self) -> bool:
        """Check if the operator is a comparison operator."""
        operators = [self.EQUAL, self.NOT_EQUAL]
        return self in operators

    def is_function(self) -> bool:
        """Check if the operator is a function."""
        functions = [self.STARTS_WITH, self.ENDS_WITH, self.CONTAINS]
        return self in functions

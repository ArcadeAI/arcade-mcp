import os
from enum import Enum

JIRA_BASE_URL = "https://api.atlassian.com/ex/jira"
JIRA_API_VERSION = "3"

try:
    JIRA_MAX_CONCURRENT_REQUESTS = max(1, int(os.getenv("JIRA_MAX_CONCURRENT_REQUESTS", 3)))
except Exception:
    JIRA_MAX_CONCURRENT_REQUESTS = 3

try:
    JIRA_API_REQUEST_TIMEOUT = int(os.getenv("JIRA_API_REQUEST_TIMEOUT", 30))
except Exception:
    JIRA_API_REQUEST_TIMEOUT = 30

try:
    JIRA_CACHE_MAX_ITEMS = max(1, int(os.getenv("JIRA_CACHE_MAX_ITEMS", 5000)))
except Exception:
    JIRA_CACHE_MAX_ITEMS = 5000


STOP_WORDS = [
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "if",
    "in",
    "into",
    "is",
    "it",
    "no",
    "not",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "will",
    "with",
    "+",
    "-",
    "&",
    "|",
    "!",
    "(",
    ")",
    "{",
    "}",
    "[",
    "]",
    "^",
    "~",
    "*",
    "?",
    "\\",
    ":",
]


class IssueCommentOrderBy(Enum):
    CREATED_DATE_ASCENDING = "created_date_ascending"
    CREATED_DATE_DESCENDING = "created_date_descending"

    def to_api_value(self) -> str:
        _map: dict[IssueCommentOrderBy, str] = {
            IssueCommentOrderBy.CREATED_DATE_ASCENDING: "+created",
            IssueCommentOrderBy.CREATED_DATE_DESCENDING: "-created",
        }
        return _map[self]


class PrioritySchemeOrderBy(Enum):
    NAME_ASCENDING = "name ascending"
    NAME_DESCENDING = "name descending"

    def to_api_value(self) -> str:
        _map: dict[PrioritySchemeOrderBy, str] = {
            PrioritySchemeOrderBy.NAME_ASCENDING: "+name",
            PrioritySchemeOrderBy.NAME_DESCENDING: "-name",
        }
        return _map[self]

"""Enums for the Zendesk toolkit."""

from enum import Enum


class ArticleSortBy(Enum):
    """Sort fields for article search results."""

    CREATED_AT = "created_at"
    RELEVANCE = "relevance"


class SortOrder(Enum):
    """Sort order direction."""

    ASC = "asc"
    DESC = "desc"


class TicketStatus(Enum):
    """Valid ticket statuses."""

    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    SOLVED = "solved"
    CLOSED = "closed"

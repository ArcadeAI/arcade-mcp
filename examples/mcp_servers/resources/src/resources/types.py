"""TypedDict definitions for structured tool outputs."""

from typing_extensions import TypedDict


class Author(TypedDict):
    """The team or person who authored an article."""

    name: str
    team: str


class ArticleDetail(TypedDict):
    """Full article detail with nested author information."""

    slug: str
    title: str
    category: str
    body: str
    author: Author


class SearchMatch(TypedDict):
    """A single search hit with relevance context."""

    slug: str
    title: str
    category: str
    matched_field: str


class SearchResult(TypedDict):
    """Search results with metadata"""

    query: str
    total_matches: int
    matches: list[SearchMatch]

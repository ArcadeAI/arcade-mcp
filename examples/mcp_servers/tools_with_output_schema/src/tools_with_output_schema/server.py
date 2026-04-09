#!/usr/bin/env python3
"""
tools_with_output_schema MCP server

Demonstrates how Arcade tools expose structured TypedDict return types as
fully-expanded JSON Schema output schemas, so MCP clients can validate and
display tool results without guessing the shape of the data.

Tools in this server progress from simple to complex:
  - calculate_statistics     — flat TypedDict (all scalar fields)
  - analyze_text             — TypedDict with a list field
  - get_calendar_info        — TypedDict with a nested TypedDict field
  - parse_url                — TypedDict with two levels of nesting
  - search_users             — TypedDict with total=False (all optional fields)
  - get_user_profile         — mixed required/optional fields via inheritance
  - lookup_record            — nullable fields (str | None)
  - get_team_info            — optional nested TypedDict (Optional[TypedDict])
"""

import sys
from collections import Counter
from datetime import datetime
from statistics import mean, median
from typing import Annotated, Optional
from urllib.parse import urlparse

from arcade_mcp_server import MCPApp
from typing_extensions import TypedDict

app = MCPApp(name="tools_with_output_schema", version="1.0.0", log_level="DEBUG")


# ---------------------------------------------------------------------------
# TypedDict definitions
# ---------------------------------------------------------------------------


class Statistics(TypedDict):
    """Descriptive statistics for a list of numbers."""

    count: int
    total: float
    mean: float
    median: float
    minimum: float
    maximum: float


class TextAnalysis(TypedDict):
    """Basic statistics about a piece of text."""

    word_count: int
    char_count: int
    sentence_count: int
    top_words: list[str]  # most-frequent words, descending


class CalendarDate(TypedDict):
    """A broken-down calendar date."""

    year: int
    month: int
    day: int
    weekday: str
    is_weekend: bool


class CalendarInfo(TypedDict):
    """Extended information about a date, including a nested CalendarDate."""

    date: CalendarDate
    day_of_year: int
    week_number: int
    days_until_year_end: int


class UrlComponents(TypedDict):
    """The individual components of a URL."""

    scheme: str
    host: str
    path: str
    port: int
    query_string: str


class ParsedUrl(TypedDict):
    """A fully parsed URL with a nested UrlComponents breakdown."""

    components: UrlComponents
    is_secure: bool
    domain: str


class SearchResult(TypedDict, total=False):
    """Search result where every field is optional (total=False).

    When a field is absent from the returned dict it must NOT appear in the
    serialized output.  Before the total=False fix, absent fields leaked as
    explicit ``null`` values, which violated the output schema.
    """

    username: str
    email: str
    display_name: str
    avatar_url: str


class _UserBase(TypedDict):
    """Required fields that every user profile must include."""

    user_id: int
    username: str


class UserProfile(_UserBase, total=False):
    """Mixed required / optional fields via TypedDict inheritance.

    ``user_id`` and ``username`` are required (from _UserBase);
    ``bio`` and ``website`` are optional (total=False on this class).
    The output schema's ``required`` array must list only the required keys.
    """

    bio: str
    website: str


class LookupResult(TypedDict):
    """Demonstrates nullable fields (``str | None``).

    A nullable field can hold either a real value or ``null``, and the
    output schema must advertise the type as ``["string", "null"]``.
    """

    key: str
    value: str | None
    error_message: str | None


class TeamMember(TypedDict, total=False):
    """A team member with all-optional fields."""

    name: str
    role: str


class TeamInfo(TypedDict):
    """Demonstrates an optional nested TypedDict (``Optional[TeamMember]``).

    The ``lead`` field is required-but-nullable: it must be present in the
    output, but its value may be ``null`` when no lead is assigned.
    """

    team_name: str
    lead: Optional[TeamMember]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@app.tool
def calculate_statistics(
    numbers: Annotated[list[float], "The list of numbers to analyze"],
) -> Annotated[Statistics, "Descriptive statistics for the provided numbers"]:
    """Compute descriptive statistics (count, total, mean, median, min, max) for a list of numbers."""
    if not numbers:
        raise ValueError("numbers must not be empty")
    return Statistics(
        count=len(numbers),
        total=sum(numbers),
        mean=mean(numbers),
        median=median(numbers),
        minimum=min(numbers),
        maximum=max(numbers),
    )


@app.tool
def analyze_text(
    text: Annotated[str, "The text to analyze"],
    top_n: Annotated[int, "How many top words to return"] = 5,
) -> Annotated[TextAnalysis, "Word, character, and sentence counts plus the most frequent words"]:
    """Analyze a piece of text and return word counts, character counts, and top words."""
    words = text.split()
    sentences = [s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
    word_freq = Counter(w.strip(".,!?;:\"'").lower() for w in words if w.strip(".,!?;:\"'"))
    top_words = [word for word, _ in word_freq.most_common(top_n)]
    return TextAnalysis(
        word_count=len(words),
        char_count=len(text),
        sentence_count=len(sentences),
        top_words=top_words,
    )


@app.tool
def get_calendar_info(
    date_str: Annotated[str, "Date in YYYY-MM-DD format"],
) -> Annotated[CalendarInfo, "Extended calendar information including a nested date breakdown"]:
    """Parse a date string and return detailed calendar information with a nested date object."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_of_year = dt.timetuple().tm_yday
    week_number = dt.isocalendar()[1]
    year_end = datetime(dt.year, 12, 31)
    days_until_year_end = (year_end - dt).days
    weekday_name = dt.strftime("%A")
    return CalendarInfo(
        date=CalendarDate(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            weekday=weekday_name,
            is_weekend=dt.weekday() >= 5,
        ),
        day_of_year=day_of_year,
        week_number=week_number,
        days_until_year_end=days_until_year_end,
    )


@app.tool
def parse_url(
    url: Annotated[str, "The URL to parse"],
) -> Annotated[ParsedUrl, "Fully parsed URL with a nested components breakdown"]:
    """Parse a URL and return its components as a structured object with nested fields."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # Strip leading 'www.' for the bare domain
    domain = host.removeprefix("www.")
    return ParsedUrl(
        components=UrlComponents(
            scheme=parsed.scheme,
            host=host,
            path=parsed.path or "/",
            port=port,
            query_string=parsed.query,
        ),
        is_secure=parsed.scheme == "https",
        domain=domain,
    )


@app.tool
def search_users(
    query: Annotated[str, "Search query to match against usernames"],
) -> Annotated[SearchResult, "Matching user (only populated fields are returned)"]:
    """Search for a user and return only the fields that matched.

    Demonstrates total=False: absent fields are omitted from the output
    rather than serialized as null.
    """
    # Simulate a search that only finds partial information
    result = SearchResult(username=query.lower())
    if "@" in query:
        result["email"] = query.lower()
    return result


@app.tool
def get_user_profile(
    username: Annotated[str, "The username to look up"],
) -> Annotated[UserProfile, "User profile with required and optional fields"]:
    """Look up a user profile.

    Demonstrates mixed required/optional fields: user_id and username are
    always present; bio and website may be absent.
    """
    profile = UserProfile(user_id=42, username=username)
    if username == "admin":
        profile["bio"] = "Site administrator"
        profile["website"] = "https://example.com"
    # For any other user, bio and website are intentionally absent
    return profile


@app.tool
def lookup_record(
    key: Annotated[str, "The key to look up"],
) -> Annotated[LookupResult, "The lookup result with nullable value and error fields"]:
    """Look up a record by key.

    Demonstrates nullable fields: value and error_message are typed as
    str | None, so the output schema advertises ["string", "null"].
    """
    records = {"color": "blue", "size": "large"}
    value = records.get(key)
    return LookupResult(
        key=key,
        value=value,
        error_message=None if value else f"No record found for key: {key}",
    )


@app.tool
def get_team_info(
    team_name: Annotated[str, "The team name to look up"],
) -> Annotated[TeamInfo, "Team info with an optional nested TypedDict for the lead"]:
    """Get team information including the team lead.

    Demonstrates Optional[TypedDict]: the lead field is required-but-nullable.
    When a lead exists, absent total=False fields inside the nested TeamMember
    are properly omitted (not serialized as null).
    """
    if team_name == "backend":
        return TeamInfo(
            team_name=team_name,
            lead=TeamMember(name="Alice"),  # role intentionally absent
        )
    # Team with no lead assigned
    return TeamInfo(team_name=team_name, lead=None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)

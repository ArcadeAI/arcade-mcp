#!/usr/bin/env python3
"""
tools_with_output_schema MCP server

Demonstrates how Arcade tools expose structured TypedDict return types as
fully-expanded JSON Schema output schemas, so MCP clients can validate and
display tool results without guessing the shape of the data.

Tools in this server progress from simple to complex:
  - calculate_statistics  — flat TypedDict (all scalar fields)
  - analyze_text          — TypedDict with a list field
  - get_calendar_info     — TypedDict with a nested TypedDict field
  - parse_url             — TypedDict with two levels of nesting
"""

import sys
from collections import Counter
from datetime import datetime
from statistics import mean, median
from typing import Annotated
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)

"""Type definitions for Google News API responses and parameters."""

from typing_extensions import TypedDict

# For now, we'll use str type alias to maintain compatibility
# In the future, these could be converted to proper Literal types
CountryCode = str
LanguageCode = str


class SearchNewsParams(TypedDict):
    """Input parameters for searching news articles."""

    keywords: str
    """Search query terms to find relevant news articles \
    (e.g., 'Apple launches new iPhone')."""

    country_code: CountryCode | None
    """Optional 2-letter country code to filter news by region \
    (e.g., 'us' for United States, 'uk' for United Kingdom)."""

    language_code: LanguageCode | None
    """Optional 2-letter language code to filter news by language \
    (e.g., 'en' for English, 'es' for Spanish)."""

    limit: int | None
    """Optional maximum number of news articles to return. \
    If not specified, returns all results from the API."""


class SourceInfo(TypedDict, total=False):
    """Information about the news source/publication."""

    name: str
    """Name of the publication (e.g., 'CNN', 'BBC News', 'The New York Times')."""

    icon: str
    """URL to the source's favicon or logo image."""

    authors: list[str]
    """List of author names for the article, if available."""


class NewsResult(TypedDict, total=False):
    """Individual news article from the Google News API response."""

    position: int
    """Ranking position of this result in the search results."""

    title: str
    """Headline or title of the news article."""

    link: str
    """Full URL to the original news article."""

    source: SourceInfo
    """Information about the publication source."""

    date: str
    """Publication date and time (e.g., '2 hours ago', 'Dec 15, 2023')."""

    snippet: str
    """Brief excerpt or summary from the article content."""

    thumbnail: str
    """URL to a high-resolution thumbnail image for the article."""

    thumbnail_small: str
    """URL to a low-resolution thumbnail image for the article."""

    story_token: str
    """Token for accessing full coverage of this news story across multiple sources."""

    stories: list["NewsResult"]
    """Related news stories from other sources covering the same topic."""

    highlight: dict
    """Additional highlighted information about the story."""


class SearchMetadata(TypedDict, total=False):
    """Metadata about the search request and processing."""

    id: str
    """Unique identifier for this search request within SerpApi."""

    status: str
    """Current processing status ('Processing', 'Success', or 'Error')."""

    json_endpoint: str
    """URL to retrieve the JSON results for this search."""

    created_at: str
    """Timestamp when the search request was created."""

    processed_at: str
    """Timestamp when the search request was processed."""

    google_news_url: str
    """Original Google News URL that would return these results."""

    total_time_taken: float
    """Total time in seconds taken to process this search."""


class SearchParameters(TypedDict, total=False):
    """Parameters used for the search request."""

    engine: str
    """Search engine used (always 'google_news' for this API)."""

    q: str
    """Search query string."""

    gl: str
    """Country code used for geographic filtering."""

    hl: str
    """Language code used for language filtering."""

    topic_token: str
    """Token for accessing specific news topics (e.g., 'World', 'Business', 'Technology')."""

    publication_token: str
    """Token for accessing news from specific publishers."""


class MenuLink(TypedDict):
    """Navigation link for news categories or topics."""

    title: str
    """Display text for the menu item (e.g., 'Technology', 'Sports', 'Business')."""

    topic_token: str
    """Token to access this specific topic or category."""

    serpapi_link: str
    """SerpApi URL to search within this topic."""


class TopStoriesLink(TypedDict):
    """Link to top stories section."""

    topic_token: str
    """Token to access top stories."""

    serpapi_link: str
    """SerpApi URL to retrieve top stories."""


class GoogleNewsResponse(TypedDict, total=False):
    """Complete response from the Google News API."""

    search_metadata: SearchMetadata
    """Metadata about the search request and processing."""

    search_parameters: SearchParameters
    """Parameters that were used for this search."""

    news_results: list[NewsResult]
    """List of news articles matching the search criteria."""

    menu_links: list[MenuLink]
    """Navigation links to different news categories and topics."""

    top_stories_link: TopStoriesLink
    """Link to access top stories."""

    title: str
    """Title of the page or topic being displayed."""


class SimplifiedNewsResult(TypedDict):
    """Simplified news article format for tool output."""

    title: str
    """Headline of the news article."""

    link: str
    """URL to the full article."""

    source: str | None
    """Name of the publication source."""

    date: str | None
    """When the article was published."""

    snippet: str | None
    """Brief excerpt from the article."""


class SearchNewsOutput(TypedDict):
    """Output format for the search_news_stories tool."""

    news_results: list[SimplifiedNewsResult]
    """List of news articles in simplified format."""

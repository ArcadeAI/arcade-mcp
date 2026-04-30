import importlib.metadata
from enum import Enum
from typing import Annotated

import httpx
from arcade_mcp_server import Context, tool

PERPLEXITY_SEARCH_URL = "https://api.perplexity.ai/search"
INTEGRATION_SLUG = "arcade"
PACKAGE_NAME = "arcade_perplexity"
DEFAULT_MAX_RESULTS = 5
MAX_RESULTS_LIMIT = 20


class SearchRecencyFilter(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


def _integration_header() -> str:
    try:
        version = importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return f"{INTEGRATION_SLUG}/{version}"


@tool(requires_secrets=["PERPLEXITY_API_KEY"])
async def search(
    context: Context,
    query: Annotated[str, "The search query to send to Perplexity."],
    max_results: Annotated[
        int,
        "Maximum number of results to return (1-20). Defaults to 5.",
    ] = DEFAULT_MAX_RESULTS,
    search_recency_filter: Annotated[
        SearchRecencyFilter | None,
        "Restrict results to content published within the given recency window.",
    ] = None,
) -> Annotated[
    list[dict[str, str]],
    "List of search results, each with 'title', 'url', and 'snippet'.",
]:
    """Search the web using the Perplexity Search API.

    Returns a list of ranked results with the page title, URL, and a short
    snippet of the most relevant content from each page.
    """
    api_key = context.get_secret("PERPLEXITY_API_KEY")

    bounded_max_results = max(1, min(int(max_results), MAX_RESULTS_LIMIT))

    payload: dict[str, object] = {
        "query": query,
        "max_results": bounded_max_results,
    }
    if search_recency_filter is not None:
        recency = (
            search_recency_filter.value
            if isinstance(search_recency_filter, SearchRecencyFilter)
            else str(search_recency_filter)
        )
        payload["search_recency_filter"] = recency

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Pplx-Integration": _integration_header(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            PERPLEXITY_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", []) if isinstance(data, dict) else []
    return [
        {
            "title": str(item.get("title", "")),
            "url": str(item.get("url", "")),
            "snippet": str(item.get("snippet", "")),
        }
        for item in results
    ]

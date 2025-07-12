"""SearXNG Search Tool - Base search functionality for SearXNG integration."""

import json
from logging import getLogger
from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import ToolExecutionError

from arcade_search_engine.enums import (
    ImageColor,
    ImageLayout,
    ImageSize,
    ImageType,
    ResponseFormat,
    SafeSearchLevel,
    TimeRange,
    VideoDuration,
)

logger = getLogger(__name__)

# List of public SearXNG instances (as fallbacks)
PUBLIC_INSTANCES = [
    "https://search.bus-hit.me",
    "https://searx.be",
    "https://searx.projectlounge.pw",
    "https://search.sapti.me",
    "https://searx.tiekoetter.com",
]


@tool
async def search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute"],
    engines: Annotated[
        list[str] | None,
        "List of specific engines to use (e.g., ['google', 'duckduckgo', 'brave'])",
    ] = None,
    categories: Annotated[
        list[str] | None,
        "List of categories to search (e.g., ['general', 'images', 'videos'])",
    ] = None,
    language: Annotated[str, "Language code for search results"] = "en",
    time_range: Annotated[TimeRange | None, "Time range filter for results"] = None,
    safe_search: Annotated[
        SafeSearchLevel, "Safe search level. Defaults to off"
    ] = SafeSearchLevel.OFF,
    page: Annotated[int, "Page number for pagination"] = 1,
    format: Annotated[ResponseFormat, "Response format"] = ResponseFormat.JSON,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing search results from SearXNG"]:
    """
    Execute a search query using SearXNG with support for multiple engines and categories.
    Use when you need to search across multiple search engines or apply specific filters.
    """

    # Build query parameters
    params = {
        "q": query,
        "format": format.value,
        "language": language,
        "safesearch": safe_search.to_api_value(),
        "pageno": page,
    }

    # Add engines if specified
    if engines:
        params["engines"] = ",".join(engines)

    # Add categories if specified
    if categories:
        params["categories"] = ",".join(categories)

    # Add time range if specified
    if time_range:
        params["time_range"] = time_range.value if isinstance(time_range, TimeRange) else time_range

    # Construct the search URL
    search_endpoint = f"{searxng_url}/search"

    # Headers to avoid 403 errors
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json" if format == ResponseFormat.JSON else "text/html",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    last_error = None
    instances_to_try = [searxng_url] if searxng_url not in PUBLIC_INSTANCES else PUBLIC_INSTANCES

    for instance_url in instances_to_try:
        try:
            search_endpoint = f"{instance_url}/search"
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(search_endpoint, params=params, headers=headers)

                # If we get a 403, try the next instance
                if response.status_code == 403:
                    logger.error(f"Access forbidden for {instance_url}")
                    last_error = f"Access forbidden for {instance_url}"
                    continue

                response.raise_for_status()

                if format == ResponseFormat.JSON:
                    return json.dumps(response.json())
                else:
                    return json.dumps({"html": response.text})

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Search failed at {instance_url} with status {e.response.status_code}: {e.response.text}"
            )
            last_error = f"Search failed at {instance_url} with status {e.response.status_code}: {e.response.text}"
            if e.response.status_code != 403:
                # For non-403 errors, we might want to try the next instance
                continue
        except Exception as e:
            logger.error(f"Search failed at {instance_url}: {str(e)}")
            last_error = f"Search failed at {instance_url}: {str(e)}"
            continue

    # If all instances failed, raise the last error
    logger.error(f"All SearXNG instances failed: {last_error}")
    raise ToolExecutionError(last_error or "All SearXNG instances failed")


@tool
async def search_with_bang(
    context: ToolContext,
    query: Annotated[str, "The search query to execute"],
    bang: Annotated[
        str,
        "Bang syntax for specific engine (e.g., '!g' for Google, '!ddg' for DuckDuckGo)",
    ],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[int, "Safe search level (0=off, 1=moderate, 2=strict)"] = 0,
    page: Annotated[int, "Page number for pagination"] = 1,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing search results from the specified engine"]:
    """
    Execute a search using SearXNG bang syntax to target a specific search engine.
    Use when you want to search using a specific engine via its bang shortcut.
    """

    # Prepend bang to query
    full_query = f"{bang} {query}"

    return await search(
        context=context,
        query=full_query,
        language=language,
        safe_search=safe_search,
        page=page,
        format=ResponseFormat.JSON,
        searxng_url=searxng_url,
    )


@tool
async def get_engines(
    context: ToolContext,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing available engines and their configuration"]:
    """
    Retrieve the list of available search engines and their configuration from a SearXNG instance.
    Use when you need to discover what engines are available or check engine settings.
    """

    engines_endpoint = f"{searxng_url}/config"

    # Headers to avoid 403 errors
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(engines_endpoint, headers=headers)
            response.raise_for_status()
            return json.dumps(response.json())

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to get engines with status {e.response.status_code}: {e.response.text}"
        )
        raise ToolExecutionError(
            f"Failed to get engines with status {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Failed to get engines: {str(e)}")
        raise ToolExecutionError(f"Failed to get engines: {str(e)}")


@tool
async def search_images(
    context: ToolContext,
    query: Annotated[str, "The search query for images"],
    size: Annotated[ImageSize | None, "Image size filter"] = None,
    type: Annotated[ImageType | None, "Image type filter"] = None,
    layout: Annotated[ImageLayout | None, "Image layout filter"] = None,
    color: Annotated[ImageColor | None, "Color filter"] = None,
    engines: Annotated[list[str] | None, "Specific image search engines to use"] = None,
    safe_search: Annotated[int, "Safe search level (0=off, 1=moderate, 2=strict)"] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing image search results"]:
    """
    Search for images using SearXNG with advanced filtering options.
    Use when you need to find images with specific characteristics like size, type, or color.
    """

    # Build the query with filters
    filter_parts = []
    if size:
        filter_parts.append(f"size:{size.value}")
    if type:
        filter_parts.append(f"type:{type.value}")
    if layout:
        filter_parts.append(f"layout:{layout.value}")
    if color:
        filter_parts.append(f"color:{color.value}")

    if filter_parts:
        query = f"{query} {' '.join(filter_parts)}"

    return await search(
        context=context,
        query=query,
        categories=["images"],
        engines=engines,
        safe_search=safe_search,
        page=page,
        searxng_url=searxng_url,
    )


@tool
async def search_videos(
    context: ToolContext,
    query: Annotated[str, "The search query for videos"],
    duration: Annotated[VideoDuration | None, "Video duration filter"] = None,
    engines: Annotated[list[str] | None, "Specific video search engines to use"] = None,
    safe_search: Annotated[int, "Safe search level (0=off, 1=moderate, 2=strict)"] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing video search results"]:
    """
    Search for videos using SearXNG with duration filtering.
    Use when you need to find videos with specific duration preferences.
    """

    if duration:
        query = f"{query} duration:{duration.value}"

    return await search(
        context=context,
        query=query,
        categories=["videos"],
        engines=engines,
        safe_search=safe_search,
        page=page,
        searxng_url=searxng_url,
    )


@tool
async def search_news(
    context: ToolContext,
    query: Annotated[str, "The search query for news articles"],
    time_range: Annotated[TimeRange, "Time range for news articles"] = TimeRange.WEEK,
    engines: Annotated[list[str] | None, "Specific news engines to use"] = None,
    language: Annotated[str, "Language code for news articles"] = "en",
    page: Annotated[int, "Page number for pagination"] = 1,
    searxng_url: Annotated[str, "Base URL of SearXNG instance"] = "https://search.bus-hit.me",
) -> Annotated[str, "JSON string containing news search results"]:
    """
    Search for news articles using SearXNG with time-based filtering.
    Use when you need to find recent news articles or news from a specific time period.
    """

    return await search(
        context=context,
        query=query,
        categories=["news"],
        time_range=time_range,
        engines=engines,
        language=language,
        page=page,
        searxng_url=searxng_url,
    )

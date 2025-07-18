import logging
import re
from typing import Any

import httpx
from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_MAX_BODY_LENGTH = 500  # Default max length for article body content


async def fetch_paginated_results(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """
    Fetch paginated results using offset and limit pattern.

    This function internally manages pagination to fulfill the requested offset and limit,
    fetching multiple pages as needed.

    Args:
        client: The HTTP client to use
        url: The API endpoint URL
        headers: Request headers including authorization
        params: Base query parameters (without pagination params)
        offset: Number of items to skip
        limit: Number of items to return

    Returns:
        Dict containing:
        - results: List of fetched items
        - count: Number of items returned
        - next_offset: Present only if more results are available
    """
    # Calculate pagination parameters
    # Most Zendesk APIs use 1-based page numbering
    items_per_page = params.get("per_page", 100)  # Use per_page from params or default to 100
    start_page = (offset // items_per_page) + 1
    start_index = offset % items_per_page

    # Collect results across multiple pages if needed
    all_results = []
    current_page = start_page
    items_collected = 0
    has_more = False
    last_page_had_more_items = False

    while items_collected < limit:
        # Set the current page
        page_params = params.copy()
        page_params["page"] = current_page

        response = await client.get(url, headers=headers, params=page_params, timeout=30.0)
        response.raise_for_status()
        page_data = response.json()

        # Extract results from current page (handle both "results" and "tickets" keys)
        page_results = page_data.get("results", page_data.get("tickets", []))

        # If this is the first page, skip to the start index
        if current_page == start_page:
            page_results = page_results[start_index:]

        # Take only what we need to reach the limit
        items_needed = limit - items_collected
        results_to_add = page_results[:items_needed]
        all_results.extend(results_to_add)
        items_collected += len(results_to_add)

        # Check if we left items on this page
        if len(page_results) > items_needed:
            last_page_had_more_items = True

        # Check if there are more pages
        has_more = page_data.get("next_page") is not None

        # Stop if we've collected enough or no more pages
        if items_collected >= limit or not has_more:
            break

        current_page += 1

    # Build the response
    result = {
        "results": all_results,
        "count": len(all_results),
    }

    # Add next_offset if there might be more results
    # This happens when:
    # 1. We got exactly the limit requested AND (there are more pages OR we left items on the page)
    # 2. We didn't get the full limit but there are more pages available
    if (len(all_results) == limit and (has_more or last_page_had_more_items)) or (
        len(all_results) < limit and has_more
    ):
        result["next_offset"] = offset + len(all_results)

    return result


def clean_html_text(text: str | None) -> str:
    """Remove HTML tags and clean up text."""
    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")
    clean_text: str = soup.get_text(separator=" ")

    clean_text = re.sub(r"\n+", "\n", clean_text)

    clean_text = re.sub(r"\s+", " ", clean_text)

    clean_text = "\n".join(line.strip() for line in clean_text.split("\n"))

    return clean_text.strip()


def truncate_text(
    text: str | None, max_length: int, suffix: str = " ... [truncated]"
) -> str | None:
    """Truncate text to a maximum length with a suffix."""
    if not text or len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix

    return text[:truncate_at] + suffix


def process_article_body(body: str | None, max_length: int | None = None) -> str | None:
    """Process article body by cleaning HTML and optionally truncating."""
    if not body:
        return None

    cleaned_text: str = clean_html_text(body)

    if max_length and len(cleaned_text) > max_length:
        result = truncate_text(cleaned_text, max_length)
        return result

    return cleaned_text


def process_search_results(
    results: list[dict[str, Any]],
    include_body: bool = False,
    max_body_length: int | None = DEFAULT_MAX_BODY_LENGTH,
) -> list[dict[str, Any]]:
    """Process search results to clean up data and restructure with content and metadata."""
    processed_results = []

    for result in results:
        body_content = result.get("body", "")
        cleaned_content = None

        if include_body and body_content:
            cleaned_content = process_article_body(body_content, max_body_length)

        processed_result: dict[str, Any] = {"content": cleaned_content, "metadata": {}}

        for key, value in result.items():
            if key != "body":
                processed_result["metadata"][key] = value

        processed_results.append(processed_result)

    return processed_results


def validate_date_format(date_string: str) -> bool:
    """Validate that a date string matches YYYY-MM-DD format and is a valid date."""
    from datetime import datetime

    try:
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
        # Ensure the input matches the expected format exactly
        return parsed_date.strftime("%Y-%m-%d") == date_string
    except ValueError:
        return False


def get_zendesk_subdomain(context: ToolContext) -> str:
    """
    Get the Zendesk subdomain from secrets with proper error handling.

    Args:
        context: The tool context containing secrets

    Returns:
        The Zendesk subdomain

    Raises:
        ToolExecutionError: If the subdomain secret is not configured
    """
    try:
        subdomain = context.get_secret("ZENDESK_SUBDOMAIN")
    except ValueError:
        raise ToolExecutionError(
            message="Zendesk subdomain is not set.",
            developer_message=(
                "Zendesk subdomain is not set. Make sure to set the "
                "'ZENDESK_SUBDOMAIN' secret in the Arcade Dashboard."
            ),
        ) from None
    else:
        return subdomain

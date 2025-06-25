import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_TOTAL_RESULTS = 1000  # Maximum total results to prevent excessive API calls
DEFAULT_MAX_BODY_LENGTH = 500  # Default max length for article body content


async def fetch_all_pages(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    max_pages: int | None = None,
) -> dict[str, Any]:
    """
    Internal helper to fetch all pages of results.

    Args:
        client: The HTTP client to use
        url: The API endpoint URL
        headers: Request headers including authorization
        params: Query parameters for the search
        max_pages: Maximum number of pages to fetch (None for all)

    Returns:
        Combined results from all pages with pagination metadata
    """
    all_results = []
    current_page = params.get("page", 1)
    pages_fetched = 0

    while True:
        params["page"] = current_page

        http_response = await client.get(url, headers=headers, params=params, timeout=30.0)
        http_response.raise_for_status()
        page_data = http_response.json()

        if "results" in page_data:
            all_results.extend(page_data["results"])

        pages_fetched += 1

        if max_pages and pages_fetched >= max_pages:
            logger.info(f"Reached max_pages limit ({max_pages})")
            break

        if len(all_results) >= MAX_TOTAL_RESULTS:
            logger.warning(f"Reached maximum total results limit ({MAX_TOTAL_RESULTS})")
            break

        if page_data.get("next_page") is None:
            break

        current_page += 1

    # Create simplified response with just results
    response: dict[str, Any] = {"results": all_results}

    # Add warnings if we hit limits
    if len(all_results) >= MAX_TOTAL_RESULTS:
        response["warnings"] = [
            {
                "type": "ResultLimitReached",
                "message": f"Result limit of {MAX_TOTAL_RESULTS} reached. "
                "Use more specific filters to narrow your search.",
                "suggestion": "Try adding filters like category, section, or date ranges "
                "to get more targeted results.",
            }
        ]

    return response


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
    """Validate that a date string matches YYYY-MM-DD format."""
    import re

    pattern = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(pattern, date_string))

import logging
from typing import Annotated, Any, Dict, Optional

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from ..utils import (
    fetch_all_pages,
    process_search_results,
    validate_date_format,
)

logger = logging.getLogger(__name__)


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def search_articles(
    context: ToolContext,
    query: Annotated[
        Optional[str],
        "Search text to match against articles. Can use quoted phrases for exact matches (e.g., 'exact phrase') or multiple terms (e.g., 'carrot potato')",
    ] = None,
    label_names: Annotated[
        Optional[str],
        "Comma-separated list of label names (case-insensitive). Article must have at least one matching label. Available on Professional/Enterprise plans only",
    ] = None,
    category: Annotated[
        Optional[int],
        "Filter by category ID. Can specify multiple by comma-separating values (e.g., '123,456')",
    ] = None,
    section: Annotated[
        Optional[int],
        "Filter by section ID. Can specify multiple by comma-separating values (e.g., '789,101')",
    ] = None,
    created_after: Annotated[
        Optional[str],
        "Filter articles created after this date (format: YYYY-MM-DD, e.g., '2024-01-15')",
    ] = None,
    created_before: Annotated[
        Optional[str],
        "Filter articles created before this date (format: YYYY-MM-DD, e.g., '2024-01-15')",
    ] = None,
    created_at: Annotated[
        Optional[str],
        "Filter articles created on this exact date (format: YYYY-MM-DD, e.g., '2024-01-15')",
    ] = None,
    sort_by: Annotated[
        Optional[str],
        "Sort results by 'created_at'. Defaults to relevance when omitted",
    ] = None,
    sort_order: Annotated[
        Optional[str],
        "Sort order: 'asc' (ascending) or 'desc' (descending). Defaults to 'desc'",
    ] = None,
    per_page: Annotated[int, "Number of results per page (maximum 100)"] = 10,
    all_pages: Annotated[
        bool,
        "Automatically fetch all available pages of results when True. Takes precedence over max_pages",
    ] = False,
    max_pages: Annotated[
        Optional[int],
        "Maximum number of pages to fetch (ignored if all_pages=True). If neither all_pages nor max_pages is specified, only the first page is returned",
    ] = None,
    include_body: Annotated[
        bool,
        "Include article body content in results. Bodies will be cleaned of HTML and truncated",
    ] = True,
) -> Annotated[Dict[str, Any], "Article search results with pagination metadata"]:
    """
    Search for Help Center articles in your Zendesk knowledge base.

    This tool searches specifically for published knowledge base articles that provide
    solutions and guidance to users. At least one search parameter (query, category,
    section, or label_names) must be provided.

    IMPORTANT: ALL FILTERS CAN BE COMBINED IN A SINGLE CALL
    You can combine multiple filters (query, category, section, labels, dates) in one
    search request. Do NOT make separate tool calls - combine all relevant filters together.

    Search Tips:
    - Use quoted phrases for exact matches: "password reset"
    - Combine with filters for precise results: query="API" + category=123

    Examples:
    - Basic search: query="installation guide"
    - Category search: category=123, query="troubleshooting"
    - Label search: label_names="windows,setup", query="installation"
    - Date range: query="API", created_after="2024-01-01", created_before="2024-12-31"
    - Combined filters: query="troubleshooting", category=100, section=200, label_names="windows,setup"
    - All results: query="API documentation", all_pages=True
    - Limited pages: query="troubleshooting", max_pages=3, per_page=50
    """

    # Validate date parameters
    date_params = {
        "created_after": created_after,
        "created_before": created_before,
        "created_at": created_at,
    }

    for param_name, param_value in date_params.items():
        if param_value and not validate_date_format(param_value):
            return {
                "error": "InvalidDateFormat",
                "message": f"Invalid date format for {param_name}: '{param_value}'. Please use YYYY-MM-DD format.",
                "example": "2024-01-15",
            }

    # Validate sort parameters
    if sort_by and sort_by not in ["created_at"]:
        return {
            "error": "InvalidSortParameter",
            "message": f"Invalid sort_by value: '{sort_by}'. Must be 'created_at'.",
        }

    if sort_order and sort_order not in ["asc", "desc"]:
        return {
            "error": "InvalidSortOrder",
            "message": f"Invalid sort_order value: '{sort_order}'. Must be 'asc' or 'desc'.",
        }

    # Validate pagination parameters
    if max_pages is not None and max_pages < 1:
        return {
            "error": "InvalidPaginationParameter",
            "message": "max_pages must be at least 1 if specified.",
        }

    # Validate that at least one search parameter is provided
    if not any([query, category, section, label_names]):
        return {
            "error": "MissingSearchParameter",
            "message": "At least one of query, category, section, or label_names must be provided.",
        }

    auth_token = context.get_auth_token_or_empty()

    if not auth_token:
        return {
            "error": "AuthenticationError",
            "message": "No authentication token found. Please authenticate with Zendesk first.",
        }

    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")
    if not subdomain:
        return {
            "error": "ConfigurationError",
            "message": "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN.",
        }

    url = f"https://{subdomain}.zendesk.com/api/v2/help_center/articles/search"

    params: Dict[str, Any] = {
        "per_page": min(per_page, 100),
        "page": 1,
    }

    if query:
        params["query"] = query

    if label_names:
        params["label_names"] = label_names

    if category:
        params["category"] = category

    if section:
        params["section"] = section

    if created_after:
        params["created_after"] = created_after

    if created_before:
        params["created_before"] = created_before

    if created_at:
        params["created_at"] = created_at

    if sort_by:
        params["sort_by"] = sort_by

    if sort_order:
        params["sort_order"] = sort_order

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Determine how many pages to fetch
            if all_pages:
                pages_to_fetch = None  # Fetch all pages
            elif max_pages is not None:
                pages_to_fetch = max_pages
            else:
                pages_to_fetch = 1  # Single page (default behavior)

            data = await fetch_all_pages(client, url, headers, params, max_pages=pages_to_fetch)
            if "results" in data:
                data["results"] = process_search_results(data["results"], include_body=include_body)
            logger.info(f"Article search results: {data}")
            return data

        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error during article search: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "message": f"Failed to search articles: {e.response.text}",
                "url": url,
                "params": params,
            }
        except httpx.TimeoutException:
            logger.exception("Timeout during article search")
            return {
                "error": "TimeoutError",
                "message": "Request timed out while searching articles. Try reducing per_page or using more specific filters.",
                "url": url,
                "params": params,
            }
        except Exception as e:
            logger.exception(f"Unexpected error during article search: {e!s}")
            return {
                "error": "SearchError",
                "message": f"Failed to search articles: {e!s}",
                "url": url,
                "params": params,
            }

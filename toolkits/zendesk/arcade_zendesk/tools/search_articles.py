import logging
from enum import Enum
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_zendesk.utils import (
    fetch_all_pages,
    get_zendesk_subdomain,
    process_search_results,
    validate_date_format,
)

logger = logging.getLogger(__name__)


class ArticleSortBy(Enum):
    """Sort fields for article search results."""

    CREATED_AT = "created_at"
    RELEVANCE = "relevance"


class SortOrder(Enum):
    """Sort order direction."""

    ASC = "asc"
    DESC = "desc"


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def search_articles(
    context: ToolContext,
    query: Annotated[
        str | None,
        "Search text to match against articles. Supports quoted expressions for exact matching",
    ] = None,
    label_names: Annotated[
        list[str] | None,
        "List of label names to filter by (case-insensitive). Article must have at least "
        "one matching label. Available on Professional/Enterprise plans only",
    ] = None,
    created_after: Annotated[
        str | None,
        "Filter articles created after this date (format: YYYY-MM-DD)",
    ] = None,
    created_before: Annotated[
        str | None,
        "Filter articles created before this date (format: YYYY-MM-DD)",
    ] = None,
    created_at: Annotated[
        str | None,
        "Filter articles created on this exact date (format: YYYY-MM-DD)",
    ] = None,
    sort_by: Annotated[
        ArticleSortBy | None,
        "Field to sort articles by. Defaults to relevance according to the search query",
    ] = None,
    sort_order: Annotated[
        SortOrder | None,
        "Sort order direction. Defaults to descending",
    ] = None,
    per_page: Annotated[int, "Number of results per page (maximum 100)"] = 10,
    all_pages: Annotated[
        bool,
        "Automatically fetch all available pages of results when True. "
        "Takes precedence over max_pages",
    ] = False,
    max_pages: Annotated[
        int | None,
        "Maximum number of pages to fetch (ignored if all_pages=True). If neither all_pages "
        "nor max_pages is specified, only the first page is returned",
    ] = None,
    include_body: Annotated[
        bool,
        "Include article body content in results. Bodies will be cleaned of HTML and truncated",
    ] = True,
    max_article_length: Annotated[
        int | None,
        "Maximum length for article body content in characters. "
        "Set to None for no limit. Defaults to 500",
    ] = 500,
) -> Annotated[dict[str, Any], "Article search results with pagination metadata"]:
    """
    Search for Help Center articles in your Zendesk knowledge base.

    This tool searches specifically for published knowledge base articles that provide
    solutions and guidance to users. At least one search parameter (query or label_names)
    must be provided.

    IMPORTANT: ALL FILTERS CAN BE COMBINED IN A SINGLE CALL
    You can combine multiple filters (query, labels, dates) in one search request.
    Do NOT make separate tool calls - combine all relevant filters together.
    """

    # Validate date parameters
    date_params = {
        "created_after": created_after,
        "created_before": created_before,
        "created_at": created_at,
    }

    for param_name, param_value in date_params.items():
        if param_value and not validate_date_format(param_value):
            raise RetryableToolError(
                message=(
                    f"Invalid date format for {param_name}: '{param_value}'. "
                    "Please use YYYY-MM-DD format."
                ),
                developer_message=(
                    f"Date validation failed for parameter '{param_name}' "
                    f"with value '{param_value}'"
                ),
                retry_after_ms=500,
                additional_prompt_content="Use format YYYY-MM-DD.",
            )

    # Validate pagination parameters
    if max_pages is not None and max_pages < 1:
        raise RetryableToolError(
            message="max_pages must be at least 1 if specified.",
            developer_message=f"Invalid max_pages value: {max_pages}",
            retry_after_ms=100,
            additional_prompt_content="Provide a positive integer for max_pages",
        )

    # Validate that at least one search parameter is provided
    if not any([query, label_names]):
        raise RetryableToolError(
            message="At least one search parameter must be provided.",
            developer_message="No search parameters were provided",
            retry_after_ms=100,
            additional_prompt_content=(
                "Provide at least one of: query text or a list of label names"
            ),
        )

    auth_token = context.get_auth_token_or_empty()
    subdomain = get_zendesk_subdomain(context)

    url = f"https://{subdomain}.zendesk.com/api/v2/help_center/articles/search"

    params: dict[str, Any] = {
        "per_page": min(per_page, 100),
        "page": 1,
    }

    if query:
        params["query"] = query

    if label_names:
        params["label_names"] = ",".join(label_names)

    if created_after:
        params["created_after"] = created_after

    if created_before:
        params["created_before"] = created_before

    if created_at:
        params["created_at"] = created_at

    if sort_by:
        params["sort_by"] = sort_by.value

    if sort_order:
        params["sort_order"] = sort_order.value

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
                data["results"] = process_search_results(
                    data["results"], include_body=include_body, max_body_length=max_article_length
                )
            logger.info(f"Article search results: {data}")

        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error during article search: {e.response.status_code}")
            raise ToolExecutionError(
                message=f"Failed to search articles: HTTP {e.response.status_code}",
                developer_message=(
                    f"HTTP {e.response.status_code} error: {e.response.text}. "
                    f"URL: {url}, params: {params}"
                ),
            ) from e
        except httpx.TimeoutException as e:
            logger.exception("Timeout during article search")
            raise RetryableToolError(
                message="Request timed out while searching articles.",
                developer_message=f"Timeout occurred. URL: {url}, params: {params}",
                retry_after_ms=5000,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during article search")
            raise ToolExecutionError(
                message=f"Failed to search articles: {e!s}",
                developer_message=(
                    f"Unexpected error: {type(e).__name__}: {e!s}. " f"URL: {url}, params: {params}"
                ),
            ) from e
        else:
            return data

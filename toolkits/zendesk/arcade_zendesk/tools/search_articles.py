import logging
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_zendesk.enums import ArticleSortBy, SortOrder
from arcade_zendesk.utils import (
    fetch_paginated_results,
    get_zendesk_subdomain,
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
    limit: Annotated[
        int,
        "Number of articles to return. Defaults to 30",
    ] = 30,
    offset: Annotated[
        int,
        "Number of articles to skip before returning results. Defaults to 0",
    ] = 0,
    include_body: Annotated[
        bool,
        "Include article body content in results. Bodies will be cleaned of HTML and truncated",
    ] = True,
    max_article_length: Annotated[
        int | None,
        "Maximum length for article body content in characters. "
        "Set to None for no limit. Defaults to 500",
    ] = 500,
) -> Annotated[
    dict[str, Any],
    "Article search results with pagination metadata. Includes 'next_offset' when more "
    "results are available. Simply use this value as the 'offset' parameter in your next "
    "call to fetch the next batch",
]:
    """
    Search for Help Center articles in your Zendesk knowledge base.

    This tool searches specifically for published knowledge base articles that provide
    solutions and guidance to users. At least one search parameter (query or label_names)
    must be provided.

    PAGINATION:
    - The response includes 'next_offset' when more results are available
    - To fetch the next batch, simply pass the 'next_offset' value as the 'offset' parameter
    - If 'next_offset' is not present, you've reached the end of available results
    - The tool automatically handles fetching from the correct page based on your offset

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

    # Validate limit and offset parameters
    if limit < 1:
        raise RetryableToolError(
            message="limit must be at least 1.",
            developer_message=f"Invalid limit value: {limit}",
            retry_after_ms=100,
            additional_prompt_content="Provide a positive limit value",
        )

    if offset < 0:
        raise RetryableToolError(
            message="offset cannot be negative.",
            developer_message=f"Invalid offset value: {offset}",
            retry_after_ms=100,
            additional_prompt_content="Provide a non-negative offset value",
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

    # Base parameters for the search
    base_params: dict[str, Any] = {
        "per_page": 100,  # Max allowed per page
    }

    if query:
        base_params["query"] = query

    if label_names:
        base_params["label_names"] = ",".join(label_names)

    if created_after:
        base_params["created_after"] = created_after

    if created_before:
        base_params["created_before"] = created_before

    if created_at:
        base_params["created_at"] = created_at

    if sort_by:
        base_params["sort_by"] = sort_by.value

    if sort_order:
        base_params["sort_order"] = sort_order.value

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            data = await fetch_paginated_results(
                client=client,
                url=url,
                headers=headers,
                params=base_params,
                offset=offset,
                limit=limit,
            )

            if "results" in data:
                data["results"] = process_search_results(
                    data["results"], include_body=include_body, max_body_length=max_article_length
                )

            logger.info(f"Article search returned {data.get('count', 0)} results")

        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error during article search: {e.response.status_code}")
            raise ToolExecutionError(
                message=f"Failed to search articles: HTTP {e.response.status_code}",
                developer_message=(
                    f"HTTP {e.response.status_code} error: {e.response.text}. "
                    f"URL: {url}, base_params: {base_params}"
                ),
            ) from e
        except httpx.TimeoutException as e:
            logger.exception("Timeout during article search")
            raise RetryableToolError(
                message="Request timed out while searching articles.",
                developer_message=f"Timeout occurred. URL: {url}, base_params: {base_params}",
                retry_after_ms=5000,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during article search")
            raise ToolExecutionError(
                message=f"Failed to search articles: {e!s}",
                developer_message=(
                    f"Unexpected error: {type(e).__name__}: {e!s}. "
                    f"URL: {url}, base_params: {base_params}"
                ),
            ) from e
        else:
            return data

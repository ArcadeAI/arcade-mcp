from typing import Annotated, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion

from arcade_notion.enums import ObjectType, SortDirection
from arcade_notion.utils import (
    _simplify_search_result,
    get_headers,
    get_url,
    remove_none_values,
)


@tool(requires_auth=Notion())
async def search_by_title(
    context: ToolContext,
    query: Annotated[
        Optional[str],
        "A substring to search for within page and database titles. "
        "If not provided (default), all pages and/or databases are returned.",
    ] = None,
    select: Annotated[
        Optional[ObjectType],
        "Limit the results to either only pages or only databases. Defaults to both.",
    ] = None,
    order_by: Annotated[
        SortDirection,
        "The direction to sort search results by last edited time. Defaults to 'descending'.",
    ] = SortDirection.DESCENDING,
    limit: Annotated[
        int,
        "The maximum number of results to return. Defaults to 100. Set to -1 for no limit.",
    ] = 100,
) -> Annotated[
    dict,
    "A dictionary containing the pages and/or databases that have "
    "titles that are the best match for the query.",
]:
    """Search all pages, databases, or both by title.
    Searches pages and/or databases that have titles similar to the query.
    """
    results = []
    current_cursor = None

    url = get_url("search_by_title")
    headers = get_headers(context)
    payload = {
        "query": query,
        "page_size": 100 if limit == -1 else min(100, limit),
        "filter": {"property": "object", "value": select.value} if select else None,
        "sort": {"direction": order_by, "timestamp": "last_edited_time"},
    }
    payload = remove_none_values(payload)

    async with httpx.AsyncClient() as client:
        while True:
            if current_cursor:
                payload["start_cursor"] = current_cursor
            elif "start_cursor" in payload:
                del payload["start_cursor"]

            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            page_results = [_simplify_search_result(item) for item in data.get("results", [])]
            results.extend(page_results)

            # If a limit is set and we've reached or exceeded it, truncate the results.
            if limit is not None and len(results) >= limit:
                results = results[:limit]
                break

            if not data.get("has_more", False):
                break

            current_cursor = data.get("next_cursor")

    return {"results": results}


@tool(requires_auth=Notion())
async def get_workspace_structure(
    context: ToolContext,
) -> Annotated[
    dict,
    "A dictionary containing the workspace structure.",
]:
    """Get the workspace structure."""
    results = []
    current_cursor = None

    url = get_url("search_by_title")
    headers = get_headers(context)
    payload = {
        "page_size": 100,
    }

    async with httpx.AsyncClient() as client:
        while True:
            if current_cursor:
                payload["start_cursor"] = current_cursor
            elif "start_cursor" in payload:
                del payload["start_cursor"]

            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            results.extend(data.get("results", []))

            if not data.get("has_more", False):
                break

            current_cursor = data.get("next_cursor")

    return {"results": results}

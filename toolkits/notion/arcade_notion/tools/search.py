from typing import Annotated, Any, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Notion
from arcade.sdk.errors import ToolExecutionError

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
    """Search all pages, databases, or both within the user's workspace by title.
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
async def get_object_metadata(
    context: ToolContext,
    object_title: Annotated[Optional[str], "Title of the page or database whose metadata to get"],
    object_id: Annotated[Optional[str], "ID of the page or database whose metadata to get"],
    object_type: Annotated[
        Optional[ObjectType],
        "The type of object to match title to. Only used if `object_title` is provided. "
        "Defaults to both",
    ] = None,
) -> Annotated[dict[str, Any], "The metadata of the object"]:
    """Get the metadata of a Notion object (page or database) from its title or ID.

    One of `object_title` or `object_id` MUST be provided, but both cannot be provided.
    The title is case-insensitive and outer whitespace is ignored.
    """
    if not (bool(object_title) ^ bool(object_id)):
        raise ToolExecutionError(
            message="Either object_title or object_id must be provided, but not both.",
        )

    async def get_metadata_by_title():
        candidates_response = await search_by_title(
            context,
            object_title,
            select=object_type,
            order_by=SortDirection.DESCENDING,
            limit=3,
        )

        if object_type:
            candidates = [
                page
                for page in candidates_response["results"]
                if page["object"] == object_type.value
            ]
        else:
            candidates = candidates_response["results"]

        normalized_title = object_title.lower().strip()
        error_msg = (
            f"The {object_type.value if object_type else 'object'} with "
            f"the title '{object_title}' could not be found. "
            "Either it does not exist, or it has not been shared with the integration."
        )

        if not candidates:
            raise ToolExecutionError(message=error_msg)

        for object_ in candidates:
            if object_["title"].lower().strip() == normalized_title:
                # object_ is either a page object: https://developers.notion.com/reference/page
                # or a database object: https://developers.notion.com/reference/database
                return object_

        raise ToolExecutionError(
            message=error_msg,
            developer_message=f"The closest matches are: {candidates}",
        )

    async def get_metadata_by_id():
        url = get_url("retrieve_a_page", page_id=object_id)
        headers = get_headers(context)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ToolExecutionError(
                    message="The page or database could not be found.",
                    developer_message=f"The response was: {response.json()}",
                )

            return dict(response.json())

    return await get_metadata_by_title() if object_title else await get_metadata_by_id()


@tool(requires_auth=Notion())
async def get_workspace_structure(
    context: ToolContext,
) -> Annotated[
    dict,
    "A dictionary containing the workspace structure.",
]:
    """Get the Notion workspace file structure."""
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

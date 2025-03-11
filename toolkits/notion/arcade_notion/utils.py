from typing import Any, Optional

import httpx
from arcade.sdk import ToolContext

from arcade_notion.constants import ENDPOINTS, NOTION_API_URL


def get_url(endpoint: str, **kwargs: Any) -> str:
    """
    Constructs the full URL for a specified notion endpoint.

    Args:
        endpoint (str): The endpoint key from ENDPOINTS.
        **kwargs: Additional parameters to format the URL.

    Returns:
        str: The complete URL for the specified endpoint.
    """
    return f"{NOTION_API_URL}{ENDPOINTS[endpoint].format(**kwargs)}"


def get_headers(context: ToolContext) -> dict[str, str]:
    """
    Retrieves the headers for a given context.

    Args:
        context (ToolContext): The context containing authorization and other information.

    Returns:
        dict[str, str]: A dictionary containing the headers for the Notion API request.
    """
    return {
        "Authorization": context.get_auth_token_or_empty(),
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def remove_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Removes all keys with None values from a dictionary.

    Args:
        payload (dict[str, Any]): The dictionary to remove None values from.

    Returns:
        dict[str, Any]: A dictionary with all None values removed.
    """
    return {k: v for k, v in payload.items() if v is not None}


def extract_title(item: dict) -> str:
    """
    Extracts a human-readable title from a page, database, or a block if possible.
    """
    properties: dict = item.get("properties", {})
    if item["object"] == "database" and "title" in item:
        return "".join([t["plain_text"] for t in item.get("title", [])])

    if item["object"] == "page" and "title" in properties:
        return "".join([t["plain_text"] for t in properties["title"].get("title", [])])

    # For blocks (like child_page blocks).
    if item.get("object") == "block":
        block_type = item.get("type")
        if block_type == "child_page":
            title: str = item.get("child_page", {}).get("title", "New Page")
            return title
        # For text-based blocks, try extracting rich_text.
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
            rich_text = item.get(block_type, {}).get("rich_text", [])
            return "".join([t.get("plain_text", "") for t in rich_text]) or block_type

    return ""


def _simplify_search_result(item: dict) -> dict:
    """
    Simplifies a search result from the Notion API.

    Args:
        item (dict): The search result to simplify.

    Returns:
        dict: A simplified search result.
    """
    title = extract_title(item)
    # properties = item.get("properties", {})
    # title = ""
    # if item["object"] == "database" and "title" in item:
    #     title = "".join([t["plain_text"] for t in item.get("title", [])])
    # elif item["object"] == "page" and "title" in properties:
    #     title = "".join([t["plain_text"] for t in properties["title"].get("title", [])])

    return {
        "id": item.get("id"),
        "object": item.get("object"),
        "parent": item.get("parent"),
        "created_time": item.get("created_time"),
        "last_edited_time": item.get("last_edited_time"),
        "title": title,
        "url": item.get("url"),
        "public_url": item.get("public_url"),
    }


async def get_next_page(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    params: Optional[dict] = None,
    cursor: Optional[str] = None,
) -> tuple[dict, bool, str]:
    """
    Retrieves the next page of results from a Notion API endpoint.

    Args:
        client (httpx.AsyncClient): The HTTP client to use for the request.
        url (str): The URL of the endpoint to request.
        headers (dict): The headers to use for the request.
        params (Optional[dict]): The parameters to use for the request.
        cursor (Optional[str]): The cursor to use for the request.

    Returns:
        tuple[dict, bool, str]: A tuple containing the results, a boolean indicating if there is a
        next page, and the next cursor.
    """
    params = params or {}
    if cursor:
        params["start_cursor"] = cursor
    elif "start_cursor" in params:
        del params["start_cursor"]

    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data, data.get("has_more", False), data.get("next_cursor")


async def get_page_url(context: ToolContext, page_id: str) -> str:
    """
    Retrieves the URL of a page from the Notion API.

    Args:
        context (ToolContext): The context containing authorization and other information.
        page_id (str): The ID of the page to get the URL of.

    Returns:
        str: The URL of the page or an empty string if the page's metadata cannot be retrieved.
    """
    url = get_url("retrieve_a_page", page_id=page_id)
    headers = get_headers(context)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return ""
        data = response.json()
        return data.get("url", "")  # type: ignore[no-any-return]

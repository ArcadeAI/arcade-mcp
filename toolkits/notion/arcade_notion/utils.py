from typing import Any

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

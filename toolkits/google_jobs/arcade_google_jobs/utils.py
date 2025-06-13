import re
from typing import Any, cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from serpapi import Client as SerpClient


def prepare_params(engine: str, **kwargs: Any) -> dict[str, Any]:
    """
    Prepares a parameters dictionary for the SerpAPI call.

    Parameters:
        engine: The engine name (e.g., "google", "google_finance").
        kwargs: Any additional parameters to include.

    Returns:
        A dictionary containing the base parameters plus any extras,
        excluding any parameters whose value is None.
    """
    params = {"engine": engine}
    params.update({k: v for k, v in kwargs.items() if v is not None})
    return params


def call_serpapi(context: ToolContext, params: dict) -> dict:
    """
    Execute a search query using the SerpAPI client and return the results as a dictionary.

    Args:
        context: The tool context containing required secrets.
        params: A dictionary of parameters for the SerpAPI search.

    Returns:
        The search results as a dictionary.
    """
    api_key = context.get_secret("SERP_API_KEY")
    client = SerpClient(api_key=api_key)
    try:
        search = client.search(params)
        return cast(dict[str, Any], search.as_dict())
    except Exception as e:
        # SerpAPI error messages sometimes contain the API key, so we need to sanitize it
        sanitized_e = re.sub(r"(api_key=)[^ &]+", r"\1***", str(e))
        raise ToolExecutionError(
            message="Failed to fetch search results",
            developer_message=sanitized_e,
        )

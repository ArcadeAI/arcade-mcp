import json
from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_search.utils import call_serpapi, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def search_google(
    context: ToolContext,
    query: Annotated[str, "Search query"],
    n_results: Annotated[int, "Number of results to retrieve"] = 5,
) -> str:
    """Search Google using SerpAPI and return organic search results."""

    params = prepare_params("google", q=query)
    results = call_serpapi(context, params)
    organic_results = results.get("organic_results", [])

    return json.dumps(organic_results[:n_results])

import json
from typing import Annotated

import serpapi
from arcade.sdk import ToolContext, tool


@tool(requires_secrets=["SERP_API_KEY"])
async def search_google(
    context: ToolContext,
    query: Annotated[str, "Search query"],
    n_results: Annotated[int, "Number of results to retrieve"] = 5,
) -> str:
    """Search Google using SerpAPI and return organic search results."""

    api_key = context.get_secret("SERP_API_KEY")

    client = serpapi.Client(api_key=api_key)
    params = {"engine": "google", "q": query}

    search = client.search(params)
    results = search.as_dict()
    organic_results = results.get("organic_results", [])

    return json.dumps(organic_results[:n_results])

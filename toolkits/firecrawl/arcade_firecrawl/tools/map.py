from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from firecrawl import FirecrawlApp


@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def map_website(
    context: ToolContext,
    url: Annotated[str, "The base URL to start crawling from"],
    search: Annotated[str | None, "Search query to use for mapping"] = None,
    ignore_sitemap: Annotated[bool, "Ignore the website sitemap when crawling"] = True,
    include_subdomains: Annotated[bool, "Include subdomains of the website"] = False,
    limit: Annotated[int, "Maximum number of links to return"] = 5000,
) -> Annotated[dict[str, Any], "Website map data"]:
    """
    Map a website from a single URL to a map of the entire website.
    """

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    params: dict[str, Any] = {
        "ignoreSitemap": ignore_sitemap,
        "includeSubdomains": include_subdomains,
        "limit": limit,
    }
    if search:
        params["search"] = search

    map_result = app.map_url(url, params=params)

    return dict(map_result)

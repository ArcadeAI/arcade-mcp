from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from firecrawl import FirecrawlApp

from arcade_firecrawl.enums import Formats


# TODO: Support actions. This would enable clicking, scrolling, screenshotting, etc.
# TODO: Support extract.
# TODO: Support headers param?
@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def scrape_url(
    context: ToolContext,
    url: Annotated[str, "URL to scrape"],
    formats: Annotated[
        list[Formats] | None, "Formats to retrieve. Defaults to ['markdown']."
    ] = None,
    only_main_content: Annotated[
        bool | None,
        "Only return the main content of the page excluding headers, navs, footers, etc.",
    ] = True,
    include_tags: Annotated[list[str] | None, "List of tags to include in the output"] = None,
    exclude_tags: Annotated[list[str] | None, "List of tags to exclude from the output"] = None,
    wait_for: Annotated[
        int | None,
        "Specify a delay in milliseconds before fetching the content, allowing the page "
        "sufficient time to load.",
    ] = 10,
    timeout: Annotated[int | None, "Timeout in milliseconds for the request"] = 30000,
) -> Annotated[dict[str, Any], "Scraped data in specified formats"]:
    """Scrape a URL using Firecrawl and return the data in specified formats."""

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    formats = formats or [Formats.MARKDOWN]

    app = FirecrawlApp(api_key=api_key)
    params = {
        "formats": formats,
        "onlyMainContent": only_main_content,
        "includeTags": include_tags or [],
        "excludeTags": exclude_tags or [],
        "waitFor": wait_for,
        "timeout": timeout,
    }
    response = app.scrape_url(url, params=params)

    return dict(response)

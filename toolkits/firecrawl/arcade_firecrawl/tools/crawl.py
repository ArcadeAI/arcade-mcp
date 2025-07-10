from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from firecrawl import FirecrawlApp


# TODO: Support scrapeOptions.
@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def crawl_website(
    context: ToolContext,
    url: Annotated[str, "URL to crawl"],
    exclude_paths: Annotated[list[str] | None, "URL patterns to exclude from the crawl"] = None,
    include_paths: Annotated[list[str] | None, "URL patterns to include in the crawl"] = None,
    max_depth: Annotated[int, "Maximum depth to crawl relative to the entered URL"] = 2,
    ignore_sitemap: Annotated[bool, "Ignore the website sitemap when crawling"] = True,
    limit: Annotated[int, "Limit the number of pages to crawl"] = 10,
    allow_backward_links: Annotated[
        bool,
        "Enable navigation to previously linked pages and enable crawling "
        "sublinks that are not children of the 'url' input parameter.",
    ] = False,
    allow_external_links: Annotated[bool, "Allow following links to external websites"] = False,
    webhook: Annotated[
        str | None,
        "The URL to send a POST request to when the crawl is started, updated and completed.",
    ] = None,
    async_crawl: Annotated[bool, "Run the crawl asynchronously"] = True,
) -> Annotated[dict[str, Any], "Crawl status and data"]:
    """
    Crawl a website using Firecrawl. If the crawl is asynchronous, then returns the crawl ID.
    If the crawl is synchronous, then returns the crawl data.
    """

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    params = {
        "limit": limit,
        "excludePaths": exclude_paths or [],
        "includePaths": include_paths or [],
        "maxDepth": max_depth,
        "ignoreSitemap": ignore_sitemap,
        "allowBackwardLinks": allow_backward_links,
        "allowExternalLinks": allow_external_links,
    }
    if webhook:
        params["webhook"] = webhook

    if async_crawl:
        response = app.async_crawl_url(url, params=params)
        response.pop("url", None)  # Remove 'url' as it's an API endpoint

        if response["success"]:
            response["status"] = await get_crawl_status(context, response["id"])
            response["llm_instructions"] = (
                "You have the ability to get crawl status, cancel a crawl, "
                "and get a crawl's data. Inform the user that you have these capabilities. "
                "Inform the user that they should let you know if they want you to perform any "
                "of these actions."
            )

    else:
        response = app.crawl_url(url, params=params)

    return dict(response)


@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def get_crawl_status(
    context: ToolContext,
    crawl_id: Annotated[str, "The ID of the crawl job"],
) -> Annotated[dict[str, Any], "Crawl status information"]:
    """
    Get the status of a Firecrawl 'crawl' that is either in progress or recently completed.
    """

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    crawl_status = app.check_crawl_status(crawl_id)

    crawl_status.pop("data", None)  # Remove 'data' if it exists
    crawl_status.pop("next", None)  # Remove 'next' as it's an API endpoint

    return dict(crawl_status)


# TODO: Support responses greater than 10 MB. If the response is greater than 10 MB,
#       then the Firecrawl API response will have a next_url field.
@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def get_crawl_data(
    context: ToolContext,
    crawl_id: Annotated[str, "The ID of the crawl job"],
) -> Annotated[dict[str, Any], "Crawl data information"]:
    """
    Get the data of a Firecrawl 'crawl' that is either in progress or recently completed.
    """

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    crawl_data = app.check_crawl_status(crawl_id)

    return dict(crawl_data)


@tool(requires_secrets=["FIRECRAWL_API_KEY"])
async def cancel_crawl(
    context: ToolContext,
    crawl_id: Annotated[str, "The ID of the asynchronous crawl job to cancel"],
) -> Annotated[dict[str, Any], "Cancellation status information"]:
    """
    Cancel an asynchronous crawl job that is in progress using the Firecrawl API.
    """

    api_key = context.get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    cancellation_status = app.cancel_crawl(crawl_id)

    return dict(cancellation_status)

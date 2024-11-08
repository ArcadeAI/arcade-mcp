from typing import Annotated, Any, Optional

from firecrawl import FirecrawlApp

from arcade.sdk import tool
from arcade_web.tools.models import Formats
from arcade_web.tools.utils import get_secret


# TODO: Support actions. This would enable clicking, scrolling, screenshotting, etc.
# TODO: Support extract.
# TODO: Support headers param?
@tool
async def scrape_url(
    url: Annotated[str, "URL to scrape"],
    formats: Annotated[
        Optional[list[Formats]], "Formats to retrieve. Defaults to ['markdown']."
    ] = None,
    only_main_content: Annotated[
        Optional[bool],
        "Only return the main content of the page excluding headers, navs, footers, etc.",
    ] = True,
    include_tags: Annotated[list[str] | None, "List of tags to include in the output"] = None,
    exclude_tags: Annotated[list[str] | None, "List of tags to exclude from the output"] = None,
    wait_for: Annotated[
        Optional[int],
        "Specify a delay in milliseconds before fetching the content, allowing the page sufficient time to load.",
    ] = 10,
    timeout: Annotated[Optional[int], "Timeout in milliseconds for the request"] = 30000,
) -> Annotated[dict[str, Any], "Scraped data in specified formats"]:
    """Scrape a URL using Firecrawl and return the data in specified formats."""

    api_key = get_secret("FIRECRAWL_API_KEY")

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

    return response


# TODO: Support scrapeOptions.
@tool
async def crawl_website(
    url: Annotated[str, "URL to crawl"],
    exclude_paths: Annotated[list[str] | None, "URL patterns to exclude from the crawl"] = None,
    include_paths: Annotated[list[str] | None, "URL patterns to include in the crawl"] = None,
    max_depth: Annotated[int, "Maximum depth to crawl relative to the entered URL"] = 2,
    ignore_sitemap: Annotated[bool, "Ignore the website sitemap when crawling"] = True,
    limit: Annotated[int, "Limit the number of pages to crawl"] = 10,
    allow_backward_links: Annotated[
        bool,
        "Enable navigation to previously linked pages and enable crawling sublinks that are not children of the 'url' input parameter.",
    ] = False,
    allow_external_links: Annotated[bool, "Allow following links to external websites"] = False,
    webhook: Annotated[
        Optional[str],
        "The URL to send a POST request to when the crawl is started, updated and completed.",
    ] = None,
    async_crawl: Annotated[bool, "Run the crawl asynchronously"] = True,
) -> Annotated[dict[str, Any], "Crawl status and data"]:
    """
    Crawl a website using Firecrawl. If the crawl is asynchronous, then returns the crawl ID.
    If the crawl is synchronous, then returns the crawl data.
    """

    api_key = get_secret("FIRECRAWL_API_KEY")

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
        if (
            "url" in response
        ):  # Url isn't clickable, so removing it since only the ID is needed to check status
            del response["url"]
    else:
        response = app.crawl_url(url, params=params)

    return response


@tool
async def get_crawl_status(
    crawl_id: Annotated[str, "The ID of the crawl job"],
) -> Annotated[dict[str, Any], "Crawl status information"]:
    """
    Get the status of a Firecrawl 'crawl' that is either in progress or recently completed.
    """

    api_key = get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    crawl_status = app.check_crawl_status(crawl_id)

    if "data" in crawl_status:
        del crawl_status["data"]

    return crawl_status


# TODO: Support responses greater than 10 MB. If the response is greater than 10 MB, then the Firecrawl API response will have a next_url field.
@tool
async def get_crawl_data(
    crawl_id: Annotated[str, "The ID of the crawl job"],
) -> Annotated[dict[str, Any], "Crawl data information"]:
    """
    Get the data of a Firecrawl 'crawl' that is either in progress or recently completed.
    """

    api_key = get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    crawl_data = app.check_crawl_status(crawl_id)

    return crawl_data


@tool
async def cancel_crawl(
    crawl_id: Annotated[str, "The ID of the asynchronous crawl job to cancel"],
) -> Annotated[dict[str, Any], "Cancellation status information"]:
    """
    Cancel an asynchronous crawl job that is in progress using the Firecrawl API.
    """

    api_key = get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    cancellation_status = app.cancel_crawl(crawl_id)

    return cancellation_status


@tool
async def map_website(
    url: Annotated[str, "The base URL to start crawling from"],
    search: Annotated[Optional[str], "Search query to use for mapping"] = None,
    ignore_sitemap: Annotated[bool, "Ignore the website sitemap when crawling"] = True,
    include_subdomains: Annotated[bool, "Include subdomains of the website"] = False,
    limit: Annotated[int, "Maximum number of links to return"] = 5000,
) -> Annotated[dict[str, Any], "Website map data"]:
    """
    Map a website from a single URL to a map of the entire website.
    """

    api_key = get_secret("FIRECRAWL_API_KEY")

    app = FirecrawlApp(api_key=api_key)
    params = {
        "ignoreSitemap": ignore_sitemap,
        "includeSubdomains": include_subdomains,
        "limit": limit,
    }
    if search:
        params["search"] = search

    map_result = app.map_url(url, params=params)

    return map_result

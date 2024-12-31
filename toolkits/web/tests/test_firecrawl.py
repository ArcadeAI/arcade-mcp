from unittest.mock import AsyncMock, patch

import pytest
from arcade.sdk.errors import ToolExecutionError

from arcade_web.tools.firecrawl import (
    cancel_crawl,
    crawl_website,
    get_crawl_data,
    get_crawl_status,
    map_website,
    scrape_url,
)


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_firecrawl_app():
    with patch("arcade_web.tools.firecrawl.FirecrawlApp") as app:
        yield app.return_value


@pytest.mark.asyncio
async def test_scrape_url_success(mock_firecrawl_app):
    mock_firecrawl_app.scrape_url.return_value = {"data": "scraped content"}

    result = await scrape_url("http://example.com")
    assert result == {"data": "scraped content"}


@pytest.mark.asyncio
async def test_crawl_website_success(mock_firecrawl_app):
    mock_firecrawl_app.async_crawl_url.return_value = {"crawl_id": "12345"}

    result = await crawl_website("http://example.com")
    assert result == {"crawl_id": "12345"}


@pytest.mark.asyncio
async def test_get_crawl_status_success(mock_firecrawl_app):
    mock_firecrawl_app.check_crawl_status.return_value = {"status": "completed"}

    result = await get_crawl_status("12345")
    assert result == {"status": "completed"}


@pytest.mark.asyncio
async def test_get_crawl_data_success(mock_firecrawl_app):
    mock_firecrawl_app.check_crawl_status.return_value = {"data": "crawl data"}

    result = await get_crawl_data("12345")
    assert result == {"data": "crawl data"}


@pytest.mark.asyncio
async def test_cancel_crawl_success(mock_firecrawl_app):
    mock_firecrawl_app.cancel_crawl.return_value = {"status": "cancelled"}

    result = await cancel_crawl("12345")
    assert result == {"status": "cancelled"}


@pytest.mark.asyncio
async def test_map_website_success(mock_firecrawl_app):
    mock_firecrawl_app.map_url.return_value = {"map": "website map"}

    result = await map_website("http://example.com")
    assert result == {"map": "website map"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,params,error_message",
    [
        (scrape_url, ("http://example.com",), "Error scraping URL"),
        (crawl_website, ("http://example.com",), "Error crawling website"),
        (get_crawl_status, ("12345",), "Error getting crawl status"),
        (get_crawl_data, ("12345",), "Error getting crawl data"),
        (cancel_crawl, ("12345",), "Error cancelling crawl"),
        (map_website, ("http://example.com",), "Error mapping website"),
    ],
)
async def test_firecrawl_error(mock_firecrawl_app, method, params, error_message):
    mock_firecrawl_app.scrape_url.side_effect = Exception(error_message)
    mock_firecrawl_app.async_crawl_url.side_effect = Exception(error_message)
    mock_firecrawl_app.check_crawl_status.side_effect = Exception(error_message)
    mock_firecrawl_app.cancel_crawl.side_effect = Exception(error_message)
    mock_firecrawl_app.map_url.side_effect = Exception(error_message)

    with pytest.raises(ToolExecutionError):
        await method(*params)

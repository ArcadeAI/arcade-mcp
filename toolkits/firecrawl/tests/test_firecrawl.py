from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem
from arcade_tdk.errors import ToolExecutionError

from arcade_firecrawl.tools import (
    cancel_crawl,
    crawl_website,
    get_crawl_data,
    get_crawl_status,
    map_website,
    scrape_url,
)


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="firecrawl_api_key", value="fake_api_key")])


@pytest.fixture
def mock_firecrawl_app_for_scrape():
    with patch("arcade_firecrawl.tools.scrape.FirecrawlApp") as app:
        yield app.return_value


@pytest.fixture
def mock_firecrawl_app_for_crawl():
    with patch("arcade_firecrawl.tools.crawl.FirecrawlApp") as app:
        yield app.return_value


@pytest.fixture
def mock_firecrawl_app_for_map():
    with patch("arcade_firecrawl.tools.map.FirecrawlApp") as app:
        yield app.return_value


@pytest.mark.asyncio
async def test_scrape_url_success(mock_firecrawl_app_for_scrape, mock_context):
    expected_response = {
        "success": True,
        "data": {"scraped_content": "scraped content"},
    }
    mock_firecrawl_app_for_scrape.scrape_url.return_value = expected_response

    result = await scrape_url(mock_context, "http://example.com")
    assert result == expected_response


@pytest.mark.asyncio
async def test_crawl_website_success(mock_firecrawl_app_for_crawl, mock_context):
    expected_response = {
        "id": "12345",
        "success": True,
    }
    mock_firecrawl_app_for_crawl.async_crawl_url.return_value = expected_response
    mock_firecrawl_app_for_crawl.check_crawl_status.return_value = expected_response

    result = await crawl_website(mock_context, "http://example.com")
    assert result == expected_response


@pytest.mark.asyncio
async def test_get_crawl_status_success(mock_firecrawl_app_for_crawl, mock_context):
    expected_response = {"status": "completed"}
    mock_firecrawl_app_for_crawl.check_crawl_status.return_value = expected_response

    result = await get_crawl_status(mock_context, "12345")
    assert result == expected_response


@pytest.mark.asyncio
async def test_get_crawl_data_success(mock_firecrawl_app_for_crawl, mock_context):
    expected_response = {"data": "crawl data"}
    mock_firecrawl_app_for_crawl.check_crawl_status.return_value = expected_response

    result = await get_crawl_data(mock_context, "12345")
    assert result == expected_response


@pytest.mark.asyncio
async def test_cancel_crawl_success(mock_firecrawl_app_for_crawl, mock_context):
    expected_response = {"status": "cancelled"}
    mock_firecrawl_app_for_crawl.cancel_crawl.return_value = expected_response

    result = await cancel_crawl(mock_context, "12345")
    assert result == expected_response


@pytest.mark.asyncio
async def test_map_website_success(mock_firecrawl_app_for_map, mock_context):
    expected_response = {"map": "website map"}
    mock_firecrawl_app_for_map.map_url.return_value = expected_response

    result = await map_website(mock_context, "http://example.com")
    assert result == expected_response


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
async def test_firecrawl_error(
    mock_firecrawl_app_for_scrape,
    mock_firecrawl_app_for_crawl,
    mock_firecrawl_app_for_map,
    mock_context,
    method,
    params,
    error_message,
):
    mock_firecrawl_app_for_scrape.scrape_url.side_effect = Exception(error_message)
    mock_firecrawl_app_for_crawl.async_crawl_url.side_effect = Exception(error_message)
    mock_firecrawl_app_for_crawl.check_crawl_status.side_effect = Exception(error_message)
    mock_firecrawl_app_for_crawl.cancel_crawl.side_effect = Exception(error_message)
    mock_firecrawl_app_for_map.map_url.side_effect = Exception(error_message)

    with pytest.raises(ToolExecutionError):
        await method(mock_context, *params)

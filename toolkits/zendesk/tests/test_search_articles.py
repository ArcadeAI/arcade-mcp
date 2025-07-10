from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_zendesk.enums import ArticleSortBy, SortOrder
from arcade_zendesk.tools.search_articles import search_articles


class TestSearchArticlesValidation:
    """Test input validation for search_articles."""

    @pytest.mark.asyncio
    async def test_missing_subdomain(self, mock_context):
        """Test error when subdomain is not configured."""
        mock_context.get_secret.side_effect = ValueError("Secret not found")

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_articles(context=mock_context, query="test")

        assert "subdomain is not set" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_missing_search_params(self, mock_context):
        """Test error when no search parameters provided."""
        mock_context.get_secret.return_value = "test-subdomain"

        with pytest.raises(RetryableToolError) as exc_info:
            await search_articles(context=mock_context)

        assert "At least one search parameter" in str(exc_info.value.message)

    @pytest.mark.parametrize(
        "date_param,date_value",
        [
            ("created_after", "2024/01/01"),
            ("created_before", "01-15-2024"),
            ("created_at", "2024-1-15"),
            ("created_after", "2024-01-1"),
            ("created_before", "20240115"),
            ("created_at", "not-a-date"),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_date_format(self, mock_context, date_param, date_value):
        """Test validation of date format parameters."""
        mock_context.get_secret.return_value = "test-subdomain"

        with pytest.raises(RetryableToolError) as exc_info:
            await search_articles(context=mock_context, query="test", **{date_param: date_value})

        assert "Invalid date format" in str(exc_info.value.message)
        assert "YYYY-MM-DD" in str(exc_info.value.message)
        assert date_param in str(exc_info.value.message)

    @pytest.mark.parametrize("limit", [0, -1, -10])
    @pytest.mark.asyncio
    async def test_invalid_limit(self, mock_context, limit):
        """Test validation of limit parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        with pytest.raises(RetryableToolError) as exc_info:
            await search_articles(context=mock_context, query="test", limit=limit)

        assert "at least 1" in str(exc_info.value.message)

    @pytest.mark.parametrize("offset", [-1, -10])
    @pytest.mark.asyncio
    async def test_invalid_offset(self, mock_context, offset):
        """Test validation of offset parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        with pytest.raises(RetryableToolError) as exc_info:
            await search_articles(context=mock_context, query="test", offset=offset)

        assert "cannot be negative" in str(exc_info.value.message)


class TestSearchArticlesSuccess:
    """Test successful search scenarios."""

    @pytest.mark.asyncio
    async def test_basic_search(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test basic search with query parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup mock response
        search_response = build_search_response()
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(context=mock_context, query="password reset")

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["metadata"]["title"] == "How to reset your password"

        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        assert (
            call_args[0][0]
            == "https://test-subdomain.zendesk.com/api/v2/help_center/articles/search"
        )
        assert call_args[1]["params"]["query"] == "password reset"
        # Check that pagination params were set correctly
        assert call_args[1]["params"]["page"] == 1
        assert call_args[1]["params"]["per_page"] == 100

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test search with multiple filter parameters."""
        mock_context.get_secret.return_value = "test-subdomain"

        search_response = build_search_response()
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(
            context=mock_context,
            query="API",
            created_after="2024-01-01",
            sort_by=ArticleSortBy.CREATED_AT,
            sort_order=SortOrder.DESC,
            limit=25,
        )

        assert "results" in result

        # Verify all parameters were passed
        call_params = mock_httpx_client.get.call_args[1]["params"]
        assert call_params["query"] == "API"
        assert call_params["created_after"] == "2024-01-01"
        assert call_params["sort_by"] == "created_at"
        assert call_params["sort_order"] == "desc"
        # Should fetch first page with 100 items per page
        assert call_params["page"] == 1
        assert call_params["per_page"] == 100

    @pytest.mark.asyncio
    async def test_search_without_body(
        self,
        mock_context,
        mock_httpx_client,
        sample_article_response,
        mock_http_response,
    ):
        """Test search with include_body=False."""
        mock_context.get_secret.return_value = "test-subdomain"

        search_response = {"results": [sample_article_response], "next_page": None}
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(context=mock_context, query="test", include_body=False)

        assert result["results"][0]["content"] is None
        assert result["results"][0]["metadata"]["title"] == sample_article_response["title"]

    @pytest.mark.asyncio
    async def test_search_by_labels(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test search by label names."""
        mock_context.get_secret.return_value = "test-subdomain"

        search_response = build_search_response()
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(context=mock_context, label_names=["password", "security"])

        assert "results" in result
        assert mock_httpx_client.get.call_args[1]["params"]["label_names"] == "password,security"


class TestSearchArticlesPagination:
    """Test pagination scenarios."""

    @pytest.mark.asyncio
    async def test_single_page_default(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test default behavior returns single page."""
        mock_context.get_secret.return_value = "test-subdomain"

        search_response = build_search_response(count=100)
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(context=mock_context, query="test")

        assert len(result["results"]) == 1
        assert mock_httpx_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_with_limit_across_pages(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test fetching results across multiple pages with limit."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup pagination responses - 100 items per page
        articles_page1 = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(1, 101)
        ]
        articles_page2 = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(101, 201)
        ]

        page1 = {"results": articles_page1, "next_page": "page2"}
        page2 = {"results": articles_page2, "next_page": "page3"}

        mock_httpx_client.get.side_effect = [
            mock_http_response(page1),
            mock_http_response(page2),
        ]

        # Request 150 items starting from offset 0
        result = await search_articles(context=mock_context, query="test", limit=150)

        assert result["count"] == 150
        assert "next_offset" in result  # More results available
        assert result["next_offset"] == 150
        assert mock_httpx_client.get.call_count == 2  # Fetched 2 pages

    @pytest.mark.asyncio
    async def test_fetch_with_offset(self, mock_context, mock_httpx_client, mock_http_response):
        """Test fetching with offset parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup response - page 2 would have items 101-200
        # We want items starting from offset 150 (which is item 151, at index 50 on page 2)
        articles_page2 = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(101, 201)
        ]
        response = {"results": articles_page2, "next_page": "page3"}

        mock_httpx_client.get.return_value = mock_http_response(response)

        # Request 30 items starting from offset 150
        result = await search_articles(context=mock_context, query="test", offset=150, limit=30)

        assert result["count"] == 30
        assert "next_offset" in result
        assert result["next_offset"] == 180

        # Should request page 2 (offset 150 = page 2, starting at index 50)
        call_params = mock_httpx_client.get.call_args[1]["params"]
        assert call_params["page"] == 2

    @pytest.mark.asyncio
    async def test_no_next_offset_when_no_more_results(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test that next_offset is not included when no more results."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup response with no next page
        articles = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(1, 21)
        ]
        response = {"results": articles, "next_page": None}

        mock_httpx_client.get.return_value = mock_http_response(response)

        result = await search_articles(context=mock_context, query="test", limit=20)

        assert result["count"] == 20
        assert "next_offset" not in result  # No more results

    @pytest.mark.asyncio
    async def test_partial_page_with_more_items(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test that next_offset is included when there are more items on the current page."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup response with 50 items on a page, but we only request 30
        articles = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(1, 51)
        ]
        response = {"results": articles, "next_page": None}

        mock_httpx_client.get.return_value = mock_http_response(response)

        # Request only 30 items when page has 50
        result = await search_articles(context=mock_context, query="test", limit=30)

        assert result["count"] == 30
        assert "next_offset" in result  # More items available on current page
        assert result["next_offset"] == 30

    @pytest.mark.asyncio
    async def test_request_more_than_available(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when requesting more items than are available returns only what's available."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup response with only 15 items total
        articles = [
            {"id": i, "title": f"Article {i}", "body": f"Content {i}"} for i in range(1, 16)
        ]
        response = {"results": articles, "next_page": None}

        mock_httpx_client.get.return_value = mock_http_response(response)

        # Request 30 items when only 15 are available
        result = await search_articles(context=mock_context, query="test", limit=30)

        assert result["count"] == 15  # Only returns what's available
        assert "next_offset" not in result  # No more results


class TestSearchArticlesErrors:
    """Test error handling scenarios."""

    @pytest.mark.parametrize(
        "status_code,error_key",
        [
            (400, "HTTP 400"),
            (401, "HTTP 401"),
            (403, "HTTP 403"),
            (404, "HTTP 404"),
            (500, "HTTP 500"),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_errors(self, mock_context, mock_httpx_client, status_code, error_key):
        """Test handling of HTTP errors."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Create mock error response
        error_response = MagicMock()
        error_response.status_code = status_code
        error_response.text = f"Error message for {status_code}"
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}", request=MagicMock(), response=error_response
        )

        mock_httpx_client.get.return_value = error_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_articles(context=mock_context, query="test")

        assert "Failed to search articles" in str(exc_info.value.message)
        assert f"HTTP {status_code}" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_context, mock_httpx_client):
        """Test handling of timeout errors."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(RetryableToolError) as exc_info:
            await search_articles(context=mock_context, query="test")

        assert "timed out" in str(exc_info.value.message)
        assert exc_info.value.retry_after_ms == 5000

    @pytest.mark.asyncio
    async def test_unexpected_error(self, mock_context, mock_httpx_client):
        """Test handling of unexpected errors."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.side_effect = Exception("Unexpected error occurred")

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_articles(context=mock_context, query="test")

        assert "Unexpected error occurred" in str(exc_info.value.message)


class TestSearchArticlesContentProcessing:
    """Test content processing and formatting."""

    @pytest.mark.asyncio
    async def test_html_cleaning(self, mock_context, mock_httpx_client, mock_http_response):
        """Test HTML content is properly cleaned."""
        mock_context.get_secret.return_value = "test-subdomain"

        article_with_html = {
            "id": 1,
            "title": "Test Article",
            "body": "<h1>Header</h1><p>Paragraph with <strong>bold</strong> and "
            "<em>italic</em>.</p><br/><div>Div content</div>",
            "url": "https://example.com/article/1",
        }

        search_response = {"results": [article_with_html], "next_page": None}
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        result = await search_articles(context=mock_context, query="test", include_body=True)

        content = result["results"][0]["content"]
        assert content == "Header Paragraph with bold and italic . Div content"

    @pytest.mark.asyncio
    async def test_max_article_length(self, mock_context, mock_httpx_client, mock_http_response):
        """Test article length limiting."""
        mock_context.get_secret.return_value = "test-subdomain"

        long_article = {
            "id": 1,
            "title": "Long Article",
            "body": "A" * 1000,  # 1000 character body
        }

        search_response = {"results": [long_article], "next_page": None}
        mock_httpx_client.get.return_value = mock_http_response(search_response)

        # Test with default 500 char limit
        result = await search_articles(context=mock_context, query="test")
        assert len(result["results"][0]["content"]) < 520  # 500 + truncation suffix

        # Test with custom limit
        result = await search_articles(context=mock_context, query="test", max_article_length=100)
        assert len(result["results"][0]["content"]) < 120  # 100 + truncation suffix

        # Test with no limit
        result = await search_articles(context=mock_context, query="test", max_article_length=None)
        assert len(result["results"][0]["content"]) == 1000

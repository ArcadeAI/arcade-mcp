from unittest.mock import MagicMock

import httpx
import pytest

from arcade_zendesk.tools.search_articles import search_articles


class TestSearchArticlesValidation:
    """Test input validation for search_articles."""

    @pytest.mark.asyncio
    async def test_missing_auth_token(self, mock_context):
        """Test error when auth token is missing."""
        mock_context.get_auth_token_or_empty.return_value = ""

        result = await search_articles(context=mock_context, query="test")

        assert result["error"] == "AuthenticationError"
        assert "authentication token" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_subdomain(self, mock_context):
        """Test error when subdomain is not configured."""
        mock_context.get_secret.return_value = None

        result = await search_articles(context=mock_context, query="test")

        assert result["error"] == "ConfigurationError"
        assert "ZENDESK_SUBDOMAIN" in result["message"]

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

        result = await search_articles(
            context=mock_context, query="test", **{date_param: date_value}
        )

        assert result["error"] == "InvalidDateFormat"
        assert "YYYY-MM-DD" in result["message"]
        assert date_param in result["message"]

    @pytest.mark.parametrize("sort_by", ["relevance", "invalid_sort", "random"])
    @pytest.mark.asyncio
    async def test_invalid_sort_parameter(self, mock_context, sort_by):
        """Test validation of sort_by parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        result = await search_articles(context=mock_context, query="test", sort_by=sort_by)

        assert result["error"] == "InvalidSortParameter"
        assert "created_at" in result["message"]
        assert "created_at" in result["message"]

    @pytest.mark.parametrize("sort_order", ["ascending", "newest", "oldest"])
    @pytest.mark.asyncio
    async def test_invalid_sort_order(self, mock_context, sort_order):
        """Test validation of sort_order parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        result = await search_articles(context=mock_context, query="test", sort_order=sort_order)

        assert result["error"] == "InvalidSortOrder"
        assert "asc" in result["message"]
        assert "desc" in result["message"]

    @pytest.mark.parametrize("max_pages", [0, -1, -10])
    @pytest.mark.asyncio
    async def test_invalid_max_pages(self, mock_context, max_pages):
        """Test validation of max_pages parameter."""
        mock_context.get_secret.return_value = "test-subdomain"

        result = await search_articles(context=mock_context, query="test", max_pages=max_pages)

        assert result["error"] == "InvalidPaginationParameter"
        assert "at least 1" in result["message"]


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
        assert call_args[1]["params"]["per_page"] == 10

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
            category=123,
            section=456,
            created_after="2024-01-01",
            sort_by="created_at",
            sort_order="desc",
            per_page=25,
        )

        assert "results" in result

        # Verify all parameters were passed
        call_params = mock_httpx_client.get.call_args[1]["params"]
        assert call_params["query"] == "API"
        assert call_params["category"] == 123
        assert call_params["section"] == 456
        assert call_params["created_after"] == "2024-01-01"
        assert call_params["sort_by"] == "created_at"
        assert call_params["sort_order"] == "desc"
        assert call_params["per_page"] == 25

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

        result = await search_articles(context=mock_context, label_names="password,security")

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
    async def test_all_pages(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test fetching all pages."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup pagination responses
        page1 = build_search_response(
            articles=[{"id": 1, "title": "Article 1", "body": "Content 1"}],
            next_page="page2",
        )
        page2 = build_search_response(
            articles=[{"id": 2, "title": "Article 2", "body": "Content 2"}],
            next_page="page3",
        )
        page3 = build_search_response(
            articles=[{"id": 3, "title": "Article 3", "body": "Content 3"}],
            next_page=None,
        )

        mock_httpx_client.get.side_effect = [
            mock_http_response(page1),
            mock_http_response(page2),
            mock_http_response(page3),
        ]

        result = await search_articles(context=mock_context, query="test", all_pages=True)

        assert len(result["results"]) == 3
        assert mock_httpx_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_max_pages_limit(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test max_pages parameter limits fetching."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup 5 pages but limit to 2
        responses = []
        for i in range(5):
            next_page = f"page{i + 2}" if i < 4 else None
            page = build_search_response(
                articles=[{"id": i + 1, "title": f"Article {i + 1}", "body": f"Content {i + 1}"}],
                next_page=next_page,
            )
            responses.append(mock_http_response(page))

        mock_httpx_client.get.side_effect = responses

        result = await search_articles(context=mock_context, query="test", max_pages=2)

        assert len(result["results"]) == 2
        assert mock_httpx_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_all_pages_overrides_max_pages(
        self, mock_context, mock_httpx_client, build_search_response, mock_http_response
    ):
        """Test all_pages=True takes precedence over max_pages."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Setup 3 pages
        responses = []
        for i in range(3):
            next_page = f"page{i + 2}" if i < 2 else None
            page = build_search_response(
                articles=[{"id": i + 1, "title": f"Article {i + 1}", "body": f"Content {i + 1}"}],
                next_page=next_page,
            )
            responses.append(mock_http_response(page))

        mock_httpx_client.get.side_effect = responses

        result = await search_articles(
            context=mock_context,
            query="test",
            all_pages=True,
            max_pages=1,  # Should be ignored
        )

        assert len(result["results"]) == 3
        assert mock_httpx_client.get.call_count == 3


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

        result = await search_articles(context=mock_context, query="test")

        assert result["error"] == error_key
        assert "Failed to search articles" in result["message"]
        assert (
            result["url"] == "https://test-subdomain.zendesk.com/api/v2/help_center/articles/search"
        )

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_context, mock_httpx_client):
        """Test handling of timeout errors."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.side_effect = httpx.TimeoutException("Request timed out")

        result = await search_articles(context=mock_context, query="test")

        assert result["error"] == "TimeoutError"
        assert "timed out" in result["message"]
        assert "Try reducing per_page" in result["message"]

    @pytest.mark.asyncio
    async def test_unexpected_error(self, mock_context, mock_httpx_client):
        """Test handling of unexpected errors."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.side_effect = Exception("Unexpected error occurred")

        result = await search_articles(context=mock_context, query="test")

        assert result["error"] == "SearchError"
        assert "Unexpected error occurred" in result["message"]


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

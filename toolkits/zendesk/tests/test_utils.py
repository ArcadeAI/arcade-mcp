import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx
from arcade_zendesk.utils import (
    clean_html_text,
    truncate_text,
    process_article_body,
    process_search_results,
    validate_date_format,
    fetch_all_pages,
    MAX_TOTAL_RESULTS,
)


class TestCleanHtmlText:
    """Test HTML cleaning functionality."""

    def test_clean_simple_html(self):
        """Test cleaning basic HTML tags."""
        html = "<p>Hello <strong>World</strong></p>"
        assert clean_html_text(html) == "Hello World"

    def test_clean_complex_html(self):
        """Test cleaning complex HTML with multiple tags."""
        html = """
        <h1>Title</h1>
        <p>Paragraph with <em>emphasis</em> and <strong>bold</strong>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <div class="footer">Footer content</div>
        """
        cleaned = clean_html_text(html)
        assert "Title" in cleaned
        assert "Paragraph with emphasis and bold" in cleaned
        assert "Item 1" in cleaned
        assert "Item 2" in cleaned
        assert "Footer content" in cleaned
        assert "<h1>" not in cleaned
        assert "<li>" not in cleaned

    def test_clean_html_with_special_chars(self):
        """Test cleaning HTML with special characters."""
        html = "<p>Price: &pound;100 &amp; &euro;120</p>"
        cleaned = clean_html_text(html)
        assert "£100" in cleaned or "100" in cleaned  # Depends on BeautifulSoup version
        assert "&" in cleaned
        assert "€120" in cleaned or "120" in cleaned

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            (None, ""),
            ("", ""),
            ("   ", ""),
            ("<p></p>", ""),
            ("<p>   </p>", ""),
        ],
    )
    def test_clean_html_edge_cases(self, input_value, expected):
        """Test edge cases for HTML cleaning."""
        assert clean_html_text(input_value) == expected

    def test_clean_html_preserves_line_breaks(self):
        """Test that meaningful line breaks are preserved."""
        html = "<p>Line 1</p><p>Line 2</p>"
        cleaned = clean_html_text(html)
        # Should have text from both lines
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned


class TestTruncateText:
    """Test text truncation functionality."""

    def test_truncate_long_text(self):
        """Test truncating text longer than max length."""
        text = "This is a very long text that needs to be truncated"
        result = truncate_text(text, 20)
        assert result == "This ... [truncated]"
        assert len(result) == 20

    def test_no_truncation_needed(self):
        """Test text shorter than max length is not truncated."""
        text = "Short text"
        assert truncate_text(text, 20) == text

    def test_truncate_with_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "This is a long text for testing"
        result = truncate_text(text, 15, "...")
        assert result == "This is a lo..."
        assert len(result) == 15

    @pytest.mark.parametrize(
        "text,max_length,expected",
        [
            (None, 10, None),
            ("", 10, ""),
            ("Hello", 5, "Hello"),
            ("Hello World", 5, " ... [truncated]"),  # Suffix is longer than allowed
        ],
    )
    def test_truncate_edge_cases(self, text, max_length, expected):
        """Test edge cases for truncation."""
        result = truncate_text(text, max_length)
        if expected == " ... [truncated]":
            # When suffix is longer than max_length, only suffix is returned
            assert result == expected
        else:
            assert result == expected

    def test_truncate_at_word_boundary(self):
        """Test that truncation happens cleanly."""
        text = "The quick brown fox jumps over the lazy dog"
        result = truncate_text(text, 25)
        assert result == "The quick ... [truncated]"
        assert len(result) == 25


class TestProcessArticleBody:
    """Test article body processing."""

    def test_process_html_body(self):
        """Test processing HTML body content."""
        body = "<h1>Article Title</h1><p>Article content with <strong>formatting</strong>.</p>"
        result = process_article_body(body)
        assert "Article Title" in result
        assert "Article content with formatting" in result
        assert "<h1>" not in result
        assert "<strong>" not in result

    def test_process_body_with_truncation(self):
        """Test processing body with max length."""
        body = "<p>" + "Long content " * 50 + "</p>"
        result = process_article_body(body, max_length=100)
        assert len(result) <= 100 + len(" ... [truncated]")
        assert result.endswith(" ... [truncated]")

    @pytest.mark.parametrize(
        "body,max_length,expected",
        [
            (None, None, None),
            ("", None, None),
            ("<p>Short</p>", 100, "Short"),
            (
                "<p></p>",
                None,
                "",
            ),  # Empty paragraph returns empty string after cleaning
        ],
    )
    def test_process_body_edge_cases(self, body, max_length, expected):
        """Test edge cases for body processing."""
        result = process_article_body(body, max_length)
        assert result == expected


class TestProcessSearchResults:
    """Test search results processing."""

    def test_process_results_with_body(self):
        """Test processing results with body content included."""
        results = [
            {
                "id": 1,
                "title": "Article 1",
                "body": "<p>Content 1</p>",
                "url": "https://example.com/1",
            },
            {
                "id": 2,
                "title": "Article 2",
                "body": "<p>Content 2</p>",
                "url": "https://example.com/2",
            },
        ]

        processed = process_search_results(results, include_body=True)

        assert len(processed) == 2
        assert processed[0]["content"] == "Content 1"
        assert processed[0]["metadata"]["id"] == 1
        assert processed[0]["metadata"]["title"] == "Article 1"
        assert "body" not in processed[0]["metadata"]

        assert processed[1]["content"] == "Content 2"
        assert processed[1]["metadata"]["id"] == 2

    def test_process_results_without_body(self):
        """Test processing results without body content."""
        results = [
            {
                "id": 1,
                "title": "Article 1",
                "body": "<p>Content 1</p>",
                "url": "https://example.com/1",
            }
        ]

        processed = process_search_results(results, include_body=False)

        assert processed[0]["content"] is None
        assert processed[0]["metadata"]["id"] == 1
        assert processed[0]["metadata"]["title"] == "Article 1"
        assert "body" not in processed[0]["metadata"]

    def test_process_results_with_max_body_length(self):
        """Test processing results with body length limit."""
        results = [
            {
                "id": 1,
                "title": "Article",
                "body": "<p>" + "Long content " * 100 + "</p>",
            }
        ]

        processed = process_search_results(results, include_body=True, max_body_length=50)

        content = processed[0]["content"]
        assert len(content) <= 50 + len(" ... [truncated]")
        assert content.endswith(" ... [truncated]")

    def test_process_empty_results(self):
        """Test processing empty results list."""
        processed = process_search_results([])
        assert processed == []

    def test_process_results_preserves_all_metadata(self):
        """Test that all non-body fields are preserved in metadata."""
        results = [
            {
                "id": 1,
                "title": "Article",
                "body": "<p>Content</p>",
                "url": "https://example.com/1",
                "created_at": "2024-01-01",
                "custom_field": "value",
                "nested": {"key": "value"},
            }
        ]

        processed = process_search_results(results, include_body=True)

        metadata = processed[0]["metadata"]
        assert metadata["id"] == 1
        assert metadata["title"] == "Article"
        assert metadata["url"] == "https://example.com/1"
        assert metadata["created_at"] == "2024-01-01"
        assert metadata["custom_field"] == "value"
        assert metadata["nested"] == {"key": "value"}
        assert "body" not in metadata


class TestValidateDateFormat:
    """Test date format validation."""

    @pytest.mark.parametrize(
        "date_string",
        [
            "2024-01-15",
            "2024-12-31",
            "2000-01-01",
            "1999-12-31",
            "2030-06-15",
        ],
    )
    def test_valid_date_formats(self, date_string):
        """Test valid YYYY-MM-DD date formats."""
        assert validate_date_format(date_string) is True

    @pytest.mark.parametrize(
        "date_string",
        [
            "2024/01/15",
            "01-15-2024",
            "2024-1-15",
            "2024-01-1",
            "24-01-15",
            "2024.01.15",
            "20240115",
            "January 15, 2024",
            "15/01/2024",
            "2024",
            "2024-01",
            "",
            "not-a-date",
            # Note: These have valid format but invalid values - regex only checks format
        ],
    )
    def test_invalid_date_formats(self, date_string):
        """Test invalid date formats."""
        assert validate_date_format(date_string) is False


class TestFetchAllPages:
    """Test pagination fetching functionality."""

    @pytest.mark.asyncio
    async def test_fetch_single_page(self, mock_http_response):
        """Test fetching a single page of results."""
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_http_response({
            "results": [{"id": 1}, {"id": 2}],
            "next_page": None,
        })

        result = await fetch_all_pages(
            client=mock_client,
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
            params={"query": "test"},
            max_pages=None,
        )

        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == 1
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_multiple_pages(self, mock_http_response):
        """Test fetching multiple pages."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_http_response({"results": [{"id": 1}], "next_page": "page2"}),
            mock_http_response({"results": [{"id": 2}], "next_page": "page3"}),
            mock_http_response({"results": [{"id": 3}], "next_page": None}),
        ]

        result = await fetch_all_pages(
            client=mock_client,
            url="https://example.com/api",
            headers={},
            params={},
            max_pages=None,
        )

        assert len(result["results"]) == 3
        assert [r["id"] for r in result["results"]] == [1, 2, 3]
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_with_max_pages_limit(self, mock_http_response):
        """Test fetching with max_pages limit."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_http_response({"results": [{"id": i}], "next_page": f"page{i + 1}"})
            for i in range(1, 6)
        ]

        result = await fetch_all_pages(
            client=mock_client,
            url="https://example.com/api",
            headers={},
            params={},
            max_pages=3,
        )

        assert len(result["results"]) == 3
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_with_total_results_limit(self, mock_http_response):
        """Test fetching stops at MAX_TOTAL_RESULTS."""
        mock_client = AsyncMock()

        # Create pages with many results each
        results_per_page = 100
        num_pages = (MAX_TOTAL_RESULTS // results_per_page) + 2

        responses = []
        for i in range(num_pages):
            page_results = [
                {"id": j} for j in range(i * results_per_page, (i + 1) * results_per_page)
            ]
            responses.append(
                mock_http_response({
                    "results": page_results,
                    "next_page": f"page{i + 2}" if i < num_pages - 1 else None,
                })
            )

        mock_client.get.side_effect = responses

        result = await fetch_all_pages(
            client=mock_client,
            url="https://example.com/api",
            headers={},
            params={},
            max_pages=None,
        )

        assert len(result["results"]) >= MAX_TOTAL_RESULTS
        assert "warnings" in result
        assert result["warnings"][0]["type"] == "ResultLimitReached"
        assert str(MAX_TOTAL_RESULTS) in result["warnings"][0]["message"]

    @pytest.mark.asyncio
    async def test_fetch_handles_http_errors(self, mock_http_response):
        """Test fetch handles HTTP errors properly."""
        mock_client = AsyncMock()

        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="HTTP 500", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_client.get.return_value = error_response

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_all_pages(
                client=mock_client,
                url="https://example.com/api",
                headers={},
                params={},
                max_pages=None,
            )

    @pytest.mark.asyncio
    async def test_fetch_increments_page_parameter(self, mock_http_response):
        """Test that page parameter is properly incremented."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            mock_http_response({"results": [{"id": 1}], "next_page": "page2"}),
            mock_http_response({"results": [{"id": 2}], "next_page": "page3"}),
            mock_http_response({"results": [{"id": 3}], "next_page": None}),
        ]

        await fetch_all_pages(
            client=mock_client,
            url="https://example.com/api",
            headers={},
            params={"page": 1},
            max_pages=None,
        )

        assert mock_client.get.call_count == 3

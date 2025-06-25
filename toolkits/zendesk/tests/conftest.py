from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_tdk import ToolContext


@pytest.fixture
def mock_context():
    """Standard mock context fixture used across all arcade toolkits."""
    context = MagicMock(spec=ToolContext)

    context.get_auth_token_or_empty = MagicMock(return_value="fake-token")
    context.get_secret = MagicMock()

    return context


@pytest.fixture
def mock_httpx_client(mocker):
    """Mock httpx.AsyncClient for API calls."""
    mock_client_class = mocker.patch("httpx.AsyncClient", autospec=True)
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    return mock_client


@pytest.fixture
def sample_article_response():
    """Sample article data for testing."""
    return {
        "id": 123456,
        "title": "How to reset your password",
        "body": "<p>To reset your password, follow these steps:</p>"
        "<ol><li>Click forgot password</li><li>Enter your email</li></ol>",
        "url": "https://support.example.com/hc/en-us/articles/123456",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-06-01T15:30:00Z",
        "section_id": 789,
        "category_id": 456,
        "label_names": ["password", "security", "account"],
    }


@pytest.fixture
def build_search_response(sample_article_response):
    """Builder for search API responses."""

    def builder(articles=None, next_page=None, count=None):
        if articles is None:
            articles = [sample_article_response]

        response = {
            "results": articles,
            "next_page": next_page,
            "page": 1,
            "per_page": len(articles),
            "page_count": 1,
        }

        if count is not None:
            response["count"] = count

        return response

    return builder


@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses."""

    def create_response(json_data=None, status_code=200, raise_for_status=True):
        response = MagicMock()
        response.json.return_value = json_data
        response.status_code = status_code

        if raise_for_status and status_code >= 400:
            response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            response.raise_for_status.return_value = None

        return response

    return create_response

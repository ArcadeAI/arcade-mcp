from unittest.mock import AsyncMock, patch

import pytest
from arcade_github.tools.repositories import (
    count_stargazers,
    get_repository,
    list_org_repositories,
    list_repository_activities,
    list_review_comments_in_a_repository,
    search_issues,
)
from httpx import Response

from arcade.core.errors import ToolExecutionError


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_client():
    with patch("arcade_github.tools.repositories.httpx.AsyncClient") as client:
        yield client.return_value.__aenter__.return_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_message,expected_error",
    [
        (422, "Validation Failed", "Error accessing.*: Validation failed"),
        (301, "Moved Permanently", "Error accessing.*: Moved permanently"),
        (404, "Not Found", "Error accessing.*: Resource not found"),
        (503, "Service Unavailable", "Error accessing.*: Service unavailable"),
        (410, "Gone", "Error accessing.*: Gone"),
    ],
)
async def test_error_responses(
    mock_context, mock_client, status_code, error_message, expected_error
):
    mock_client.get.return_value = Response(status_code, json={"message": error_message})
    mock_client.post.return_value = Response(status_code, json={"message": error_message})

    with pytest.raises(ToolExecutionError, match=expected_error):
        if status_code == 422:
            await search_issues(mock_context, "owner", "repo", "invalid query")
        elif status_code == 301:
            await count_stargazers("owner", "repo")
        elif status_code == 404:
            await list_org_repositories(mock_context, "non_existent_org")
        elif status_code == 503:
            await get_repository(mock_context, "owner", "repo")
        elif status_code == 410:
            await list_review_comments_in_a_repository(mock_context, "owner", "repo")


@pytest.mark.asyncio
async def test_list_repository_activities_invalid_cursor(mock_context, mock_client):
    mock_client.get.return_value = Response(422, json={"message": "Validation Failed"})

    with pytest.raises(ToolExecutionError, match="Error accessing.*: Validation failed"):
        await list_repository_activities(mock_context, "owner", "repo", before="invalid_cursor")


@pytest.mark.asyncio
async def test_search_issues_success(mock_context, mock_client):
    mock_client.get.return_value = Response(
        200,
        json={
            "items": [
                {
                    "title": "Test Issue",
                    "html_url": "https://github.com/owner/repo/issues/1",
                    "created_at": "2023-05-01T12:00:00Z",
                }
            ]
        },
    )

    result = await search_issues(mock_context, "owner", "repo", "test query")
    assert "Test Issue" in str(result)
    assert "https://github.com/owner/repo/issues/1" in str(result)


@pytest.mark.asyncio
async def test_count_stargazers_success(mock_client):
    mock_client.get.return_value = Response(200, json={"stargazers_count": 42})

    result = await count_stargazers("owner", "repo")
    assert result == 42

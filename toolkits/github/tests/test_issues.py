from unittest.mock import AsyncMock, patch

import pytest
from arcade_github.tools.issues import create_issue, create_issue_comment
from httpx import Response

from arcade.sdk.errors import ToolExecutionError


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_client():
    with patch("arcade_github.tools.issues.httpx.AsyncClient") as client:
        yield client.return_value.__aenter__.return_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_message,expected_error,func,args",
    [
        (
            422,
            "Validation Failed",
            "Error accessing.*: Validation failed",
            create_issue,
            ("owner", "repo", "title"),
        ),
        (
            401,
            "Unauthorized",
            "Error accessing.*: Failed to process request",
            create_issue_comment,
            ("owner", "repo", 1, "body"),
        ),
        (
            403,
            "API rate limit exceeded",
            "Error accessing.*: Forbidden",
            create_issue_comment,
            ("owner", "repo", 1, "body"),
        ),
        (
            401,
            "Bad credentials",
            "Error accessing.*: Failed to process request",
            create_issue,
            ("owner", "repo", "title"),
        ),
    ],
)
async def test_issue_errors(
    mock_context, mock_client, status_code, error_message, expected_error, func, args
):
    mock_client.post.return_value = Response(status_code, json={"message": error_message})

    with pytest.raises(ToolExecutionError, match=expected_error):
        await func(mock_context, *args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func,args,response_json,expected_assertions",
    [
        (
            create_issue,
            ("owner", "repo", "Test Issue", "This is a test issue"),
            {
                "id": 1,
                "url": "https://api.github.com/repos/owner/repo/issues/1",
                "title": "Test Issue",
                "body": "This is a test issue",
                "state": "open",
                "html_url": "https://github.com/owner/repo/issues/1",
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-01T12:00:00Z",
                "user": {"login": "testuser"},
                "assignees": [],
                "labels": [],
            },
            ["Test Issue", "https://github.com/owner/repo/issues/1"],
        ),
        (
            create_issue_comment,
            ("owner", "repo", 1, "This is a test comment"),
            {
                "id": 1,
                "url": "https://api.github.com/repos/owner/repo/issues/comments/1",
                "body": "This is a test comment",
                "user": {"login": "testuser"},
                "created_at": "2023-05-01T12:00:00Z",
                "updated_at": "2023-05-01T12:00:00Z",
            },
            ["This is a test comment", "https://api.github.com/repos/owner/repo/issues/comments/1"],
        ),
    ],
)
async def test_issue_success(
    mock_context, mock_client, func, args, response_json, expected_assertions
):
    mock_client.post.return_value = Response(201, json=response_json)

    result = await func(mock_context, *args)
    for assertion in expected_assertions:
        assert assertion in result

from unittest.mock import AsyncMock, patch

import pytest
from arcade_tdk.errors import ToolExecutionError
from httpx import Response

from arcade_github.tools.activity import list_stargazers, set_starred


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_client():
    with patch("arcade_github.tools.activity.httpx.AsyncClient") as client:
        yield client.return_value.__aenter__.return_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "starred,expected_message",
    [
        (True, "Successfully starred the repository owner/repo"),
        (False, "Successfully unstarred the repository owner/repo"),
    ],
)
async def test_set_starred_success(mock_context, mock_client, starred, expected_message):
    mock_client.put.return_value = mock_client.delete.return_value = Response(204)

    result = await set_starred(mock_context, "owner", "repo", starred)
    assert result == expected_message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_message,expected_error",
    [
        (403, "Forbidden", "Error accessing.*: Forbidden"),
        (404, "Not Found", "Error accessing.*: Resource not found"),
        (500, "Internal Server Error", "Error accessing.*: Failed to process request"),
    ],
)
async def test_set_starred_errors(
    mock_context, mock_client, status_code, error_message, expected_error
):
    mock_client.put.return_value = mock_client.delete.return_value = Response(
        status_code, json={"message": error_message}
    )

    with pytest.raises(ToolExecutionError, match=expected_error):
        await set_starred(mock_context, "owner", "repo", True)


@pytest.mark.asyncio
async def test_list_stargazers_success(mock_context, mock_client):
    mock_response_data = [
        {
            "login": "user1",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "html_url": "https://github.com/user1",
        },
        {
            "login": "user2",
            "id": 2,
            "node_id": "MDQ6VXNlcjI=",
            "html_url": "https://github.com/user2",
        },
    ]
    mock_client.get.return_value = Response(200, json=mock_response_data)

    result = await list_stargazers(mock_context, "owner", "repo", limit=2)
    assert result == {"number_of_stargazers": 2, "stargazers": mock_response_data}


@pytest.mark.asyncio
async def test_list_stargazers_empty(mock_context, mock_client):
    mock_client.get.return_value = Response(200, json=[])

    result = await list_stargazers(mock_context, "owner", "repo")
    assert result == {"number_of_stargazers": 0, "stargazers": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_message,expected_error",
    [
        (403, "Forbidden", "Error accessing.*: Forbidden"),
        (404, "Not Found", "Error accessing.*: Resource not found"),
        (500, "Internal Server Error", "Error accessing.*: Failed to process request"),
    ],
)
async def test_list_stargazers_errors(
    mock_context, mock_client, status_code, error_message, expected_error
):
    mock_client.get.return_value = Response(status_code, json={"message": error_message})

    with pytest.raises(ToolExecutionError, match=expected_error):
        await list_stargazers(mock_context, "owner", "repo")

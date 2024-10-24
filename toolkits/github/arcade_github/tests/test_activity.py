from unittest.mock import AsyncMock, patch

import pytest
from arcade_github.tools.activity import set_starred
from httpx import Response

from arcade.sdk.errors import ToolExecutionError


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

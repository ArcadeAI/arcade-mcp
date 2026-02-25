from unittest.mock import MagicMock

import pytest
from arcade_mcp_server import Context


@pytest.fixture
def tool_context():
    """Fixture for the tool Context with mock authorization."""
    context = MagicMock(spec=Context)
    context.authorization.token = "test_token"  # noqa: S105
    context.authorization.user_info = {"sub": "test_user"}
    return context


@pytest.fixture
def mock_httpx_client(mocker):
    """Fixture to mock the httpx.AsyncClient."""
    # Mock the AsyncClient context manager
    mock_client = mocker.patch("httpx.AsyncClient", autospec=True)
    async_mock_client = mock_client.return_value.__aenter__.return_value
    return async_mock_client

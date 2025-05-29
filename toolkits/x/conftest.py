import pytest
from arcade_tdk import ToolContext


@pytest.fixture
def tool_context():
    """Fixture for the ToolContext with mock authorization."""
    return ToolContext(authorization={"token": "test_token", "user_id": "test_user"})


@pytest.fixture
def mock_httpx_client(mocker):
    """Fixture to mock the httpx.AsyncClient."""
    # Mock the AsyncClient context manager
    mock_client = mocker.patch("httpx.AsyncClient", autospec=True)
    async_mock_client = mock_client.return_value.__aenter__.return_value
    return async_mock_client

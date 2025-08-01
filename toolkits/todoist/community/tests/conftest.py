import pytest
from arcade_tdk import ToolContext


@pytest.fixture
def tool_context() -> ToolContext:
    return ToolContext(authorization={"token": "test_token"})


@pytest.fixture
def httpx_mock(mocker):
    mock_client = mocker.patch("httpx.AsyncClient", autospec=True)
    async_mock_client = mock_client.return_value.__aenter__.return_value
    return async_mock_client

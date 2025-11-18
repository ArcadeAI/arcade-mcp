import pytest
from arcade_tdk import ToolContext, ToolSecretItem


@pytest.fixture
def tool_context() -> ToolContext:
    return ToolContext(
        authorization={"token": "test_token"},
        secrets=[ToolSecretItem(key="MASTODON_SERVER_URL", value="https://mastodon.social")],
    )


@pytest.fixture
def httpx_mock(mocker):
    mock_client = mocker.patch("httpx.AsyncClient", autospec=True)
    async_mock_client = mock_client.return_value.__aenter__.return_value
    return async_mock_client


@pytest.fixture
def mock_lookup_single_user_by_username(mocker):
    mock_tool = mocker.patch("arcade_mastodon.tools.statuses.lookup_single_user_by_username")
    return mock_tool

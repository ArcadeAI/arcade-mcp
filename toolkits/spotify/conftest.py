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


@pytest.fixture
def sample_track():
    """Fixture for a sample track."""
    return {
        "album": {"id": "1234567890", "name": "Test Album", "uri": "spotify:album:1234567890"},
        "artists": [{"name": "Test Artist", "type": "artist", "uri": "spotify:artist:1234567890"}],
        "available_markets": ["us"],
        "duration_ms": 123456,
        "id": "1234567890",
        "is_playable": True,
        "name": "Test Track",
        "popularity": 100,
        "type": "track",
        "uri": "spotify:track:1234567890",
    }

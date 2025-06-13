from unittest.mock import patch

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_httpx_client():
    with patch("arcade_hubspot.models.httpx") as mock_httpx:
        yield mock_httpx.AsyncClient().__aenter__.return_value

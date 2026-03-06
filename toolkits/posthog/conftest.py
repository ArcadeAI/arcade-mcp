"""Shared test fixtures for PostHog toolkit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from arcade_mcp_server import Context


MOCK_SECRETS = {
    "POSTHOG_PROJECT_ID": "12345",
    "POSTHOG_SERVER_URL": "https://us.posthog.com",
    "POSTHOG_PERSONAL_API_KEY": "phx_test_key_123",
}


@pytest.fixture
def tool_context():
    """Fixture for the tool Context with mock PostHog secrets."""
    context = MagicMock(spec=Context)
    context.get_secret = MagicMock(side_effect=lambda key: MOCK_SECRETS[key])
    return context


@pytest.fixture
def mock_httpx_client(mocker):
    """Fixture to mock the httpx.AsyncClient."""
    mock_client = mocker.patch("httpx.AsyncClient", autospec=True)
    async_mock_client = mock_client.return_value.__aenter__.return_value
    return async_mock_client

"""Tests for check_connection tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from arcade_posthog.tools.connection import check_connection


@pytest.mark.asyncio
async def test_check_connection_success(tool_context):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "My Project",
        "organization": {"name": "My Org"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("arcade_posthog.tools.connection.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_connection(tool_context)

    assert result["status"] == "connected"
    assert result["project_name"] == "My Project"
    assert result["organization"] == "My Org"


@pytest.mark.asyncio
async def test_check_connection_missing_secret():
    context = MagicMock()
    context.get_secret = MagicMock(side_effect=Exception("Secret not found"))

    result = await check_connection(context)
    assert "error" in result
    assert result["error_type"] == "auth"


@pytest.mark.asyncio
async def test_check_connection_timeout(tool_context):
    with patch("arcade_posthog.tools.connection.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await check_connection(tool_context)

    assert result["retryable"] is True
    assert result["error_type"] == "timeout"

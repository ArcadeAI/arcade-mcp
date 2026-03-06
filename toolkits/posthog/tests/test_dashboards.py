"""Tests for dashboard tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arcade_posthog.tools.dashboards import create_dashboard, get_dashboard, list_dashboards


@pytest.mark.asyncio
async def test_list_dashboards_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {"id": 1, "name": "Growth", "pinned": True, "tags": [], "created_at": "2025-01-01"},
                {"id": 2, "name": "Marketing", "pinned": False, "tags": ["ads"], "created_at": "2025-01-02"},
            ],
            "count": 2,
        }
    }

    with patch(
        "arcade_posthog.tools.dashboards._call_tool",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await list_dashboards(tool_context)

    assert result["count"] == 2
    assert result["results"][0]["name"] == "Growth"
    assert "posthog_url" in result


@pytest.mark.asyncio
async def test_get_dashboard_by_id(tool_context):
    mock_response = {"response_json": {"id": 1, "name": "Growth", "tiles": []}}

    with patch(
        "arcade_posthog.tools.dashboards._call_tool",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_dashboard(tool_context, dashboard_id=1)

    assert "posthog_url" in result


@pytest.mark.asyncio
async def test_get_dashboard_missing_params(tool_context):
    result = await get_dashboard(tool_context)
    assert "error" in result
    assert result["error_type"] == "client"


@pytest.mark.asyncio
async def test_create_dashboard_success(tool_context):
    mock_response = {"response_json": {"id": 99, "name": "New Dashboard"}}

    with patch(
        "arcade_posthog.tools.dashboards._call_tool",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await create_dashboard(tool_context, name="New Dashboard")

    assert result["response_json"]["name"] == "New Dashboard"

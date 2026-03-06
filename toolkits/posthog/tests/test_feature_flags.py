"""Tests for feature flag tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arcade_posthog.tools.feature_flags import (
    delete_feature_flag,
    get_feature_flag,
    list_feature_flags,
)


@pytest.mark.asyncio
async def test_list_feature_flags_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "id": 1,
                    "key": "beta-feature",
                    "name": "Beta Feature",
                    "active": True,
                    "created_at": "2025-01-01",
                },
            ],
            "count": 1,
        }
    }

    with patch(
        "arcade_posthog.tools.feature_flags._call_tool",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await list_feature_flags(tool_context)

    assert result["count"] == 1
    assert result["results"][0]["key"] == "beta-feature"


@pytest.mark.asyncio
async def test_get_feature_flag_missing_params(tool_context):
    result = await get_feature_flag(tool_context)
    assert "error" in result


@pytest.mark.asyncio
async def test_delete_feature_flag_missing_params(tool_context):
    result = await delete_feature_flag(tool_context)
    assert "error" in result

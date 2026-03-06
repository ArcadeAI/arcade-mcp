"""Tests for analytics convenience tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arcade_posthog.tools.analytics import (
    compare_periods,
    get_funnel,
    get_retention,
    get_trend,
    get_trends,
)


@pytest.mark.asyncio
async def test_get_trend_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "label": "$pageview",
                    "count": 500,
                    "labels": ["W1", "W2"],
                    "data": [250, 250],
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_trend(tool_context, event="$pageview")

    assert len(result["series"]) == 1
    assert result["series"][0]["label"] == "$pageview"


@pytest.mark.asyncio
async def test_get_trend_with_breakdown(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "label": "$pageview - Chrome",
                    "count": 300,
                    "labels": ["W1"],
                    "data": [300],
                    "breakdown_value": "Chrome",
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_trend(
            tool_context, event="$pageview", breakdown_property="$browser"
        )

    assert result["series"][0]["breakdown_value"] == "Chrome"


@pytest.mark.asyncio
async def test_get_trend_error(tool_context):
    mock_response = {
        "error": "Query failed",
        "retryable": True,
        "error_type": "server",
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_trend(tool_context, event="$pageview")

    assert result["error"] == "Query failed"


@pytest.mark.asyncio
async def test_get_funnel_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "action_id": "step1",
                    "name": "Pageview",
                    "count": 1000,
                    "conversionRates": {"total": 1.0},
                    "order": 0,
                },
                {
                    "action_id": "step2",
                    "name": "Signup",
                    "count": 200,
                    "conversionRates": {"total": 0.2},
                    "order": 1,
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_funnel(tool_context, steps=["$pageview", "signup"])

    assert len(result["steps"]) == 2
    assert result["steps"][1]["conversion_rate"] == 0.2


@pytest.mark.asyncio
async def test_get_retention_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "date": "2025-01-01",
                    "label": "Week 0",
                    "values": [{"count": 100}, {"count": 50}],
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_retention(tool_context, start_event="signup")

    assert len(result["cohorts"]) == 1
    assert result["cohorts"][0]["people_count"] == 100


@pytest.mark.asyncio
async def test_get_trends_batch(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "label": "$pageview",
                    "count": 500,
                    "labels": ["W1"],
                    "data": [500],
                },
                {
                    "label": "signup",
                    "count": 100,
                    "labels": ["W1"],
                    "data": [100],
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await get_trends(tool_context, events=["$pageview", "signup"])

    assert len(result["series"]) == 2


@pytest.mark.asyncio
async def test_compare_periods_success(tool_context):
    mock_response = {
        "response_json": {
            "results": [
                {
                    "label": "signup",
                    "count": 100,
                    "labels": ["Mon"],
                    "data": [100],
                },
                {
                    "label": "signup - previous",
                    "count": 80,
                    "labels": ["Mon"],
                    "data": [80],
                },
            ]
        }
    }

    with patch(
        "arcade_posthog.tools.analytics._run_posthog_query",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await compare_periods(
            tool_context, event="signup", current_date_from="-7d"
        )

    assert len(result["series"]) == 2

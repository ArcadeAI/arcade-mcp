"""Comprehensive unit tests for all helper functions in arcade_posthog._helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from arcade_posthog._helpers import (
    PARAMETER_ALIASES,
    _attach_url,
    _classify_error,
    _get_project_id,
    _posthog_ui_url,
    _shape_funnel_response,
    _shape_list_response,
    _shape_retention_response,
    _shape_trend_response,
)


class TestClassifyError:
    def test_timeout(self):
        exc = httpx.ReadTimeout("timed out")
        result = _classify_error(exc)
        assert result["retryable"] is True
        assert result["error_type"] == "timeout"

    def test_rate_limit(self):
        response = httpx.Response(429)
        exc = httpx.HTTPStatusError(
            "rate limited",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is True
        assert result["error_type"] == "rate_limit"

    def test_auth_401(self):
        response = httpx.Response(401)
        exc = httpx.HTTPStatusError(
            "unauthorized",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is False
        assert result["error_type"] == "auth"

    def test_auth_403(self):
        response = httpx.Response(403)
        exc = httpx.HTTPStatusError(
            "forbidden",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is False
        assert result["error_type"] == "auth"

    def test_not_found(self):
        response = httpx.Response(404)
        exc = httpx.HTTPStatusError(
            "not found",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is False
        assert result["error_type"] == "not_found"

    def test_server_error(self):
        response = httpx.Response(500)
        exc = httpx.HTTPStatusError(
            "server error",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is True
        assert result["error_type"] == "server"

    def test_client_error(self):
        response = httpx.Response(400)
        exc = httpx.HTTPStatusError(
            "bad request",
            request=httpx.Request("GET", "http://test"),
            response=response,
        )
        result = _classify_error(exc)
        assert result["retryable"] is False
        assert result["error_type"] == "client"

    def test_network_error(self):
        exc = httpx.ConnectError("connection refused")
        result = _classify_error(exc)
        assert result["retryable"] is True
        assert result["error_type"] == "network"

    def test_unknown_error(self):
        exc = ValueError("something went wrong")
        result = _classify_error(exc)
        assert result["retryable"] is False
        assert result["error_type"] == "unknown"


class TestShapeListResponse:
    def test_shapes_results(self):
        response = {
            "response_json": {
                "results": [
                    {"id": 1, "name": "Dashboard A", "pinned": True, "extra_field": "ignored"},
                    {"id": 2, "name": "Dashboard B", "pinned": False, "extra_field": "ignored"},
                ],
                "count": 2,
            }
        }
        result = _shape_list_response(response, ["id", "name", "pinned"])
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0] == {"id": 1, "name": "Dashboard A", "pinned": True}
        assert "extra_field" not in result["results"][0]

    def test_missing_response_json(self):
        response = {"something_else": "value"}
        result = _shape_list_response(response, ["id", "name"])
        assert result == response

    def test_non_dict_response_json(self):
        response = {"response_json": "not a dict"}
        result = _shape_list_response(response, ["id", "name"])
        assert result == response

    def test_no_results_key(self):
        response = {"response_json": {"other": "data"}}
        result = _shape_list_response(response, ["id"])
        assert result == response

    def test_empty_results(self):
        response = {"response_json": {"results": [], "count": 0}}
        result = _shape_list_response(response, ["id"])
        assert result["count"] == 0
        assert result["results"] == []


class TestShapeTrendResponse:
    def test_single_series(self):
        response = {
            "response_json": {
                "results": [
                    {
                        "label": "$pageview",
                        "count": 100,
                        "labels": ["Mon", "Tue"],
                        "data": [50, 50],
                    },
                ]
            }
        }
        result = _shape_trend_response(response)
        assert len(result["series"]) == 1
        assert result["series"][0]["label"] == "$pageview"
        assert result["series"][0]["count"] == 100

    def test_with_breakdown(self):
        response = {
            "response_json": {
                "results": [
                    {
                        "label": "$pageview - Chrome",
                        "count": 60,
                        "labels": ["Mon"],
                        "data": [60],
                        "breakdown_value": "Chrome",
                    },
                    {
                        "label": "$pageview - Firefox",
                        "count": 40,
                        "labels": ["Mon"],
                        "data": [40],
                        "breakdown_value": "Firefox",
                    },
                ]
            }
        }
        result = _shape_trend_response(response)
        assert len(result["series"]) == 2
        assert result["series"][0]["breakdown_value"] == "Chrome"

    def test_missing_response_json(self):
        response = {"other": "data"}
        result = _shape_trend_response(response)
        assert result == response


class TestShapeFunnelResponse:
    def test_flat_funnel(self):
        response = {
            "response_json": {
                "results": [
                    {
                        "action_id": "step1",
                        "name": "Page View",
                        "count": 1000,
                        "conversionRates": {"total": 1.0},
                        "order": 0,
                    },
                    {
                        "action_id": "step2",
                        "name": "Sign Up",
                        "count": 200,
                        "conversionRates": {"total": 0.2},
                        "order": 1,
                    },
                ]
            }
        }
        result = _shape_funnel_response(response)
        assert len(result["steps"]) == 2
        assert result["steps"][0]["name"] == "Page View"
        assert result["steps"][1]["conversion_rate"] == 0.2

    def test_breakdown_funnel(self):
        response = {
            "response_json": {
                "results": [
                    [
                        {
                            "name": "Step 1",
                            "count": 100,
                            "conversionRates": {"total": 1.0},
                            "breakdown_value": "organic",
                            "order": 0,
                        },
                        {
                            "name": "Step 2",
                            "count": 50,
                            "conversionRates": {"total": 0.5},
                            "breakdown_value": "organic",
                            "order": 1,
                        },
                    ]
                ]
            }
        }
        result = _shape_funnel_response(response)
        assert "groups" in result
        assert result["groups"][0]["breakdown_value"] == "organic"


class TestShapeRetentionResponse:
    def test_cohort_rows(self):
        response = {
            "response_json": {
                "results": [
                    {
                        "date": "2025-01-01",
                        "label": "Week 0",
                        "values": [{"count": 100}, {"count": 50}, {"count": 25}],
                    },
                ]
            }
        }
        result = _shape_retention_response(response)
        assert len(result["cohorts"]) == 1
        assert result["cohorts"][0]["people_count"] == 100
        assert result["cohorts"][0]["values"] == [100, 50, 25]


class TestUrlHelpers:
    def test_posthog_ui_url(self, tool_context):
        url = _posthog_ui_url(tool_context, "dashboards")
        assert url == "https://us.posthog.com/project/12345/dashboards"

    def test_attach_url(self, tool_context):
        result = {"data": "value"}
        _attach_url(result, tool_context, "dashboard/1")
        assert "posthog_url" in result
        assert "dashboard/1" in result["posthog_url"]


class TestGetProjectId:
    def test_from_context(self, tool_context):
        assert _get_project_id(tool_context) == "12345"

    def test_missing_raises(self):
        context = MagicMock()
        context.get_secret = MagicMock(side_effect=Exception("not found"))
        with pytest.raises(ValueError, match="POSTHOG_PROJECT_ID is required"):
            _get_project_id(context)


class TestParameterAliases:
    def test_dashboard_id_aliases(self):
        assert "dashboard_id" in PARAMETER_ALIASES
        assert "dashboard_identifier" in PARAMETER_ALIASES["dashboard_id"]

    def test_project_id_aliases(self):
        assert "project_id" in PARAMETER_ALIASES
        assert "posthog_project_id" in PARAMETER_ALIASES["project_id"]

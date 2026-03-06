"""Shared helpers, exceptions, and constants for arcade_posthog tools."""

from __future__ import annotations

import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Sequence

import httpx
from arcade_mcp_server import Context
from dotenv import load_dotenv

# Import PosthogApi tools from Arcade's posthog_api toolkit
try:
    from arcade_posthog_api.tools import (
        ToolMode,
        create_dashboard as _api_create_dashboard,
        create_dashboard_collaborator as _api_create_dashboard_collaborator,
        create_experiment_in_project as _api_create_experiment,
        create_insight_entry as _api_create_insight,
        create_survey as _api_create_survey,
        delete_dashboard as _api_delete_dashboard,
        delete_experiment as _api_delete_experiment,
        delete_insight as _api_delete_insight,
        delete_survey as _api_delete_survey,
        get_available_dashboards as _api_list_dashboards,
        get_current_org_projects as _api_list_projects,
        get_dashboard_details as _api_get_dashboard,
        get_error_tracking_fingerprint as _api_get_error,
        get_organization_details as _api_get_org_details,
        get_project_experiment_details as _api_get_experiment,
        get_project_surveys as _api_list_surveys,
        get_survey_response_statistics as _api_get_survey_stats,
        get_survey_statistics as _api_get_all_survey_stats,
        list_error_tracking_fingerprints as _api_list_errors,
        list_feature_flags as _api_list_feature_flags,
        list_organizations as _api_list_organizations,
        list_posthog_experiments as _api_list_experiments,
        list_project_insights as _api_list_insights,
        list_property_definitions as _api_list_properties,
        mark_feature_flag_deleted as _api_delete_feature_flag,
        retrieve_draft_sql_query as _api_get_draft_sql,
        retrieve_event_definitions as _api_list_event_definitions,
        retrieve_experiment_timeseries as _api_get_experiment_results,
        retrieve_feature_flags as _api_get_feature_flag,
        retrieve_insight_data as _api_get_insight,
        retrieve_survey_data as _api_get_survey,
        update_dashboard as _api_update_dashboard,
        update_experiment as _api_update_experiment,
        update_feature_flags as _api_update_feature_flag,
        update_insights as _api_update_insight,
        update_survey_info as _api_update_survey,
    )
    from arcade_posthog_api.tools import (
        create_feature_flag as _api_create_feature_flag,
    )
except ImportError as e:
    raise ImportError(
        f"Could not import arcade_posthog_api.tools: {e}\n"
        "Install with: pip install arcade-posthog-api"
    ) from e

LOGGER = logging.getLogger(__name__)

# Required secrets for PostHog tools
POSTHOG_SECRETS = ["POSTHOG_PROJECT_ID", "POSTHOG_SERVER_URL", "POSTHOG_PERSONAL_API_KEY"]


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------

def _load_environment() -> None:
    """Load environment variables from a .env file located next to the package."""
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def _get_project_id(context: Context) -> str:
    """Get project ID from context secrets."""
    try:
        return context.get_secret("POSTHOG_PROJECT_ID")
    except Exception:
        project_id = os.getenv("POSTHOG_PROJECT_ID") or os.getenv("PROJECT_ID")
        if project_id:
            return project_id
        raise ValueError(
            "POSTHOG_PROJECT_ID is required. "
            "Set it as an environment variable or in MCP secrets."
        )


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------

class PostHogParameterError(RuntimeError):
    """Raised when wrapper parameters cannot be mapped to the underlying toolkit signature."""


class PostHogConfigurationError(RuntimeError):
    """Raised when required PostHog configuration is missing."""


class PostHogResponseError(RuntimeError):
    """Raised when a PostHog API response does not contain the expected JSON payload."""


class FeatureFlagResolutionError(RuntimeError):
    """Raised when a feature flag cannot be resolved by key."""


# ---------------------------------------------------------------------------
# Error classification (Pattern: Error Classification)
# ---------------------------------------------------------------------------

def _classify_error(exc: Exception) -> dict[str, Any]:
    """Return a structured error dict that tells the agent whether to retry."""
    msg = str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return {"error": f"Request timed out: {msg}", "retryable": True, "error_type": "timeout"}
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 429:
            return {"error": f"Rate limited: {msg}", "retryable": True, "error_type": "rate_limit"}
        if code in (401, 403):
            return {"error": f"Authentication failed (HTTP {code}): {msg}", "retryable": False, "error_type": "auth"}
        if code == 404:
            return {"error": f"Resource not found (HTTP 404): {msg}", "retryable": False, "error_type": "not_found"}
        if code >= 500:
            return {"error": f"PostHog server error (HTTP {code}): {msg}", "retryable": True, "error_type": "server"}
        return {"error": f"HTTP {code}: {msg}", "retryable": False, "error_type": "client"}
    if isinstance(exc, httpx.HTTPError):
        return {"error": f"Network error: {msg}", "retryable": True, "error_type": "network"}
    return {"error": msg, "retryable": False, "error_type": "unknown"}


# ---------------------------------------------------------------------------
# GUI URL builder (Pattern: GUI URL)
# ---------------------------------------------------------------------------

def _posthog_ui_url(context: Context, path: str) -> str:
    """Build a PostHog web-UI URL for the given resource path."""
    try:
        base = context.get_secret("POSTHOG_SERVER_URL").rstrip("/")
    except Exception:
        base = "https://us.posthog.com"
    project_id = _get_project_id(context)
    return f"{base}/project/{project_id}/{path}"


def _attach_url(result: dict[str, Any], context: Context, path: str) -> dict[str, Any]:
    """Inject a 'posthog_url' key into a result dict."""
    try:
        result["posthog_url"] = _posthog_ui_url(context, path)
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Response shaping (Pattern: Response Shaper / Token-Efficient Response)
# ---------------------------------------------------------------------------

def _shape_list_response(
    response: dict[str, Any],
    summary_keys: Sequence[str],
) -> dict[str, Any]:
    """Trim a list response to only the summary_keys per item (Progressive Detail)."""
    payload = response.get("response_json")
    if not isinstance(payload, dict):
        return response
    results = payload.get("results")
    if not isinstance(results, list):
        return response
    shaped = []
    for item in results:
        if isinstance(item, dict):
            shaped.append({k: item[k] for k in summary_keys if k in item})
    return {
        "count": payload.get("count", len(shaped)),
        "results": shaped,
        "next": payload.get("next"),
    }


def _shape_trend_response(response: dict[str, Any]) -> dict[str, Any]:
    """Flatten a TrendsQuery response to essential data."""
    payload = response.get("response_json")
    if not isinstance(payload, dict):
        return response
    raw_results = payload.get("results", [])
    series_list = []
    for series in raw_results:
        if not isinstance(series, dict):
            continue
        entry: dict[str, Any] = {
            "label": series.get("label"),
            "count": series.get("count") or series.get("aggregated_value"),
            "labels": series.get("labels"),
            "data": series.get("data"),
        }
        if series.get("breakdown_value") is not None:
            entry["breakdown_value"] = series["breakdown_value"]
        series_list.append(entry)
    return {"series": series_list}


def _shape_funnel_response(response: dict[str, Any]) -> dict[str, Any]:
    """Flatten a FunnelsQuery response to step-level conversion data."""
    payload = response.get("response_json")
    if not isinstance(payload, dict):
        return response
    raw_results = payload.get("results", [])
    if raw_results and isinstance(raw_results[0], dict) and "action_id" in raw_results[0]:
        steps = []
        for step in raw_results:
            steps.append({
                "name": step.get("name") or step.get("custom_name"),
                "count": step.get("count"),
                "conversion_rate": step.get("conversionRates", {}).get("total"),
                "average_time": step.get("average_conversion_time"),
                "order": step.get("order"),
            })
        return {"steps": steps}
    groups = []
    for group in raw_results:
        if isinstance(group, list):
            steps = []
            breakdown_val = None
            for step in group:
                if isinstance(step, dict):
                    if breakdown_val is None:
                        breakdown_val = step.get("breakdown_value")
                    steps.append({
                        "name": step.get("name") or step.get("custom_name"),
                        "count": step.get("count"),
                        "conversion_rate": step.get("conversionRates", {}).get("total"),
                        "order": step.get("order"),
                    })
            groups.append({"breakdown_value": breakdown_val, "steps": steps})
    return {"groups": groups} if groups else response


def _shape_retention_response(response: dict[str, Any]) -> dict[str, Any]:
    """Flatten a RetentionQuery response to cohort rows."""
    payload = response.get("response_json")
    if not isinstance(payload, dict):
        return response
    raw_results = payload.get("results", [])
    cohorts = []
    for row in raw_results:
        if not isinstance(row, dict):
            continue
        cohorts.append({
            "date": row.get("date"),
            "label": row.get("label"),
            "people_count": row.get("values", [{}])[0].get("count") if row.get("values") else None,
            "values": [v.get("count") for v in row.get("values", []) if isinstance(v, dict)],
        })
    return {"cohorts": cohorts}


# ---------------------------------------------------------------------------
# Natural identifier resolution (Pattern: Natural Identifier)
# ---------------------------------------------------------------------------

async def _resolve_entity_by_name(
    list_fn: Callable[..., Awaitable[dict[str, Any]]],
    context: Context,
    name: str,
    *,
    entity_label: str = "entity",
    extra_kwargs: dict[str, Any] | None = None,
) -> int | None:
    """Search a list endpoint for an entity matching *name* and return its numeric id."""
    kwargs: dict[str, Any] = {"project_id": _get_project_id(context)}
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    response = await _call_tool(list_fn, context, **kwargs)
    payload = response.get("response_json")
    if not isinstance(payload, dict):
        return None
    for item in payload.get("results", []):
        if isinstance(item, dict) and str(item.get("name", "")).lower() == name.lower():
            eid = item.get("id")
            if isinstance(eid, int):
                return eid
    return None


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------

PARAMETER_ALIASES: dict[str, tuple[str, ...]] = {
    "dashboard_id": (
        "dashboard_id",
        "dashboard_identifier",
        "dashboard_identification_number",
    ),
    "flag_id": ("feature_flag_id", "flag_id"),
    "flag_key": ("feature_flag_key", "flag_key"),
    "insight_id": ("insight_id", "insight_identifier"),
    "issue_id": ("issue_id", "error_tracking_fingerprint_uuid"),
    "limit": (
        "limit",
        "results_per_page",
        "page_result_limit",
        "results_limit_per_page",
        "results_limit",
        "results_per_page",
    ),
    "offset": (
        "offset",
        "start_index_for_results",
        "start_index",
        "results_offset",
        "results_offset_index",
        "initial_index_for_results",
        "initial_result_index",
        "results_start_index",
        "result_start_index",
    ),
    "project_id": (
        "project_id",
        "project_identifier",
        "project_unique_identifier",
        "project_id_for_experiment_creation",
        "project_identifier_for_access",
        "project_id_for_access",
        "project_id_to_access",
        "project_id_for_creation",
        "posthog_project_id",
    ),
    "survey_id": ("survey_id", "survey_uuid"),
}

OPTIONAL_PARAMETER_NAMES: set[str] = {
    "date_from",
    "date_to",
    "favorited",
    "filter_test_accounts",
    "order_by",
    "order_direction",
    "pinned",
    "refresh",
    "saved",
    "search",
    "status",
}


def _resolve_parameter_name(
    signature: inspect.Signature,
    supplied_key: str,
    alias_map: Mapping[str, Sequence[str]],
) -> str:
    if supplied_key in signature.parameters:
        return supplied_key

    for alias in alias_map.get(supplied_key, ()):
        if alias in signature.parameters:
            return alias

    available = ", ".join(signature.parameters.keys())
    message = (
        f"Unable to map parameter '{supplied_key}' to "
        f"{signature} (available: {available})"
    )
    LOGGER.error(message)
    raise PostHogParameterError(message)


async def _call_tool(
    tool_fn: Callable[..., Awaitable[dict[str, Any]]],
    context: Context,
    *,
    alias_overrides: Mapping[str, Sequence[str]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    signature = inspect.signature(tool_fn)
    alias_map: dict[str, tuple[str, ...]] = dict(PARAMETER_ALIASES)
    if alias_overrides:
        alias_map.update({key: tuple(value) for key, value in alias_overrides.items()})

    resolved_kwargs: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        try:
            target_key = _resolve_parameter_name(signature, key, alias_map)
        except PostHogParameterError:
            if key in OPTIONAL_PARAMETER_NAMES:
                LOGGER.debug(
                    "Skipping unsupported optional parameter '%s' for tool '%s'",
                    key,
                    tool_fn.__name__,
                )
                continue
            raise

        resolved_kwargs[target_key] = value

    return await tool_fn(context, **resolved_kwargs)


def _coerce_response_json(response: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the JSON payload from a PostHog tool response."""
    payload = response.get("response_json")
    if isinstance(payload, dict):
        return payload

    LOGGER.error("PostHog response missing JSON payload: %s", response)
    raise PostHogResponseError("PostHog API response missing JSON payload")


async def _resolve_feature_flag_id(
    context: Context,
    project_id: str,
    flag_key: str,
) -> int:
    """Resolve a feature flag key to its numeric identifier."""
    response = await _call_tool(
        _api_list_feature_flags,
        context,
        project_id=project_id,
        feature_flag_search_term=flag_key,
        limit=200,
    )

    payload = response.get("response_json")
    if not isinstance(payload, dict):
        LOGGER.error("Unexpected feature flag list payload: %s", response)
        raise FeatureFlagResolutionError(f"Could not resolve feature flag '{flag_key}'")

    results = payload.get("results", [])
    for item in results:
        if isinstance(item, dict) and item.get("key") == flag_key:
            identifier = item.get("id")
            if isinstance(identifier, int):
                return identifier

    LOGGER.error("Feature flag '%s' not found in project '%s'", flag_key, project_id)
    raise FeatureFlagResolutionError(f"Feature flag '{flag_key}' not found")


async def _run_posthog_query(context: Context, query: dict[str, Any]) -> dict[str, Any]:
    """Execute a query against the PostHog Query API."""
    project_id = _get_project_id(context)

    try:
        base_url = context.get_secret("POSTHOG_SERVER_URL").rstrip("/")
        api_key = context.get_secret("POSTHOG_PERSONAL_API_KEY")
    except Exception:  # noqa: BLE001
        return {"error": "POSTHOG_SERVER_URL and POSTHOG_PERSONAL_API_KEY secrets are required.", "retryable": False, "error_type": "auth"}

    url = f"{base_url}/api/projects/{project_id}/query/"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=query, headers=headers)
            response.raise_for_status()
    except Exception as exc:
        LOGGER.error("Failed to execute PostHog query: %s", exc)
        return _classify_error(exc)

    return {"response_json": response.json()}

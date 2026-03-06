"""Event, property, and documentation discovery tools."""

import json
import logging
from typing import Annotated, Any, Literal

import httpx
from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    PostHogResponseError,
    _api_list_event_definitions,
    _api_list_properties,
    _call_tool,
    _classify_error,
    _coerce_response_json,
    _get_project_id,
    _posthog_ui_url,
    _shape_list_response,
)

LOGGER = logging.getLogger(__name__)


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_event_definitions(
    context: Context,
    search: Annotated[str | None, "Filter events by name (case-insensitive substring match, e.g., 'purchase')"] = None,
) -> dict[str, Any]:
    """List all tracked event names in the project. This is the discovery starting point — call it first to find valid event names, then call list_properties(event_name=...) to explore an event's properties for filtering and breakdowns."""
    project_id = _get_project_id(context)

    response = await _call_tool(
        _api_list_event_definitions,
        context,
        project_id=project_id,
    )

    if search is not None:
        try:
            payload = _coerce_response_json(response)
        except PostHogResponseError:
            return response

        results = payload.get("results")
        if isinstance(results, list):
            filtered_results: list[dict[str, Any]] = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", ""))
                if search.lower() in name.lower():
                    filtered_results.append(item)
            payload["results"] = filtered_results
            payload["count"] = len(filtered_results)

    # Shape to essentials: name, volume, query_usage_30_day, last_seen_at
    result = _shape_list_response(response, ["name", "volume_30_day", "query_usage_30_day", "last_seen_at"])
    result["posthog_url"] = _posthog_ui_url(context, "data-management/events")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_properties(
    context: Context,
    event_name: Annotated[str | None, "Event name to get properties for (required when type is 'event'). Use list_event_definitions to find valid names."] = None,
    type: Annotated[Literal["event", "person"] | None, "Property type: 'event' (requires event_name) or 'person'."] = None,
) -> dict[str, Any]:
    """List property definitions with their names, types, and example values. Schema Explorer step 2: call list_event_definitions first to find an event, then call this with event_name to discover its properties for use in filters and breakdowns."""
    project_id = _get_project_id(context)

    kwargs: dict[str, Any] = {"project_id": project_id}
    if event_name is not None:
        kwargs["event_names_json"] = json.dumps([event_name])
        kwargs["filter_properties_by_event_names"] = True
    if type is not None:
        kwargs["property_definition_type"] = type

    response = await _call_tool(
        _api_list_properties,
        context,
        **kwargs,
    )
    result = _shape_list_response(response, ["name", "property_type", "is_numerical"])
    result["posthog_url"] = _posthog_ui_url(context, "data-management/properties")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def search_docs(
    context: Context,
    query: Annotated[str, "Search query (e.g., 'python feature flags', 'react surveys', 'hogql date functions')"],
) -> dict[str, Any]:
    """Search PostHog documentation. This is the fallback tool — use it when the specialized analytics tools (get_trend, get_funnel, etc.) return unexpected results, when you need HogQL syntax help, or to find SDK integration guides after creating feature flags/surveys/experiments."""
    async with httpx.AsyncClient() as client:
        url = "https://posthog.com/docs/api/search"
        try:
            response = await client.get(url, params={"q": query}, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            LOGGER.error("PostHog docs search failed: %s", exc)
            return _classify_error(exc)

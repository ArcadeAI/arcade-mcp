"""Insight management tools."""

import json
from typing import Annotated, Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    PostHogResponseError,
    ToolMode,
    _api_create_insight,
    _api_delete_insight,
    _api_get_insight,
    _api_list_insights,
    _api_update_insight,
    _attach_url,
    _call_tool,
    _coerce_response_json,
    _get_project_id,
    _posthog_ui_url,
    _resolve_entity_by_name,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_insight_from_query(
    context: Context,
    query_id: Annotated[str, "Query ID from a previous run_query result"],
    name: Annotated[str, "Display name for the saved insight (e.g., 'Weekly Active Users')"],
    description: Annotated[str | None, "What this insight measures"] = None,
) -> dict[str, Any]:
    """Save a tested query as a reusable insight. Always call run_query or a convenience tool first to verify the query works before creating an insight."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {"query_id": query_id, "name": name}
    if description is not None:
        data["description"] = description

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_insight,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=request_body,
    )
    payload = result.get("response_json", {})
    if isinstance(payload, dict) and payload.get("id"):
        _attach_url(result, context, f"insights/{payload['id']}")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def delete_insight(
    context: Context,
    insight_id: Annotated[int, "Numeric insight ID to delete"],
) -> dict[str, Any]:
    """Soft-delete an insight by ID."""
    project_id = _get_project_id(context)

    return await _call_tool(
        _api_delete_insight,
        context,
        insight_id=insight_id,
        project_id=project_id,
    )


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_insight(
    context: Context,
    insight_id: Annotated[int | None, "Numeric insight ID (from list_insights)"] = None,
    insight_name: Annotated[str | None, "Insight name (case-insensitive exact match). Resolved via list_insights."] = None,
) -> dict[str, Any]:
    """Get an insight's full configuration and current query results. Provide insight_id or insight_name. Call this before update_insight to see the current query structure."""
    resolved_id = insight_id
    if resolved_id is None and insight_name is not None:
        resolved_id = await _resolve_entity_by_name(_api_list_insights, context, insight_name, entity_label="insight")
    if resolved_id is None:
        return {"error": "Provide insight_id or insight_name. Could not resolve insight.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_insight,
        context,
        insight_id=resolved_id,
        project_id=project_id,
    )
    return _attach_url(result, context, f"insights/{resolved_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_insights(
    context: Context,
    search: Annotated[str | None, "Filter insights by name (case-insensitive substring match)"] = None,
) -> dict[str, Any]:
    """List all saved insights. Returns summaries (id, name, description, last_modified_at). Use get_insight for full configuration and query results."""
    project_id = _get_project_id(context)

    response = await _call_tool(
        _api_list_insights,
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

    result = _shape_list_response(response, ["id", "name", "description", "last_modified_at"])
    result["posthog_url"] = _posthog_ui_url(context, "insights")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def update_insight(
    context: Context,
    insight_id: Annotated[int, "Numeric insight ID to update"],
    name: Annotated[str | None, "New insight name"] = None,
    description: Annotated[str | None, "New insight description"] = None,
    filters: Annotated[dict[str, Any] | None, "New query filters (overwrites existing). Call get_insight first to see current structure."] = None,
) -> dict[str, Any]:
    """Update an insight's name, description, or query filters. Call get_insight first to see the current query structure and only modify the parts you need to change."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if filters is not None:
        data["filters"] = filters

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_update_insight,
        context,
        mode=ToolMode.EXECUTE,
        insight_id=insight_id,
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"insights/{insight_id}")

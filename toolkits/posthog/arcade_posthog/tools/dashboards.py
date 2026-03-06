"""Dashboard management tools."""

import json
from typing import Annotated, Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    PostHogResponseError,
    ToolMode,
    _api_create_dashboard,
    _api_create_dashboard_collaborator,
    _api_delete_dashboard,
    _api_get_dashboard,
    _api_list_dashboards,
    _api_update_dashboard,
    _attach_url,
    _call_tool,
    _coerce_response_json,
    _get_project_id,
    _posthog_ui_url,
    _resolve_entity_by_name,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def add_insight_to_dashboard(
    context: Context,
    insight_id: Annotated[str, "Numeric insight ID to add (e.g., '42')"],
    dashboard_id: Annotated[int, "Numeric dashboard ID to add the insight to (e.g., 7)"],
) -> dict[str, Any]:
    """Pin an existing insight as a tile on a dashboard. Get the insight_id from list_insights and the dashboard_id from list_dashboards."""
    project_id = _get_project_id(context)

    data = {"insightId": insight_id, "dashboardId": dashboard_id}
    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_dashboard_collaborator,
        context,
        mode=ToolMode.EXECUTE,
        dashboard_id=dashboard_id,
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"dashboard/{dashboard_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_dashboard(
    context: Context,
    name: Annotated[str, "Dashboard name (e.g., 'Weekly KPIs')"],
    description: Annotated[str | None, "What this dashboard tracks"] = None,
    pinned: Annotated[bool | None, "Pin to the top of the dashboards list"] = None,
    tags: Annotated[list[str] | None, "Tags for organization (e.g., ['marketing', 'q1'])"] = None,
) -> dict[str, Any]:
    """Create a new empty dashboard. Add insights to it afterward with add_insight_to_dashboard."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {"name": name}
    if description is not None:
        data["description"] = description
    if pinned is not None:
        data["pinned"] = pinned
    if tags is not None:
        data["tags"] = tags

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_dashboard,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=request_body,
    )
    # Attach URL using the newly created dashboard's id
    payload = result.get("response_json", {})
    if isinstance(payload, dict) and payload.get("id"):
        _attach_url(result, context, f"dashboard/{payload['id']}")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def delete_dashboard(
    context: Context,
    dashboard_id: Annotated[int, "Numeric dashboard ID to delete"],
) -> dict[str, Any]:
    """Soft-delete a dashboard by ID. The dashboard is marked as deleted but can be restored."""
    project_id = _get_project_id(context)

    return await _call_tool(
        _api_delete_dashboard,
        context,
        dashboard_id=dashboard_id,
        project_id=project_id,
    )


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_dashboard(
    context: Context,
    dashboard_id: Annotated[int | None, "Numeric dashboard ID to retrieve"] = None,
    dashboard_name: Annotated[str | None, "Dashboard name (case-insensitive exact match). Resolved via list_dashboards."] = None,
) -> dict[str, Any]:
    """Get a dashboard's full configuration including all insight tiles. Provide dashboard_id or dashboard_name."""
    resolved_id = dashboard_id
    if resolved_id is None and dashboard_name is not None:
        resolved_id = await _resolve_entity_by_name(_api_list_dashboards, context, dashboard_name, entity_label="dashboard")
    if resolved_id is None:
        return {"error": "Provide dashboard_id or dashboard_name. Could not resolve dashboard.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_dashboard,
        context,
        dashboard_id=resolved_id,
        project_id=project_id,
    )
    return _attach_url(result, context, f"dashboard/{resolved_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_dashboards(
    context: Context,
    limit: Annotated[int | None, "Max results to return (default 100)"] = None,
    offset: Annotated[int | None, "Number of results to skip for pagination"] = None,
    search: Annotated[str | None, "Filter dashboards by name (case-insensitive substring match)"] = None,
    pinned: Annotated[bool | None, "Filter to only pinned (true) or unpinned (false) dashboards"] = None,
) -> dict[str, Any]:
    """List all dashboards in the project. Returns summaries (id, name, pinned, tags, created_at). Use get_dashboard for full detail."""
    project_id = _get_project_id(context)

    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if search is not None:
        params["search"] = search
    if pinned is not None:
        params["pinned"] = pinned

    response = await _call_tool(
        _api_list_dashboards,
        context,
        project_id=project_id,
        **params,
    )

    if search is not None or pinned is not None:
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
                if search is not None:
                    name = str(item.get("name", ""))
                    if search.lower() not in name.lower():
                        continue
                if pinned is not None and bool(item.get("pinned")) is not pinned:
                    continue
                filtered_results.append(item)
            payload["results"] = filtered_results
            payload["count"] = len(filtered_results)

    result = _shape_list_response(response, ["id", "name", "pinned", "tags", "created_at"])
    result["posthog_url"] = _posthog_ui_url(context, "dashboards")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def update_dashboard(
    context: Context,
    dashboard_id: Annotated[int, "Numeric dashboard ID to update"],
    name: Annotated[str | None, "New dashboard name"] = None,
    description: Annotated[str | None, "New dashboard description"] = None,
    pinned: Annotated[bool | None, "Pin or unpin the dashboard"] = None,
    tags: Annotated[list[str] | None, "Replace tags (e.g., ['marketing', 'q1'])"] = None,
) -> dict[str, Any]:
    """Update a dashboard's name, description, pinned status, or tags. Call get_dashboard first to see current values."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if pinned is not None:
        data["pinned"] = pinned
    if tags is not None:
        data["tags"] = tags

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_update_dashboard,
        context,
        mode=ToolMode.EXECUTE,
        dashboard_id=dashboard_id,
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"dashboard/{dashboard_id}")

"""Feature flag management tools."""

import json
from typing import Annotated, Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    ToolMode,
    _api_create_feature_flag,
    _api_delete_feature_flag,
    _api_get_feature_flag,
    _api_list_feature_flags,
    _api_update_feature_flag,
    _attach_url,
    _call_tool,
    _get_project_id,
    _posthog_ui_url,
    _resolve_feature_flag_id,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_feature_flag(
    context: Context,
    key: Annotated[str, "Unique flag key using lowercase letters, numbers, hyphens, and underscores (e.g., 'new-checkout-flow')"],
    name: Annotated[str | None, "Human-readable display name"] = None,
    description: Annotated[str | None, "What this flag controls and why"] = None,
    active: Annotated[bool | None, "Whether the flag is active (default true)"] = None,
    filters: Annotated[dict[str, Any] | None, "Rollout and targeting rules. Example: {'groups': [{'rollout_percentage': 50}]}"] = None,
) -> dict[str, Any]:
    """Create a new feature flag. Call list_feature_flags first to avoid duplicate keys. After creation, use search_docs to find PostHog SDK documentation for the user's language/framework."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {"key": key}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if active is not None:
        data["active"] = active
    if filters is not None:
        data["filters"] = filters

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_feature_flag,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=request_body,
    )
    payload = result.get("response_json", {})
    if isinstance(payload, dict) and payload.get("id"):
        _attach_url(result, context, f"feature_flags/{payload['id']}")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def delete_feature_flag(
    context: Context,
    flag_id: Annotated[int | None, "Numeric flag ID (from list_feature_flags)"] = None,
    flag_key: Annotated[str | None, "Flag key string (e.g., 'new-checkout-flow')"] = None,
) -> dict[str, Any]:
    """Soft-delete a feature flag by numeric ID or key. Provide one of flag_id or flag_key."""
    if flag_id is None and flag_key is None:
        return {"error": "Either flag_id or flag_key must be provided.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    target_flag_id = flag_id
    if target_flag_id is None and flag_key is not None:
        target_flag_id = await _resolve_feature_flag_id(context, project_id, flag_key)

    if target_flag_id is None:
        return {"error": "Unable to resolve feature flag identifier.", "retryable": False, "error_type": "not_found"}

    return await _call_tool(
        _api_delete_feature_flag,
        context,
        flag_id=target_flag_id,
        project_id=project_id,
    )


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_feature_flags(
    context: Context,
) -> dict[str, Any]:
    """List all feature flags. Returns summaries (id, key, name, active). Use get_feature_flag for full rollout rules and targeting detail."""
    project_id = _get_project_id(context)

    response = await _call_tool(
        _api_list_feature_flags,
        context,
        project_id=project_id,
    )
    result = _shape_list_response(response, ["id", "key", "name", "active", "created_at"])
    result["posthog_url"] = _posthog_ui_url(context, "feature_flags")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_feature_flag(
    context: Context,
    flag_id: Annotated[int | None, "Numeric flag ID (from list_feature_flags)"] = None,
    flag_key: Annotated[str | None, "Flag key string (e.g., 'new-checkout-flow')"] = None,
) -> dict[str, Any]:
    """Get a feature flag's full definition including rollout rules and targeting. Provide one of flag_id or flag_key."""
    if flag_id is None and flag_key is None:
        return {"error": "Either flag_id or flag_key must be provided.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    target_flag_id = flag_id
    if target_flag_id is None and flag_key is not None:
        target_flag_id = await _resolve_feature_flag_id(context, project_id, flag_key)

    if target_flag_id is None:
        return {"error": "Unable to resolve feature flag identifier.", "retryable": False, "error_type": "not_found"}

    result = await _call_tool(
        _api_get_feature_flag,
        context,
        flag_id=target_flag_id,
        project_id=project_id,
    )
    return _attach_url(result, context, f"feature_flags/{target_flag_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def update_feature_flag(
    context: Context,
    flag_id: Annotated[int | None, "Numeric flag ID (from list_feature_flags)"] = None,
    flag_key: Annotated[str | None, "Flag key string (e.g., 'new-checkout-flow')"] = None,
    name: Annotated[str | None, "New display name"] = None,
    description: Annotated[str | None, "New description"] = None,
    active: Annotated[bool | None, "Set active (true) or inactive (false)"] = None,
    filters: Annotated[dict[str, Any] | None, "New rollout/targeting rules. To enable: set active=true with rollout_percentage=100. To disable: set active=false."] = None,
) -> dict[str, Any]:
    """Update a feature flag's properties or rollout rules. Provide one of flag_id or flag_key. Call get_feature_flag first to see current state. To enable: set active=true and rollout_percentage=100. To disable: set active=false."""
    if flag_id is None and flag_key is None:
        return {"error": "Either flag_id or flag_key must be provided.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    data: dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if active is not None:
        data["active"] = active
    if filters is not None:
        data["filters"] = filters

    request_body = json.dumps(data)

    target_flag_id = flag_id
    if target_flag_id is None and flag_key is not None:
        target_flag_id = await _resolve_feature_flag_id(context, project_id, flag_key)

    if target_flag_id is None:
        return {"error": "Unable to resolve feature flag identifier.", "retryable": False, "error_type": "not_found"}

    result = await _call_tool(
        _api_update_feature_flag,
        context,
        mode=ToolMode.EXECUTE,
        flag_id=target_flag_id,
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"feature_flags/{target_flag_id}")

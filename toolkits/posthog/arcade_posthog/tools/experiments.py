"""Experiment management tools."""

import json
from typing import Annotated, Any, Literal

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    ToolMode,
    _api_create_experiment,
    _api_create_feature_flag,
    _api_delete_experiment,
    _api_get_experiment,
    _api_get_experiment_results,
    _api_list_experiments,
    _api_update_experiment,
    _attach_url,
    _call_tool,
    _get_project_id,
    _posthog_ui_url,
    _resolve_entity_by_name,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_experiments(
    context: Context,
) -> dict[str, Any]:
    """List all A/B test experiments. Returns summaries (id, name, feature_flag_key, start_date, end_date). Use get_experiment for full configuration."""
    project_id = _get_project_id(context)

    response = await _call_tool(
        _api_list_experiments,
        context,
        project_id=project_id,
    )
    result = _shape_list_response(response, ["id", "name", "feature_flag_key", "start_date", "end_date", "created_at"])
    result["posthog_url"] = _posthog_ui_url(context, "experiments")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_experiment(
    context: Context,
    name: Annotated[str, "Experiment name describing the hypothesis (e.g., 'Checkout button color test')"],
    feature_flag_key: Annotated[str, "Feature flag key for this experiment. Lowercase letters, numbers, hyphens, underscores only (e.g., 'checkout-button-color')"],
    description: Annotated[str | None, "Detailed hypothesis and expected outcome"] = None,
    type: Annotated[Literal["product", "web"] | None, "Experiment type: 'product' (backend/API) or 'web' (frontend UI)."] = None,
    primary_metrics: Annotated[list[dict[str, Any]] | None, "Primary success metrics to measure. Use list_event_definitions to find valid event names."] = None,
    secondary_metrics: Annotated[list[dict[str, Any]] | None, "Secondary metrics to monitor for side effects"] = None,
    variants: Annotated[list[dict[str, Any]] | None, "Variant definitions (default: 50/50 control/test)"] = None,
    draft: Annotated[bool | None, "Create as draft (true) or launch immediately (false)"] = None,
) -> dict[str, Any]:
    """Create an A/B test experiment. Workflow: 1) Call list_feature_flags to check for existing flags. 2) Call list_event_definitions to find events for metrics. 3) Create the experiment."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {"name": name, "feature_flag_key": feature_flag_key}
    if description is not None:
        data["description"] = description
    if type is not None:
        data["type"] = type
    if primary_metrics is not None:
        data["primary_metrics"] = primary_metrics
    if secondary_metrics is not None:
        data["secondary_metrics"] = secondary_metrics
    if variants is not None:
        data["variants"] = variants
    if draft is not None:
        data["draft"] = draft

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_experiment,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=request_body,
    )
    payload = result.get("response_json", {})
    if isinstance(payload, dict) and payload.get("id"):
        _attach_url(result, context, f"experiments/{payload['id']}")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def delete_experiment(
    context: Context,
    experiment_id: Annotated[int, "Numeric experiment ID to delete"],
) -> dict[str, Any]:
    """Delete an experiment by ID."""
    project_id = _get_project_id(context)

    return await _call_tool(
        _api_delete_experiment,
        context,
        experiment_id=experiment_id,
        project_id=project_id,
    )


@tool(requires_secrets=POSTHOG_SECRETS)
async def update_experiment(
    context: Context,
    experiment_id: Annotated[int, "Numeric experiment ID to update"],
    name: Annotated[str | None, "New experiment name"] = None,
    description: Annotated[str | None, "New experiment description"] = None,
    primary_metrics: Annotated[list[dict[str, Any]] | None, "Replace primary metrics. Use list_event_definitions to find valid event names."] = None,
    secondary_metrics: Annotated[list[dict[str, Any]] | None, "Replace secondary metrics"] = None,
    launch: Annotated[bool | None, "Set true to launch a draft experiment"] = None,
    conclude: Annotated[str | None, "Conclusion result string to end the experiment"] = None,
    restart: Annotated[bool | None, "Set true to restart a concluded experiment"] = None,
) -> dict[str, Any]:
    """Update an experiment's properties or lifecycle state. Call get_experiment first to see current state. To launch: set launch=true. To conclude: set conclude='winning_variant_name'. To restart: set restart=true."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if primary_metrics is not None:
        data["primary_metrics"] = primary_metrics
    if secondary_metrics is not None:
        data["secondary_metrics"] = secondary_metrics
    if launch is not None:
        data["launch"] = launch
    if conclude is not None:
        data["conclude"] = conclude
    if restart is not None:
        data["restart"] = restart

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_update_experiment,
        context,
        mode=ToolMode.EXECUTE,
        experiment_id=experiment_id,
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"experiments/{experiment_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_experiment(
    context: Context,
    experiment_id: Annotated[int | None, "Numeric experiment ID (from list_experiments)"] = None,
    experiment_name: Annotated[str | None, "Experiment name (case-insensitive exact match). Resolved via list_experiments."] = None,
) -> dict[str, Any]:
    """Get an experiment's full configuration including variants, metrics, and current status. Provide experiment_id or experiment_name."""
    resolved_id = experiment_id
    if resolved_id is None and experiment_name is not None:
        resolved_id = await _resolve_entity_by_name(_api_list_experiments, context, experiment_name, entity_label="experiment")
    if resolved_id is None:
        return {"error": "Provide experiment_id or experiment_name. Could not resolve experiment.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_experiment,
        context,
        experiment_id=resolved_id,
        project_id=project_id,
    )
    return _attach_url(result, context, f"experiments/{resolved_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_experiment_results(
    context: Context,
    experiment_id: Annotated[int, "Numeric experiment ID to get results for"],
) -> dict[str, Any]:
    """Get experiment results including primary/secondary metric data and exposure counts. Only works with new-style experiments (not legacy). Call get_experiment first to verify the experiment exists."""
    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_experiment_results,
        context,
        experiment_id=experiment_id,
        project_id=project_id,
    )
    return _attach_url(result, context, f"experiments/{experiment_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_experiment_with_flag(
    context: Context,
    name: Annotated[str, "Experiment name describing the hypothesis (e.g., 'Checkout button color test')"],
    feature_flag_key: Annotated[str, "Feature flag key. Lowercase letters, numbers, hyphens, underscores only (e.g., 'checkout-button-color')"],
    description: Annotated[str | None, "Detailed hypothesis and expected outcome"] = None,
    type: Annotated[Literal["product", "web"] | None, "Experiment type: 'product' (backend/API) or 'web' (frontend UI)."] = None,
    primary_metrics: Annotated[list[dict[str, Any]] | None, "Primary success metrics. Use list_event_definitions to find valid event names."] = None,
    secondary_metrics: Annotated[list[dict[str, Any]] | None, "Secondary metrics to monitor for side effects"] = None,
    rollout_percentage: Annotated[int, "Percentage of users who see the experiment (0-100). Default 100."] = 100,
    draft: Annotated[bool | None, "Create as draft (true) or launch immediately (false). Default true."] = True,
) -> dict[str, Any]:
    """Create a feature flag AND an experiment in one step. This bundles the two operations that always go together — no need to call create_feature_flag separately. The flag is created with the specified rollout_percentage, then the experiment is linked to it."""
    project_id = _get_project_id(context)

    # Step 1: Create the feature flag
    flag_data: dict[str, Any] = {
        "key": feature_flag_key,
        "name": f"Experiment: {name}",
        "filters": {"groups": [{"rollout_percentage": rollout_percentage}]},
    }
    flag_result = await _call_tool(
        _api_create_feature_flag,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=json.dumps(flag_data),
    )
    flag_payload = flag_result.get("response_json", {})
    if isinstance(flag_payload, dict) and flag_payload.get("detail"):
        return {"error": f"Failed to create feature flag: {flag_payload['detail']}", "retryable": False, "error_type": "client"}

    # Step 2: Create the experiment linked to the flag
    exp_data: dict[str, Any] = {"name": name, "feature_flag_key": feature_flag_key}
    if description is not None:
        exp_data["description"] = description
    if type is not None:
        exp_data["type"] = type
    if primary_metrics is not None:
        exp_data["primary_metrics"] = primary_metrics
    if secondary_metrics is not None:
        exp_data["secondary_metrics"] = secondary_metrics
    if draft is not None:
        exp_data["draft"] = draft

    exp_result = await _call_tool(
        _api_create_experiment,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=json.dumps(exp_data),
    )

    exp_payload = exp_result.get("response_json", {})
    result: dict[str, Any] = {
        "feature_flag": {
            "id": flag_payload.get("id") if isinstance(flag_payload, dict) else None,
            "key": feature_flag_key,
        },
        "experiment": {
            "id": exp_payload.get("id") if isinstance(exp_payload, dict) else None,
            "name": name,
        },
    }
    if isinstance(exp_payload, dict) and exp_payload.get("id"):
        _attach_url(result, context, f"experiments/{exp_payload['id']}")
    return result

"""Survey management tools."""

import json
from typing import Annotated, Any, Literal

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    ToolMode,
    _api_create_survey,
    _api_delete_survey,
    _api_get_all_survey_stats,
    _api_get_survey,
    _api_get_survey_stats,
    _api_list_surveys,
    _api_update_survey,
    _attach_url,
    _call_tool,
    _get_project_id,
    _posthog_ui_url,
    _resolve_entity_by_name,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def create_survey(
    context: Context,
    name: Annotated[str, "Survey name (e.g., 'Onboarding NPS Q1')"],
    description: Annotated[str | None, "Internal description of the survey's purpose"] = None,
    type: Annotated[Literal["popover", "api", "widget", "button"] | None, "Survey type: 'popover' (in-app modal), 'api' (headless), 'widget' (embedded), 'button' (trigger-based)."] = None,
    questions: Annotated[list[dict[str, Any]] | None, "List of question objects. Each needs 'type' ('open', 'multiple_choice', 'rating', 'link') and 'question' (text)."] = None,
) -> dict[str, Any]:
    """Create a new survey. Call list_surveys first to avoid duplicates. After creation, use search_docs to find SDK documentation for adding the survey to the user's application."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {"name": name}
    if description is not None:
        data["description"] = description
    if type is not None:
        data["type"] = type
    if questions is not None:
        data["questions"] = questions

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_create_survey,
        context,
        mode=ToolMode.EXECUTE,
        project_id=project_id,
        request_body=request_body,
    )
    payload = result.get("response_json", {})
    if isinstance(payload, dict) and payload.get("id"):
        _attach_url(result, context, f"surveys/{payload['id']}")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_survey(
    context: Context,
    survey_id: Annotated[int | None, "Numeric survey ID (from list_surveys)"] = None,
    survey_name: Annotated[str | None, "Survey name (case-insensitive exact match). Resolved via list_surveys."] = None,
) -> dict[str, Any]:
    """Get a survey's full configuration including questions, targeting rules, and scheduling. Provide survey_id or survey_name."""
    resolved_id = survey_id
    if resolved_id is None and survey_name is not None:
        resolved_id = await _resolve_entity_by_name(_api_list_surveys, context, survey_name, entity_label="survey")
    if resolved_id is None:
        return {"error": "Provide survey_id or survey_name. Could not resolve survey.", "retryable": False, "error_type": "client"}

    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_survey,
        context,
        survey_id=str(resolved_id),
        project_id=project_id,
    )
    return _attach_url(result, context, f"surveys/{resolved_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_surveys(
    context: Context,
    search: Annotated[str | None, "Filter surveys by name (case-insensitive substring match)"] = None,
    limit: Annotated[int | None, "Max results to return"] = None,
    offset: Annotated[int | None, "Number of results to skip for pagination"] = None,
) -> dict[str, Any]:
    """List all surveys. Returns summaries (id, name, type, created_at). Use get_survey for full configuration."""
    project_id = _get_project_id(context)

    params: dict[str, Any] = {}
    if search is not None:
        params["search"] = search
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = await _call_tool(
        _api_list_surveys,
        context,
        project_id=project_id,
        **params,
    )
    result = _shape_list_response(response, ["id", "name", "type", "created_at", "start_date", "end_date"])
    result["posthog_url"] = _posthog_ui_url(context, "surveys")
    return result


@tool(requires_secrets=POSTHOG_SECRETS)
async def update_survey(
    context: Context,
    survey_id: Annotated[int, "Numeric survey ID to update"],
    name: Annotated[str | None, "New survey name"] = None,
    description: Annotated[str | None, "New survey description"] = None,
    questions: Annotated[list[dict[str, Any]] | None, "Replacement question list (overwrites existing questions)"] = None,
) -> dict[str, Any]:
    """Update a survey's name, description, or questions. Call get_survey first to see current configuration."""
    project_id = _get_project_id(context)

    data: dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if questions is not None:
        data["questions"] = questions

    request_body = json.dumps(data)

    result = await _call_tool(
        _api_update_survey,
        context,
        mode=ToolMode.EXECUTE,
        survey_id=str(survey_id),
        project_id=project_id,
        request_body=request_body,
    )
    return _attach_url(result, context, f"surveys/{survey_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def delete_survey(
    context: Context,
    survey_id: Annotated[int, "Numeric survey ID to delete"],
) -> dict[str, Any]:
    """Soft-delete a survey by ID (marks as archived)."""
    project_id = _get_project_id(context)

    return await _call_tool(
        _api_delete_survey,
        context,
        survey_id=str(survey_id),
        project_id=project_id,
    )


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_survey_stats(
    context: Context,
    survey_id: Annotated[int, "Numeric survey ID to get statistics for"],
) -> dict[str, Any]:
    """Get response statistics for a survey: event counts (shown, dismissed, sent), unique respondents, and conversion rates."""
    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_survey_stats,
        context,
        project_id=project_id,
        survey_id=str(survey_id),
    )
    return _attach_url(result, context, f"surveys/{survey_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_all_survey_stats(
    context: Context,
) -> dict[str, Any]:
    """Get aggregated response statistics across all surveys: total shown, dismissed, sent, respondents, and conversion rates."""
    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_all_survey_stats,
        context,
        project_id=project_id,
    )
    result["posthog_url"] = _posthog_ui_url(context, "surveys")
    return result

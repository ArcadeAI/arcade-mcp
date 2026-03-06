"""Error tracking tools."""

from typing import Annotated, Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    _api_get_error,
    _api_list_errors,
    _attach_url,
    _call_tool,
    _get_project_id,
    _posthog_ui_url,
    _shape_list_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_error_details(
    context: Context,
    issue_id: Annotated[str, "Error fingerprint UUID (from list_errors)"],
) -> dict[str, Any]:
    """Get stack trace, occurrence count, and affected users/sessions for a specific error. Call list_errors first to find the fingerprint UUID."""
    project_id = _get_project_id(context)

    result = await _call_tool(
        _api_get_error,
        context,
        project_id=project_id,
        issue_id=issue_id,
    )
    return _attach_url(result, context, f"error_tracking/{issue_id}")


@tool(requires_secrets=POSTHOG_SECRETS)
async def list_errors(
    context: Context,
) -> dict[str, Any]:
    """List error tracking issues. Returns summaries (id, fingerprint, status, occurrences, users, first_seen, last_seen). Use get_error_details for full stack traces."""
    project_id = _get_project_id(context)

    response = await _call_tool(
        _api_list_errors,
        context,
        project_id=project_id,
    )
    result = _shape_list_response(response, ["id", "fingerprint", "status", "occurrences", "users", "first_seen", "last_seen"])
    result["posthog_url"] = _posthog_ui_url(context, "error_tracking")
    return result

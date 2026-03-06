"""Organization and project management tools."""

from typing import Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    _api_get_org_details,
    _api_list_organizations,
    _api_list_projects,
)


@tool
async def list_projects(
    context: Context,
) -> dict[str, Any]:
    """List all projects the user has access to in the current organization."""
    return await _api_list_projects(context)


@tool
async def list_organizations(
    context: Context,
) -> dict[str, Any]:
    """List all organizations the user belongs to."""
    return await _api_list_organizations(context)


@tool
async def get_organization_details(
    context: Context,
) -> dict[str, Any]:
    """Get the active organization's name, billing info, and member count."""
    return await _api_get_org_details(context)

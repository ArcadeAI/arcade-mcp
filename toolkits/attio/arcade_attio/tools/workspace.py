"""Attio workspace operations - members and context."""

from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_attio.tools.records import _attio_request


@tool(requires_secrets=["ATTIO_API_KEY"])
async def list_workspace_members(
    context: ToolContext,
) -> Annotated[dict, "All workspace members"]:
    """
    Get all members in the Attio workspace.

    Useful for task assignment and understanding who owns records.
    """
    response = await _attio_request("GET", "/workspace_members")

    members = []
    for m in response.get("data", []):
        members.append({
            "member_id": m.get("id", {}).get("workspace_member_id", ""),
            "name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
            "email": m.get("email_address", ""),
        })

    return {"members": members}

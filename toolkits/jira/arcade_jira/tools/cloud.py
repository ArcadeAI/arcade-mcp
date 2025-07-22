from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_available_atlassian_clouds(
    context: ToolContext,
) -> Annotated[dict[str, Any], "Available Atlassian Clouds"]:
    """Get available Atlassian Clouds."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {context.get_auth_token_or_empty()}"},
        )

    clouds = response.json()
    cloud_ids_seen = set()
    unique_clouds = []

    for cloud in clouds:
        if cloud["id"] not in cloud_ids_seen:
            unique_clouds.append({
                "id": cloud["id"],
                "name": cloud["name"],
                "url": cloud["url"],
            })
            cloud_ids_seen.add(cloud["id"])

    return {"clouds_available": unique_clouds}

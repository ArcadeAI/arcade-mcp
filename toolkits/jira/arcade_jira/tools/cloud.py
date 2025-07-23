import asyncio
from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.constants import JIRA_MAX_CONCURRENT_REQUESTS
from arcade_jira.utils import check_if_cloud_is_authorized


@tool(requires_auth=Atlassian(scopes=["read:jira-user"]))
async def get_available_atlassian_clouds(
    context: ToolContext,
) -> Annotated[dict[str, list[dict[str, str]]], "Available Atlassian Clouds"]:
    """Get available Atlassian Clouds."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {context.get_auth_token_or_empty()}"},
        )

    verified_clouds = response.json()
    cloud_ids_seen = set()
    unique_clouds = []

    for cloud in verified_clouds:
        if cloud["id"] not in cloud_ids_seen:
            unique_clouds.append({
                "atlassian_cloud_id": cloud["id"],
                "atlassian_cloud_name": cloud["name"],
                "atlassian_cloud_url": cloud["url"],
            })
            cloud_ids_seen.add(cloud["id"])

    semaphore = asyncio.Semaphore(JIRA_MAX_CONCURRENT_REQUESTS)

    verified_clouds = await asyncio.gather(*[
        check_if_cloud_is_authorized(context, cloud, semaphore) for cloud in unique_clouds
    ])

    return {
        "clouds_available": [
            cloud_available for cloud_available in verified_clouds if cloud_available is not False
        ]
    }

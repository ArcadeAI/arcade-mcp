from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_todoist.utils import get_headers, get_url, parse_projects


@tool(
    requires_auth=OAuth2(
        id="todoist",
        scopes=["data:read"],
    ),
)
async def get_projects(
    context: ToolContext,
) -> Annotated[dict, "The projects object returned by the Todoist API."]:
    """
    Get all projects from the Todoist API. Use this when the user wants to see, list, or browse
    their projects. Do NOT use this for creating tasks - use create_task instead even if a
    project name is mentioned.
    """

    async with httpx.AsyncClient() as client:
        url = get_url(context=context, endpoint="projects")
        headers = get_headers(context=context)

        response = await client.get(url, headers=headers)

        response.raise_for_status()

        projects = parse_projects(response.json()["results"])

        return {"projects": projects}

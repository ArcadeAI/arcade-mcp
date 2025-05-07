import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.constants import PROJECT_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import clean_request_params


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def get_project_by_id(
    context: ToolContext,
    project_id: Annotated[str, "The ID of the project."],
) -> Annotated[
    dict[str, Any],
    "Get a project by its ID",
]:
    """Get an Asana project by its ID"""
    client = AsanaClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"/projects/{project_id}",
        params={"opt_fields": PROJECT_OPT_FIELDS},
    )
    return {"project": response["data"]}


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def list_projects(
    context: ToolContext,
    team_ids: Annotated[
        list[str] | None,
        "The team IDs to get projects from. Multiple team IDs can be provided in the list. "
        "Defaults to None (get projects from all teams the user is a member of).",
    ] = None,
    limit: Annotated[
        int, "The maximum number of projects to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    offset: Annotated[int, "The offset of projects to return. Defaults to 0"] = 0,
) -> Annotated[
    dict[str, Any],
    "List projects in Asana associated to teams the current user is a member of",
]:
    """List projects in Asana"""
    # Note: Asana recommends filtering by team to avoid timeout in large domains.
    # Ref: https://developers.asana.com/reference/getprojects
    limit = max(1, min(100, limit))

    client = AsanaClient(context.get_auth_token_or_empty())

    if team_ids:
        from arcade_asana.tools.teams import get_team_by_id  # avoid circular imports

        responses = await asyncio.gather(*[
            get_team_by_id(context, team_id) for team_id in team_ids
        ])
        user_teams = {"teams": [response["data"] for response in responses]}

    else:
        # Avoid circular imports
        from arcade_asana.tools.teams import list_teams_the_current_user_is_a_member_of

        user_teams = await list_teams_the_current_user_is_a_member_of(context)

    responses = await asyncio.gather(*[
        client.get(
            "/projects",
            params=clean_request_params({
                "limit": limit,
                "offset": offset,
                "team": team["id"],
                "workspace": team["organization"]["id"],
                "opt_fields": PROJECT_OPT_FIELDS,
            }),
        )
        for team in user_teams["teams"]
    ])

    projects = [project for response in responses for project in response["data"]]

    return {
        "projects": projects,
        "count": len(projects),
    }

import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_asana.constants import PROJECT_OPT_FIELDS
from arcade_asana.models import AsanaClient
from arcade_asana.utils import clean_request_params, paginate_tool_call


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
async def search_projects_by_name(
    context: ToolContext,
    names: Annotated[list[str], "The names of the projects to search for."],
    team_ids: Annotated[
        list[str] | None,
        "The IDs of the teams to get projects from. "
        "Defaults to None (get projects from all teams the user is a member of).",
    ] = None,
    limit: Annotated[
        int, "The maximum number of projects to return. Min is 1, max is 100. Defaults to 100."
    ] = 100,
    return_projects_not_matched: Annotated[
        bool, "Whether to return projects that were not matched. Defaults to False."
    ] = False,
) -> Annotated[dict[str, Any], "Search for projects by name"]:
    """Search for projects by name"""
    names_lower = {name.casefold() for name in names}

    projects = await paginate_tool_call(
        tool=list_projects,
        context=context,
        response_key="projects",
        max_items=500,
        timeout_seconds=15,
        team_ids=team_ids,
    )

    matches: list[dict[str, Any]] = []
    not_matched: list[str] = []

    for project in projects:
        project_name_lower = project["name"].casefold()
        if len(matches) >= limit:
            break
        if project_name_lower in names_lower:
            matches.append(project)
            names_lower.remove(project_name_lower)
        else:
            not_matched.append(project)

    not_found = [name for name in names if name.casefold() in names_lower]

    response = {
        "matches": {
            "projects": matches,
            "count": len(matches),
        },
        "not_found": {
            "names": not_found,
            "count": len(not_found),
        },
    }

    if return_projects_not_matched:
        response["not_matched"] = {
            "projects": not_matched,
            "count": len(not_matched),
        }

    return response


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["default"]))
async def list_projects(
    context: ToolContext,
    team_ids: Annotated[
        list[str] | None,
        "The IDs of the teams to get projects from. "
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
                "team": team["gid"],
                "workspace": team["organization"]["gid"],
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

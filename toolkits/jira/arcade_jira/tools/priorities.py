import asyncio
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.constants import JIRA_API_REQUEST_TIMEOUT, PrioritySchemeOrderBy
from arcade_jira.exceptions import MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    clean_priority_dict,
    clean_priority_scheme_dict,
    clean_project_dict,
    find_unique_project,
    paginate_all_priorities_by_priority_scheme,
    paginate_all_priority_schemes,
    remove_none_values,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_priority_by_id(
    context: ToolContext,
    priority_id: Annotated[str, "The ID of the priority to retrieve."],
) -> Annotated[dict[str, Any], "The priority"]:
    """Get the details of a priority by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        response = await client.get(f"/priority/{priority_id}")
    except NotFoundError:
        return {"error": f"Priority not found with id '{priority_id}'"}
    return {"priority": clean_priority_dict(response)}


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priority_schemes(
    context: ToolContext,
    scheme_name: Annotated[
        str | None, "Filter by scheme name. Defaults to None (returns all scheme names)."
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of priority schemes to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of priority schemes to skip. Defaults to 0 (start from the first scheme)."
    ] = 0,
    order_by: Annotated[
        PrioritySchemeOrderBy,
        "The order in which to return the priority schemes. Defaults to name ascending.",
    ] = PrioritySchemeOrderBy.NAME_ASCENDING,
) -> Annotated[dict[str, Any], "The priority schemes available"]:
    """Browse the priority schemes available in Jira."""
    limit = max(min(limit, 50), 1)
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        "/priorityscheme",
        params=remove_none_values({
            "startAt": offset,
            "maxResults": limit,
            "schemeName": scheme_name,
            "orderBy": order_by.to_api_value(),
        }),
    )
    schemes = [clean_priority_scheme_dict(scheme) for scheme in api_response["values"]]
    response = {
        "priority_schemes": schemes,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, schemes, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_associated_with_a_priority_scheme(
    context: ToolContext,
    scheme_id: Annotated[str, "The ID of the priority scheme to retrieve priorities for."],
    limit: Annotated[
        int,
        "The maximum number of priority schemes to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of priority schemes to skip. Defaults to 0 (start from the first scheme)."
    ] = 0,
) -> Annotated[dict[str, Any], "The priorities associated with the priority scheme"]:
    """Browse the priorities associated with a priority scheme."""
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        f"/priorityscheme/{scheme_id}/priorities",
        params={
            "startAt": offset,
            "maxResults": limit,
        },
    )
    priorities = [clean_priority_dict(priority) for priority in api_response["values"]]
    response = {
        "priorities": priorities,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, priorities, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_projects_associated_with_a_priority_scheme(
    context: ToolContext,
    scheme_id: Annotated[str, "The ID of the priority scheme to retrieve projects for."],
    project: Annotated[
        str | None, "Filter by project ID, key or name. Defaults to None (returns all projects)."
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of projects to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int, "The number of projects to skip. Defaults to 0 (start from the first project)."
    ] = 0,
) -> Annotated[dict[str, Any], "The projects associated with the priority scheme"]:
    """Browse the projects associated with a priority scheme."""
    if project:
        try:
            project = await find_unique_project(context, project)
        except (NotFoundError, MultipleItemsFoundError) as exc:
            return {"error": exc.message}
        finally:
            project = project["id"]

    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        f"/priorityscheme/{scheme_id}/projects",
        params=remove_none_values({
            "startAt": offset,
            "maxResults": limit,
            "projectId": project,
        }),
    )
    projects = [clean_project_dict(project) for project in api_response["values"]]
    response = {
        "projects": projects,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, projects, limit, offset)


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_available_to_a_project(
    context: ToolContext,
    project: Annotated[str, "The ID, key or name of the project to retrieve priorities for."],
) -> Annotated[
    dict[str, Any],
    "The priorities available to be used in issues in the specified Jira project",
]:
    """Browse the priorities available to be used in issues in the specified Jira project.

    This tool may need to loop through several API calls to get all priorities associated with
    a specific project. In Jira environments with too many Projects or Priority Schemes,
    the search may take too long, and the tool call will timeout.
    """
    try:
        project = await find_unique_project(context, project)
    except (NotFoundError, MultipleItemsFoundError) as exc:
        return {"error": exc.message}

    scheme_ids: set[str] = set()
    priority_ids: set[str] = set()
    priorities: list[dict[str, Any]] = []

    try:
        async with asyncio.timeout(JIRA_API_REQUEST_TIMEOUT):
            import json

            priority_schemes = await paginate_all_priority_schemes(context)
            projects_by_scheme = await asyncio.gather(*[
                list_projects_associated_with_a_priority_scheme(
                    context=context,
                    scheme_id=scheme["id"],
                    project=project["id"],
                )
                for scheme in priority_schemes
            ])
            print("\n\n\nprojects_by_scheme: ", json.dumps(projects_by_scheme, indent=2), "\n\n\n")

            for scheme_index, scheme_projects in enumerate(projects_by_scheme):
                if scheme_projects.get("error"):
                    return scheme_projects

                for scheme_project in scheme_projects["projects"]:
                    if scheme_project["id"] == project["id"]:
                        scheme = priority_schemes[scheme_index]
                        scheme_ids.add(scheme["id"])
                        break

            priorities_by_scheme = await asyncio.gather(*[
                paginate_all_priorities_by_priority_scheme(context, scheme_id)
                for scheme_id in scheme_ids
            ])

            for priorities_available in priorities_by_scheme:
                for priority in priorities_available:
                    if priority["id"] in priority_ids:
                        continue
                    priority_ids.add(priority["id"])
                    priorities.append(priority)

        return {
            "project": {
                "id": project["id"],
                "key": project["key"],
                "name": project["name"],
            },
            "priorities_available": priorities,
        }

    except asyncio.TimeoutError:
        return {"error": f"The search timed out after {JIRA_API_REQUEST_TIMEOUT} seconds."}


@tool(requires_auth=Atlassian(scopes=["manage:jira-configuration"]))
async def list_priorities_available_to_an_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID, key or name of the issue to retrieve priorities for."],
) -> Annotated[dict[str, Any], "The priorities available to be used in the specified Jira issue"]:
    """Browse the priorities available to be used in the specified Jira issue."""
    from arcade_jira.tools.issues import get_issue_by_id

    issue = await get_issue_by_id(context, issue)
    if issue.get("error"):
        return issue

    response = await list_priorities_available_to_a_project(context, issue["project"]["id"])

    return {
        "issue": {
            "id": issue["id"],
            "key": issue["key"],
            "name": issue["fields"]["summary"],
        },
        "priorities_available": response["priorities_available"],
    }

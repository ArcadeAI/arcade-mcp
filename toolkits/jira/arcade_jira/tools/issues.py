from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.constants import IssuePriority, IssueStatus
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    build_adf_doc_from_plaintext,
    build_search_issues_jql,
    clean_issue_dict,
    clean_issue_type_dict,
    convert_date_string_to_date,
    remove_none_values,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_issue_types(
    context: ToolContext,
    project: Annotated[
        str | None,
        "The project to get issue types for. Provide a project name, key, or ID. "
        "Defaults to None (all projects).",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of issue types to retrieve. Min 1, max 200, default 200.",
    ] = 200,
    offset: Annotated[
        int,
        "The number of issue types to skip. Defaults to 0 (start from the first issue type).",
    ] = 0,
) -> Annotated[
    dict[str, Any], "Information about the issue types available for the specified project."
]:
    """Get the list of issue types (e.g. 'Task', 'Epic', etc.) available to a given project."""
    # Avoid circular import
    from arcade_jira.tools.projects import get_project_by_id, search_projects

    client = JiraClient(context.get_auth_token_or_empty())

    project_id: str = ""
    project = await get_project_by_id(context, project)

    if not project.get("project"):
        projects = await search_projects(context, project)
        if len(projects["total"]) == 0:
            return {"error": f"Project not found with ID/key/name '{project}'."}
        elif len(projects["total"]) > 1:
            return {
                "error": (
                    f"Multiple projects found with ID/key/name '{project}'. "
                    "Please provide a specific project ID."
                ),
                "matching_projects": projects["projects"],
            }
        else:
            project_id = projects["projects"][0]["id"]

    api_response = await client.get(
        f"/issue/createmeta/{project_id}/issuetypes",
        params={
            "maxResults": limit,
            "startAt": offset,
        },
    )
    issue_types = [clean_issue_type_dict(issue_type) for issue_type in api_response["issueTypes"]]
    response = {
        "issue_types": issue_types,
        "count": len(issue_types),
    }
    return add_pagination_to_response(response, issue_types, limit, offset)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_type_by_id(
    context: ToolContext,
    issue_type: Annotated[str, "The ID or key of the issue type to retrieve"],
) -> Annotated[dict, "Information about the issue type"]:
    """Get the details of a Jira issue type by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    response = await client.get(f"issuetype/{issue_type}")
    return {"issue_type": clean_issue_type_dict(response)}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_by_id(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve"],
) -> Annotated[dict, "Information about the issue"]:
    """Get the details of a Jira issue by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        issue = await client.get(
            f"issue/{issue}",
            params={"expand": "renderedFields"},
        )
    except NotFoundError:
        return {"error": f"Issue not found with ID/key '{issue}'."}
    return {"issue": clean_issue_dict(issue)}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issues_without_id(
    context: ToolContext,
    keywords: Annotated[
        str | None,
        "Keywords to search for issues. Matches against the issue "
        "name, description, comments, and any custom field of type text. "
        "Defaults to None (no keywords filtering).",
    ] = None,
    due_from: Annotated[
        str | None,
        "Match issues due on or after this date. Format: YYYY-MM-DD. Ex: '2025-01-01'. "
        "Defaults to None (no due date filtering).",
    ] = None,
    due_until: Annotated[
        str | None,
        "Match issues due on or before this date. Format: YYYY-MM-DD. Ex: '2025-01-01'. "
        "Defaults to None (no due date filtering).",
    ] = None,
    status: Annotated[
        IssueStatus | None,
        "Match issues that are in this status. Ex: 'To Do'. Defaults to None (any status).",
    ] = None,
    priority: Annotated[
        IssuePriority | None,
        "Match issues that have this priority. Ex: 'Highest'. Defaults to None (any priority).",
    ] = None,
    assignee: Annotated[
        str | None,
        "Match issues that are assigned to this user. "
        "Provide the user's display name or email address. "
        "Ex: 'John Doe' or 'john.doe@example.com'. Defaults to None (any assignee).",
    ] = None,
    project: Annotated[
        str | None,
        "Match issues that are associated with this project. "
        "Provide the project's name, ID, or key. "
        "Defaults to None (any project or no project).",
    ] = None,
    issue_type: Annotated[
        str | None,
        "Match issues that are of this issue type. Provide an issue type name or ID. "
        "E.g. 'Task', 'Epic', '10000'. To get a full list of available issue types, use the "
        f"`Jira.{list_issue_types.__tool_name__}` tool. Defaults to None (any issue type).",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "Match issues that are in these labels. Defaults to None (any label).",
    ] = None,
    parent_issue: Annotated[
        str | None,
        "Match issues that are a child of this issue. Provide the issue's ID or key. "
        "Defaults to None (no parent issue filtering).",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of issues to retrieve. Min 1, max 100, default 50.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "The token to use to get the next page of issues. Defaults to None (first page).",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the issues matching the search criteria"]:
    """Search for Jira issues when you don't have the issue ID(s).

    All text-based arguments (keywords, assignee, project, labels) are case-insensitive.
    """
    limit = max(1, min(limit, 100))

    client = JiraClient(context.get_auth_token_or_empty())

    due_from = convert_date_string_to_date(due_from) if due_from else None
    due_until = convert_date_string_to_date(due_until) if due_until else None

    jql = build_search_issues_jql(
        keywords=keywords,
        due_from=due_from,
        due_until=due_until,
        status=status,
        priority=priority,
        assignee=assignee,
        project=project,
        issue_type=issue_type,
        labels=labels,
        parent_issue=parent_issue,
    )
    body = {
        "jql": jql,
        "maxResults": limit,
        "nextPageToken": next_page_token,
        "fields": ["*all"],
        "expand": "renderedFields",
    }
    response = await client.post("search/jql", json_data=body)

    return {
        "issues": [clean_issue_dict(issue) for issue in response["issues"]],
        "count": len(response["issues"]),
        "next_page_token": response.get("nextPageToken"),
    }


@tool(requires_auth=Atlassian(scopes=["write:jira-work"]))
async def create_issue(
    context: ToolContext,
    title: Annotated[
        str,
        "The title of the issue.",
    ],
    project_id: Annotated[
        str,
        "The ID of the project to associate the issue with.",
    ],
    issue_type_id: Annotated[
        str,
        "The ID of the issue type. To get a full list of available "
        f"issue types, use the `Jira.{list_issue_types.__tool_name__}` tool. ",
    ],
    due_date: Annotated[
        str | None,
        "The due date of the issue. Format: YYYY-MM-DD. Ex: '2025-01-01'. "
        "Defaults to None (no due date).",
    ] = None,
    description: Annotated[
        str | None,
        "The description of the issue. Defaults to None (no description).",
    ] = None,
    environment: Annotated[
        str | None,
        "The environment of the issue. Defaults to None (no environment).",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "The labels of the issue. Defaults to None (no labels).",
    ] = None,
    parent_issue_id: Annotated[
        str | None,
        "The ID of the parent issue. Defaults to None (no parent issue).",
    ] = None,
    priority_id: Annotated[
        str | None,
        "The ID of the issue priority. Defaults to None "
        "(Jira's default priority set in the user's account).",
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to assign the issue to. Defaults to None (no assignee).",
    ] = None,
    reporter_id: Annotated[
        str | None,
        "The ID of the user who is the reporter of the issue. Defaults to None (no reporter).",
    ] = None,
) -> Annotated[dict, "The created issue"]:
    """Create a new Jira issue."""
    client = JiraClient(context.get_auth_token_or_empty())

    request_body = {
        "fields": remove_none_values({
            "summary": title,
            "labels": labels,
            "duedate": due_date,
            "issuetype": {"id": issue_type_id} if issue_type_id else None,
            "parent": {"id": parent_issue_id} if parent_issue_id else None,
            "project": {"id": project_id} if project_id else None,
            "priority": {"id": priority_id} if priority_id else None,
            "assignee": {"id": assignee_id} if assignee_id else None,
            "reporter": {"id": reporter_id} if reporter_id else None,
        }),
    }

    if environment:
        request_body["fields"]["environment"] = build_adf_doc_from_plaintext(environment)

    if description:
        request_body["fields"]["description"] = build_adf_doc_from_plaintext(description)

    response = await client.post("issue", json_data=request_body)

    return {
        "status": {
            "success": True,
            "message": "Issue successfully created.",
        },
        "issue": {
            "id": response["id"],
            "key": response["key"],
            "url": response["self"],
        },
    }

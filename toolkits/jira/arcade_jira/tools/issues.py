from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.constants import IssuePriority, IssueStatus
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import (
    build_search_issues_jql,
    clean_issue_dict,
    clean_issue_type_dict,
    convert_date_string_to_date,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_issue_types(
    context: ToolContext,
) -> Annotated[dict[str, Any], "List of issue types"]:
    """Get the list of issue types (e.g. 'Task', 'Epic', etc.) available to the current user."""
    client = JiraClient(context.get_auth_token_or_empty())
    response = await client.get("issuetype")
    return {"issue_types": [clean_issue_type_dict(issue_type) for issue_type in response]}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_by_id(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve"],
) -> Annotated[dict, "Information about the issue"]:
    """Get the details of a Jira issue by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        issue = await client.get(f"issue/{issue}")
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
        "Ex: 'Task', 'Epic', '10000'. To get a full list of available issue types, use the "
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

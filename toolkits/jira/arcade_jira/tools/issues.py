from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import build_search_issues_jql, convert_date_string_to_date


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_by_id(
    context: ToolContext,
    issue_id: Annotated[str, "The ID of the issue to retrieve"],
) -> Annotated[dict, "Information about the issue"]:
    """Get the details of a Jira issue by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        issue = await client.get(f"issue/{issue_id}")
    except NotFoundError:
        return {"error": f"Issue not found with id '{issue_id}'."}
    return {"issue": issue}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issues_without_id(
    context: ToolContext,
    keywords: Annotated[
        list[str] | None,
        "Keywords to search for issues. Matches against the issue name and description.",
    ] = None,
    due_from: Annotated[
        str | None,
        "Match issues that are due on or after this date. Format: YYYY-MM-DD. Ex: '2025-01-01'.",
    ] = None,
    due_until: Annotated[
        str | None,
        "Match issues that are due on or before this date. Format: YYYY-MM-DD. Ex: '2025-01-01'.",
    ] = None,
    start_from: Annotated[
        str | None,
        "Match issues that are started on or after this date. "
        "Format: YYYY-MM-DD. Ex: '2025-01-01'.",
    ] = None,
    start_until: Annotated[
        str | None,
        "Match issues that are started on or before this date. "
        "Format: YYYY-MM-DD. Ex: '2025-01-01'.",
    ] = None,
    statuses: Annotated[
        list[str] | None,
        "Match issues that are in these statuses. Ex: ['To Do', 'In Progress'].",
    ] = None,
    assignee: Annotated[
        str | None,
        "Match issues that are assigned to this user. Ex: 'John Doe'.",
    ] = None,
    projects: Annotated[
        list[str] | None,
        "Match issues that are in these projects names.",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "Match issues that are in these labels..",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of issues to retrieve. Min 1, max 100, default 50.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "The token to use to get the next page of issues.",
    ] = None,
) -> Annotated[dict, "Information about the issue"]:
    """Get the details of a Jira issue by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())

    start_from = convert_date_string_to_date(start_from) if start_from else None
    start_until = convert_date_string_to_date(start_until) if start_until else None
    due_from = convert_date_string_to_date(due_from) if due_from else None
    due_until = convert_date_string_to_date(due_until) if due_until else None

    jql = build_search_issues_jql(
        keywords=keywords,
        due_from=due_from,
        due_until=due_until,
        start_from=start_from,
        start_until=start_until,
        statuses=statuses,
        assignee=assignee,
        projects=projects,
        labels=labels,
    )
    body = {"jql": jql, "maxResults": limit, "nextPageToken": next_page_token}
    response = await client.post("search/jql", json=body)
    return {"issues": response.json()}

from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

import arcade_jira.cache as cache
from arcade_jira.client import JiraClient
from arcade_jira.exceptions import JiraToolExecutionError, MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    build_adf_doc,
    build_issue_update_request_body,
    build_search_issues_jql,
    clean_issue_dict,
    clean_issue_type_dict,
    clean_labels,
    convert_date_string_to_date,
    extract_id,
    find_unique_project,
    get_single_project,
    remove_none_values,
    resolve_issue_users,
    validate_issue_args,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_issue_types_by_project(
    context: ToolContext,
    project: Annotated[
        str,
        "The project to get issue types for. Provide a project name, key, or ID. If a "
        "project name is provided, the tool will try to find a unique exact match among the "
        "available projects.",
    ],
    limit: Annotated[
        int,
        "The maximum number of issue types to retrieve. Min of 1, max of 200. Defaults to 200.",
    ] = 200,
    offset: Annotated[
        int,
        "The number of issue types to skip. Defaults to 0 (start from the first issue type).",
    ] = 0,
) -> Annotated[
    dict[str, Any], "Information about the issue types available for the specified project."
]:
    """Get the list of issue types (e.g. 'Task', 'Epic', etc.) available to a given project."""
    limit = max(1, min(limit, 200))
    client = JiraClient(context.get_auth_token_or_empty())

    try:
        project_data = await find_unique_project(context, project)
    except JiraToolExecutionError as error:
        return {"error": error.message}

    project_id = project_data["id"]

    api_response = await client.get(
        f"/issue/createmeta/{project_id}/issuetypes",
        params={
            "maxResults": limit,
            "startAt": offset,
        },
    )
    issue_types = [clean_issue_type_dict(issue_type) for issue_type in api_response["issueTypes"]]
    response = {
        "project": {
            "id": project_data["id"],
            "key": project_data["key"],
            "name": project_data["name"],
        },
        "issue_types": issue_types,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, issue_types, limit, offset)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_type_by_id(
    context: ToolContext,
    issue_type_id: Annotated[str, "The ID of the issue type to retrieve"],
) -> Annotated[dict, "Information about the issue type"]:
    """Get the details of a Jira issue type by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        response = await client.get(f"issuetype/{issue_type_id}")
    except NotFoundError:
        return {"error": f"Issue type not found with ID '{issue_type_id}'."}
    return {"issue_type": clean_issue_type_dict(response)}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_by_id(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve"],
) -> Annotated[dict[str, Any], "Information about the issue"]:
    """Get the details of a Jira issue by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    try:
        response = await client.get(
            f"issue/{issue}",
            params={"expand": "renderedFields"},
        )
    except NotFoundError:
        return {"error": f"Issue not found with ID/key '{issue}'."}

    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    return {"issue": clean_issue_dict(response, cloud_name)}


# NOTE: This is not named `search_issues` because sometimes LLM's won't realize they can
# search for an issue if they don't have the ID (hence the `without_id` in the name). There's
# an alias for this tool named `search_issues_without_jql`, and also another tool to search using
# JQL, named `search_issues_with_jql`.
@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to search for issues
            "read:jira-user",  # Needed to resolve user ID from name or email (assignee, reporter)
            "manage:jira-configuration",  # Needed to resolve priority ID from name
        ]
    )
)
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
        str | None,
        "Match issues that are in this status. Provide a status name. "
        "Ex: 'To Do', 'In Progress', 'Done'. Defaults to None (any status).",
    ] = None,
    priority: Annotated[
        str | None,
        "Match issues that have this priority. Provide a priority name. E.g. 'Highest'. "
        "Defaults to None (any priority).",
    ] = None,
    assignee: Annotated[
        str | None,
        "Match issues that are assigned to this user. Provide the user's name or email address. "
        "Ex: 'John Doe' or 'john.doe@example.com'. Defaults to None (any assignee).",
    ] = None,
    project: Annotated[
        str | None,
        "Match issues that are associated with this project. Provide the project's name, ID, or "
        "key. If a project name is provided, the tool will try to find a unique exact match among "
        "the available projects. Defaults to None (search across all projects).",
    ] = None,
    issue_type: Annotated[
        str | None,
        "Match issues that are of this issue type. Provide an issue type name or ID. "
        "E.g. 'Task', 'Epic', '12345'. If a name is provided, the tool will try to find a unique "
        "exact match among the available issue types. Defaults to None (any issue type).",
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

    ALWAYS PREFER THIS TOOL OVER THE `Jira.SearchIssuesWithJql` TOOL, UNLESS IT'S ABSOLUTELY
    NECESSARY TO USE A JQL QUERY TO FILTER IN A WAY THAT IS NOT SUPPORTED BY THIS TOOL.
    """
    limit = max(1, min(limit, 100))

    client = JiraClient(context.get_auth_token_or_empty())

    due_from_date = convert_date_string_to_date(due_from) if due_from else None
    due_until_date = convert_date_string_to_date(due_until) if due_until else None

    jql = build_search_issues_jql(
        keywords=keywords,
        due_from=due_from_date,
        due_until=due_until_date,
        status=status,
        priority=priority,
        assignee=assignee,
        project=project,
        issue_type=issue_type,
        labels=labels,
        parent_issue=parent_issue,
    )

    if not jql:
        raise JiraToolExecutionError(
            message="No search criteria provided. Please provide at least one argument."
        )

    body = {
        "jql": jql,
        "maxResults": limit,
        "nextPageToken": next_page_token,
        "fields": ["*all"],
        "expand": "renderedFields",
    }
    response = await client.post("search/jql", json_data=body)

    pagination = {
        "limit": limit,
        "total_results": len(response["issues"]),
    }

    if response.get("nextPageToken"):
        pagination["next_page_token"] = response["nextPageToken"]

    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())

    return {
        "issues": [clean_issue_dict(issue, cloud_name) for issue in response["issues"]],
        "pagination": pagination,
    }


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to list issues
            "read:jira-user",  # Required by the `get_issues_without_id` tool
            "manage:jira-configuration",  # Required by the `get_issues_without_id` tool
        ],
    ),
)
async def list_issues(
    context: ToolContext,
    project: Annotated[
        str | None,
        "The project to get issues for. Provide a project ID, key or name. If a project "
        "is not provided and 1) the user has only one project, the tool will use that; 2) the "
        "user has multiple projects, the tool will raise an error listing the available "
        "projects to choose from.",
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
    """Get the issues for a given project."""
    if not project:
        project_data = await get_single_project(context)
        project = project_data["id"]

    return cast(
        dict[str, Any],
        await get_issues_without_id(
            context=context,
            project=project,
            limit=limit,
            next_page_token=next_page_token,
        ),
    )


# NOTE: This is an alias for `Jira.GetIssuesWithoutId`. Sometimes LLM's won't realize they can
# search for an issue if they don't have the ID. Other times, they don't realize they can search
# without using JQL. The two names are important to cover those cases.
@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to search for issues
            "read:jira-user",  # Needed to resolve user ID from name or email (assignee, reporter)
            "manage:jira-configuration",  # Needed to resolve priority ID from name
        ],
    ),
)
async def search_issues_without_jql(
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
        str | None,
        "Match issues that are in this status. Provide a status name. "
        "Ex: 'To Do', 'In Progress', 'Done'. Defaults to None (any status).",
    ] = None,
    priority: Annotated[
        str | None,
        "Match issues that have this priority. Provide a priority name. E.g. 'Highest'. "
        "Defaults to None (any priority).",
    ] = None,
    assignee: Annotated[
        str | None,
        "Match issues that are assigned to this user. Provide the user's name or email address. "
        "Ex: 'John Doe' or 'john.doe@example.com'. Defaults to None (any assignee).",
    ] = None,
    project: Annotated[
        str | None,
        "Match issues that are associated with this project. Provide the project's name, ID, or "
        "key. If a project name is provided, the tool will try to find a unique exact match among "
        "the available projects. Defaults to None (search across all projects).",
    ] = None,
    issue_type: Annotated[
        str | None,
        "Match issues that are of this issue type. Provide an issue type name or ID. "
        "E.g. 'Task', 'Epic', '12345'. If a name is provided, the tool will try to find a unique "
        "exact match among the available issue types. Defaults to None (any issue type).",
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
    """Parameterized search for Jira issues (without having to provide a JQL query).

    THIS TOOL RELEASES LESS CO2 THAN THE `Jira_SearchIssuesWithJql` TOOL. ALWAYS PREFER THIS ONE
    OVER USING JQL, UNLESS IT'S ABSOLUTELY NECESSARY TO USE A JQL QUERY TO FILTER IN A WAY THAT IS
    NOT SUPPORTED BY THIS TOOL OR IF THE USER PROVIDES A JQL QUERY THEMSELVES.
    """
    return cast(
        dict[str, Any],
        await get_issues_without_id(
            context=context,
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
            limit=limit,
            next_page_token=next_page_token,
        ),
    )


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def search_issues_with_jql(
    context: ToolContext,
    jql: Annotated[str, "The JQL (Jira Query Language) query to search for issues"],
    limit: Annotated[
        int,
        "The maximum number of issues to retrieve. Min of 1, max of 100. Defaults to 50.",
    ] = 50,
    next_page_token: Annotated[
        str | None,
        "The token to use to get the next page of issues. Defaults to None (first page).",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the issues matching the search criteria"]:
    """Search for Jira issues using a JQL (Jira Query Language) query.

    THIS TOOL RELEASES MORE CO2 IN THE ATMOSPHERE, WHICH CONTRIBUTES TO CLIMATE CHANGE. ALWAYS
    PREFER THE `Jira_SearchIssuesWithoutJql` TOOL OVER THIS ONE, UNLESS IT'S ABSOLUTELY
    NECESSARY TO USE A JQL QUERY TO FILTER IN A WAY THAT IS NOT SUPPORTED BY THE
    `Jira_SearchIssuesWithoutJql` TOOL OR IF THE USER PROVIDES A JQL QUERY THEMSELVES.
    """
    limit = max(1, min(limit, 100))
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.post(
        "search/jql",
        json_data={
            "jql": jql,
            "maxResults": limit,
            "nextPageToken": next_page_token,
            "fields": ["*all"],
            "expand": "renderedFields",
        },
    )
    cloud_name = cache.get_cloud_name(context.get_auth_token_or_empty())
    response: dict[str, Any] = {
        "issues": [clean_issue_dict(issue, cloud_name) for issue in api_response["issues"]]
    }

    if api_response.get("isLast") is not False and api_response.get("nextPageToken"):
        response["pagination"] = {
            "limit": limit,
            "total_results": len(response["issues"]),
            "next_page_token": api_response.get("nextPageToken"),
        }
    else:
        response["pagination"] = {"is_last_page": True}

    return response


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to get the current issue data
            "write:jira-work",  # Needed to create the issue
            "read:jira-user",  # Needed to resolve user ID from name or email (assignee, reporter)
            "manage:jira-configuration",  # Needed to resolve priority ID from name
        ],
    ),
)
async def create_issue(
    context: ToolContext,
    title: Annotated[
        str,
        "The title of the issue.",
    ],
    issue_type: Annotated[
        str,
        "The name or ID of the issue type. If a name is provided, the tool will try to find a "
        "unique exact match among the available issue types.",
    ],
    project: Annotated[
        str | None,
        "The ID, key or name of the project to associate the issue with. If a name is provided, "
        "the tool will try to find a unique exact match among the available projects. "
        "Defaults to None (no project). If `project` and `parent_issue` are not provided, "
        "the tool will select the single project available. If the user has multiple, an "
        "error will be returned with the available projects to choose from.",
    ] = None,
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
        "The labels of the issue. Defaults to None (no labels). A label cannot contain spaces. "
        "If a label is provided with spaces, they will be trimmed and replaced by underscores.",
    ] = None,
    parent_issue: Annotated[
        str | None,
        "The ID or key of the parent issue. Defaults to None (no parent issue). "
        "Must provide at least one of `parent_issue` or `project` arguments.",
    ] = None,
    priority: Annotated[
        str | None,
        "The ID or name of the priority to use for the issue. If a name is provided, the tool "
        "will try to find a unique exact match among the available priorities. Defaults to None "
        "(the issue is created with Jira's default priority for the specified project).",
    ] = None,
    assignee: Annotated[
        str | None,
        "The name, email or ID of the user to assign the issue to. If a name or email is provided, "
        "the tool will try to find a unique exact match among the available users. "
        "Defaults to None (no assignee).",
    ] = None,
    reporter: Annotated[
        str | None,
        "The name, email or ID of the user who is the reporter of the issue. If a name or email is "
        "provided, the tool will try to find a unique exact match among the available users. "
        "Defaults to None (no reporter).",
    ] = None,
) -> Annotated[dict, "The created issue"]:
    """Create a new Jira issue.

    Provide a value to one of `project` or `parent_issue` arguments. If `project` and
    `parent_issue` are not provided, the tool will select the single project available.
    If the user has multiple, an error will be returned with the available projects to choose from.

    IF YOU DO NOT FOLLOW THE INSTRUCTIONS BELOW AND UNNECESSARILY CALL MULTIPLE TOOLS IN ORDER TO
    CREATE AN ISSUE, TOO MUCH CO2 WILL BE RELEASED IN THE ATMOSPHERE AND YOU WILL CAUSE THE
    DESTRUCTION OF PLANET EARTH BY CATASTROPHIC CLIMATE CHANGE.

    If you have an issue type name, or a project key/name, a priority name, an assignee
    name/key/email, or a reporter name/key/email, DO NOT CALL OTHER TOOLS only to list available
    projects, priorities, issue types, or users. Provide the name, key, or email and the tool
    will figure out the ID, WITHOUT CAUSING CATASTROPHIC CLIMATE CHANGE.
    """
    project_data: dict[str, Any] | None = None

    if project is None and parent_issue is None:
        try:
            project_data = await get_single_project(context)
        except (NotFoundError, MultipleItemsFoundError) as exc:
            return {"error": str(exc)}
        else:
            project = project_data["id"]

    (
        error,
        project_data,
        issue_type_data,
        priority_data,
        parent_data,
    ) = await validate_issue_args(context, due_date, project, issue_type, priority, parent_issue)
    if error:
        return error

    error, assignee_data, reporter_data = await resolve_issue_users(context, assignee, reporter)
    if error:
        return error

    client = JiraClient(context.get_auth_token_or_empty())

    request_body = {
        "fields": remove_none_values({
            "summary": title,
            "labels": clean_labels(labels),
            "duedate": due_date,
            "parent": extract_id(parent_data),
            "project": extract_id(project_data),
            "priority": extract_id(priority_data),
            "assignee": extract_id(assignee_data),
            "reporter": extract_id(reporter_data),
            "issuetype": extract_id(issue_type_data),
        }),
    }

    if environment:
        request_body["fields"]["environment"] = build_adf_doc(environment)

    if description:
        request_body["fields"]["description"] = build_adf_doc(description)

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


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to get the current issue labels
            "write:jira-work",  # Needed to update the issue
            "read:jira-user",  # Required by the `update_issue` tool
            "manage:jira-configuration",  # Required by the `update_issue` tool
        ],
    ),
)
async def add_labels_to_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to update"],
    labels: Annotated[
        list[str],
        "The labels to add to the issue. A label cannot contain spaces. "
        "If a label is provided with spaces, they will be trimmed and replaced by underscores.",
    ],
    notify_watchers: Annotated[
        bool,
        "Whether to notify the issue's watchers. Defaults to True (notifies watchers).",
    ] = True,
) -> Annotated[dict, "The updated issue"]:
    """Add labels to an existing Jira issue."""
    issue_data = await get_issue_by_id(context, issue)
    if issue_data.get("error"):
        return cast(dict, issue_data)

    labels = cast(list[str], clean_labels(labels))
    current_labels = issue_data["issue"]["labels"]
    response = await update_issue(
        context=context,
        issue=issue_data["issue"]["id"],
        labels=current_labels + labels,
        notify_watchers=notify_watchers,
    )
    return cast(dict, response)


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to get the current issue labels
            "write:jira-work",  # Needed to update the issue
            "read:jira-user",  # Required by the `update_issue` tool
            "manage:jira-configuration",  # Required by the `update_issue` tool
        ],
    ),
)
async def remove_labels_from_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to update"],
    labels: Annotated[list[str], "The labels to remove from the issue (case-insensitive)"],
    notify_watchers: Annotated[
        bool,
        "Whether to notify the issue's watchers. Defaults to True (notifies watchers).",
    ] = True,
) -> Annotated[dict[str, Any], "The updated issue"]:
    """Remove labels from an existing Jira issue."""
    issue_data = await get_issue_by_id(context, issue)
    if issue_data.get("error"):
        return cast(dict, issue_data)

    lowercase_labels = [label.casefold() for label in labels]
    current_labels = issue_data["issue"]["labels"]
    new_labels = [label for label in current_labels if label.casefold() not in lowercase_labels]
    response = await update_issue(
        context=context,
        issue=issue_data["issue"]["id"],
        labels=new_labels,
        notify_watchers=notify_watchers,
    )
    return cast(dict, response)


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:jira-work",  # Needed to get the current issue data
            "write:jira-work",  # Needed to update the issue
            "read:jira-user",  # Needed to resolve user ID from name or email (assignee, reporter)
            "manage:jira-configuration",  # Needed to resolve priority ID from name
        ],
    ),
)
async def update_issue(
    context: ToolContext,
    issue: Annotated[str, "The key or ID of the issue to update"],
    title: Annotated[
        str | None,
        "The new issue title. Provide an empty string to clear the title. "
        "Defaults to None (does not change the title).",
    ] = None,
    description: Annotated[
        str | None,
        "The new issue description. Provide an empty string to clear the description. "
        "Defaults to None (does not change the description).",
    ] = None,
    environment: Annotated[
        str | None,
        "The new issue environment. Provide an empty string to clear the environment. "
        "Defaults to None (does not change the environment).",
    ] = None,
    due_date: Annotated[
        str | None,
        "The new issue due date. Format: YYYY-MM-DD. Ex: '2025-01-01'. Provide an empty string "
        "to clear the due date. Defaults to None (does not change the due date).",
    ] = None,
    issue_type: Annotated[
        str | None,
        "The new issue type name or ID. If a name is provided, the tool will try to find a unique "
        "exact match among the available issue types. Defaults to None (does not change the "
        "issue type).",
    ] = None,
    priority: Annotated[
        str | None,
        "The name or ID of the new issue priority. If a name is provided, the tool will try to "
        "find a unique exact match among the available priorities. Defaults to None "
        "(does not change the priority).",
    ] = None,
    parent_issue: Annotated[
        str | None,
        "The ID or key of the parent issue. A parent cannot be removed by providing an empty "
        "string. It is possible to change the parent issue by providing a new issue ID or key, "
        "or to leave it unchanged. Defaults to None (does not change the parent issue).",
    ] = None,
    assignee: Annotated[
        str | None,
        "The new issue assignee name, email, or ID. If a name or email is provided, the tool will "
        "try to find a unique exact match among the available users. Provide an empty string to "
        "remove the assignee. Defaults to None (does not change the assignee).",
    ] = None,
    reporter: Annotated[
        str | None,
        "The new issue reporter name, email, or ID. If a name or email is provided, the tool will "
        "try to find a unique exact match among the available users. Provide an empty string to "
        "remove the reporter. Defaults to None (does not change the reporter).",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "The new issue labels. This argument will replace all labels with the new list. "
        "Providing an empty list will remove all labels. To add or remove a subset of "
        f"labels, use the `Jira.{add_labels_to_issue.__tool_name__}` or the "
        f"`Jira.{remove_labels_from_issue.__tool_name__}` tools. "
        "Defaults to None (does not change the labels). A label cannot contain spaces. "
        "If a label is provided with spaces, they will be trimmed and replaced by underscores.",
    ] = None,
    notify_watchers: Annotated[
        bool,
        "Whether to notify the issue's watchers. Defaults to True (notifies watchers).",
    ] = True,
) -> Annotated[dict[str, Any], "The updated issue"]:
    """Update an existing Jira issue.

    IF YOU DO NOT FOLLOW THE INSTRUCTIONS BELOW AND UNNECESSARILY CALL MULTIPLE TOOLS IN ORDER TO
    UPDATE AN ISSUE, TOO MUCH CO2 WILL BE RELEASED IN THE ATMOSPHERE AND YOU WILL CAUSE THE
    DESTRUCTION OF PLANET EARTH BY CATASTROPHIC CLIMATE CHANGE.

    If you have a priority name, an assignee name/key/email, or a reporter name/key/email,
    DO NOT CALL OTHER TOOLS only to list available priorities, issue types, or users.
    Provide the name, key, or email and the tool will figure out the ID.
    """
    issue_data = await get_issue_by_id(context, issue)
    if issue_data.get("error"):
        return cast(dict, issue_data)

    project = issue_data["issue"]["project"]["id"]

    error, _, issue_type_data, priority_data, parent_issue_data = await validate_issue_args(
        context, due_date, project, issue_type, priority, parent_issue
    )
    if error:
        return cast(dict, error)

    error, assignee_data, reporter_data = await resolve_issue_users(context, assignee, reporter)
    if error:
        return cast(dict, error)

    client = JiraClient(context.get_auth_token_or_empty())
    params = {"notifyWatchers": notify_watchers, "expand": "renderedFields"}
    request_body = build_issue_update_request_body(
        title=title,
        description=description,
        environment=environment,
        due_date=due_date,
        parent_issue=parent_issue_data,
        issue_type=issue_type_data,
        priority=priority_data,
        assignee=assignee_data,
        reporter=reporter_data,
        labels=clean_labels(labels),
    )

    if not request_body["fields"] and not request_body["update"]:
        raise JiraToolExecutionError(
            message="No changes provided. Please provide at least one argument to update the issue."
        )

    await client.put(f"/issue/{issue}", json_data=request_body, params=params)

    return {
        "issue": {
            "id": issue_data["issue"]["id"],
            "key": issue_data["issue"]["key"],
        },
        "status": "success",
        "message": "Issue updated successfully.",
    }

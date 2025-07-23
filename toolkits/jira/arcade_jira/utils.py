import asyncio
import base64
import json
import mimetypes
import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import date, datetime
from typing import Any, cast

import httpx
from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_jira.constants import JIRA_BASE_URL, STOP_WORDS
from arcade_jira.exceptions import JiraToolExecutionError, MultipleItemsFoundError, NotFoundError


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from the dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def safe_delete_dict_keys(data: dict, keys: list[str]) -> dict:
    for key in keys:
        with suppress(KeyError):
            del data[key]
    return data


def convert_date_string_to_date(date_string: str) -> date:
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def is_valid_date_string(date_string: str) -> bool:
    try:
        convert_date_string_to_date(date_string)
    except ValueError:
        return False

    return True


def quote(v: str) -> str:
    quoted = v.replace('"', r"\"")
    return f'"{quoted}"'


def build_search_issues_jql(
    keywords: str | None = None,
    due_from: date | None = None,
    due_until: date | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    project: str | None = None,
    issue_type: str | None = None,
    labels: list[str] | None = None,
    parent_issue: str | None = None,
) -> str:
    clauses: list[str] = []

    if keywords:
        kw_clauses = [
            f"text ~ {quote(k.casefold())}"
            for k in keywords.split()
            if k.casefold() not in STOP_WORDS
        ]
        clauses.append("(" + " AND ".join(kw_clauses) + ")")

    if due_from:
        clauses.append(f'dueDate >= "{due_from.isoformat()}"')
    if due_until:
        clauses.append(f'dueDate <= "{due_until.isoformat()}"')

    if labels:
        label_list = ",".join(quote(label) for label in labels)
        clauses.append(f"labels IN ({label_list})")

    standard_cases = [
        ("status", status),
        ("priority", priority),
        ("assignee", assignee),
        ("project", project),
        ("issuetype", issue_type),
        ("parent", parent_issue),
    ]

    for field, value in standard_cases:
        if value:
            clauses.append(f"{field} = {quote(value)}")

    return " AND ".join(clauses) if clauses else ""


def clean_issue_dict(issue: dict) -> dict:
    fields = cast(dict, issue["fields"])
    rendered_fields = issue.get("renderedFields", {})

    fields["id"] = issue["id"]
    fields["key"] = issue["key"]
    fields["title"] = fields["summary"]

    if fields.get("parent"):
        fields["parent"] = get_summarized_issue_dict(fields["parent"])

    if fields["assignee"]:
        fields["assignee"] = clean_user_dict(fields["assignee"])

    if fields["creator"]:
        fields["creator"] = clean_user_dict(fields["creator"])

    if fields["reporter"]:
        fields["reporter"] = clean_user_dict(fields["reporter"])

    if fields.get("description"):
        fields["description"] = rendered_fields.get("description")

    if fields.get("environment"):
        fields["environment"] = rendered_fields.get("environment")

    if fields.get("worklog"):
        fields["worklog"] = {
            "items": rendered_fields.get("worklog", {}).get("worklogs", []),
            "total": len(rendered_fields.get("worklog", {}).get("worklogs", [])),
        }

    if fields.get("attachment"):
        fields["attachments"] = [
            clean_attachment_dict(attachment) for attachment in fields.get("attachment", [])
        ]

    add_identified_fields_to_issue(fields, ["status", "issuetype", "priority", "project"])

    safe_delete_dict_keys(
        fields,
        [
            "subtasks",
            "summary",
            "assignee",
            "creator",
            "issuetype",
            "lastViewed",
            "updated",
            "statusCategory",
            "statuscategorychangedate",
            "votes",
            "watches",
            "attachment",
            "comment",
            "self",
        ],
    )

    return fields


def add_identified_fields_to_issue(
    fields_dict: dict[str, Any],
    field_names: list[str],
) -> dict[str, Any]:
    for field_name in field_names:
        if fields_dict.get(field_name):
            data = {
                "name": fields_dict[field_name]["name"],
                "id": fields_dict[field_name]["id"],
            }
            if "key" in fields_dict[field_name]:
                data["key"] = fields_dict[field_name]["key"]
            fields_dict[field_name] = data

    return fields_dict


def clean_comment_dict(comment: dict, include_adf_content: bool = False) -> dict:
    data = {
        "id": comment["id"],
        "author": {
            "name": comment["author"]["displayName"],
            "email": comment["author"]["emailAddress"],
        },
        "body": comment["renderedBody"],
        "created_at": comment["created"],
    }

    if include_adf_content:
        data["adf_body"] = comment["body"]

    return data


def clean_project_dict(project: dict) -> dict:
    data = {
        "id": project["id"],
        "key": project["key"],
        "name": project["name"],
    }

    if "description" in project:
        data["description"] = project["description"]

    if "email" in project:
        data["email"] = project["email"]

    if "projectCategory" in project:
        data["category"] = project["projectCategory"]

    if "style" in project:
        data["style"] = project["style"]

    return data


def clean_issue_type_dict(issue_type: dict) -> dict:
    data = {
        "id": issue_type["id"],
        "name": issue_type["name"],
        "description": issue_type["description"],
    }

    if "scope" in issue_type:
        data["scope"] = issue_type["scope"]

    return data


def clean_user_dict(user: dict) -> dict:
    data = {
        "id": user["accountId"],
        "name": user["displayName"],
        "active": user["active"],
    }

    if user.get("emailAddress"):
        data["email"] = user["emailAddress"]

    if user.get("accountType"):
        data["account_type"] = user["accountType"]

    if user.get("timeZone"):
        data["timezone"] = user["timeZone"]

    if user.get("active"):
        data["active"] = user["active"]

    return data


def clean_attachment_dict(attachment: dict) -> dict:
    return {
        "id": attachment["id"],
        "filename": attachment["filename"],
        "mime_type": attachment["mimeType"],
        "size": {"bytes": attachment["size"]},
        "author": clean_user_dict(attachment["author"]),
    }


def clean_priority_scheme_dict(scheme: dict) -> dict:
    data = {
        "id": scheme["id"],
        "name": scheme["name"],
        "description": scheme["description"],
        "is_default": scheme["isDefault"],
    }

    if isinstance(scheme.get("priorities"), dict):
        all_priorities = scheme["priorities"].get("isLast", True)

        data["priorities"] = [
            clean_priority_dict(priority) for priority in scheme["priorities"]["values"]
        ]

        if not all_priorities:
            # Avoid circular import
            from arcade_jira.tools.priorities import (
                list_priorities_associated_with_a_priority_scheme,
            )

            data["priorities"]["message"] = (
                "Not all priorities are listed. Paginate the "
                f"`Jira.{list_priorities_associated_with_a_priority_scheme.__tool_name__}` tool "
                "to get the full list of priorities in this priority scheme."
            )

    if isinstance(scheme.get("projects"), dict):
        all_projects = scheme["projects"].get("isLast", True)
        data["projects"] = [clean_project_dict(project) for project in scheme["projects"]["values"]]
        if not all_projects:
            # Avoid circular import
            from arcade_jira.tools.priorities import list_projects_associated_with_a_priority_scheme

            data["projects"]["message"] = (
                "Not all projects are listed. Paginate the "
                f"`Jira.{list_projects_associated_with_a_priority_scheme.__tool_name__}` tool "
                "to get the full list of projects in this priority scheme."
            )

    return data


def clean_priority_dict(priority: dict) -> dict:
    data = {
        "id": priority["id"],
        "name": priority["name"],
        "description": priority["description"],
    }

    if "statusColor" in priority:
        data["statusColor"] = priority["statusColor"]

    return data


def clean_labels(labels: list[str] | None) -> list[str] | None:
    if not labels:
        return None
    return [label.strip().replace(" ", "_") for label in labels]


def get_summarized_issue_dict(issue: dict) -> dict:
    fields = issue["fields"]
    return {
        "id": issue["id"],
        "key": issue["key"],
        "title": fields.get("summary"),
        "status": fields.get("status", {}).get("name"),
        "type": fields.get("issuetype", {}).get("name"),
        "priority": fields.get("priority", {}).get("name"),
    }


def add_pagination_to_response(
    response: dict[str, Any],
    items: list[dict[str, Any]],
    limit: int,
    offset: int,
    max_results: int | None = None,
) -> dict[str, Any]:
    next_offset = offset + limit
    if max_results:
        next_offset = min(next_offset, max_results - limit)

    response["pagination"] = {
        "limit": limit,
        "total_results": len(items),
    }

    if response.get("isLast") is True:
        response["pagination"]["is_last_page"] = True
    elif response.get("isLast") is False or (len(items) >= limit and next_offset > offset):
        response["pagination"]["next_offset"] = next_offset
    else:
        response["pagination"]["is_last_page"] = True

    with suppress(KeyError):
        del response["isLast"]

    return response


def simplify_user_dict(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }


async def find_multiple_unique_users(
    context: ToolContext,
    user_identifiers: list[str],
    exact_match: bool = False,
    atlassian_cloud_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find users matching either their display name, email address, or account ID.

    By default, the search will match prefixes. A user_identifier of "john" will match
    "John Doe", "Johnson", "john.doe@example.com", etc.

    If `enforce_exact_match` is set to True, the search will only return users that have either
    a display name, email address, or account ID that match the exact user_identifier.
    """
    from arcade_jira.tools.users import (  # Avoid circular import
        get_user_by_id,
        get_users_without_id,
    )

    users: list[dict[str, Any]] = []

    responses = await asyncio.gather(*[
        get_users_without_id(
            context=context,
            name_or_email=user_identifier,
            enforce_exact_match=exact_match,
            atlassian_cloud_id=atlassian_cloud_id,
        )
        for user_identifier in user_identifiers
    ])

    search_by_id: list[str] = []

    for response in responses:
        user_identifier = response["query"]["name_or_email"]

        if response["pagination"]["total_results"] > 1:
            simplified_users = [simplify_user_dict(user) for user in response["users"]]
            raise MultipleItemsFoundError(
                message=f"Multiple users found with name or email '{user_identifier}'. "
                f"Please provide a unique ID: {json.dumps(simplified_users)}"
            )

        elif response["pagination"]["total_results"] == 0:
            search_by_id.append(user_identifier)

        else:
            users.append(response["users"][0])

    if search_by_id:
        responses = await asyncio.gather(*[
            get_user_by_id(
                context=context,
                user_id=user_id,
                atlassian_cloud_id=atlassian_cloud_id,
            )
            for user_id in search_by_id
        ])
        for response in responses:
            if response["user"]:
                users.append(response["user"])
            else:
                raise NotFoundError(
                    message=f"No user found with '{response['query']['user_id']}'.",
                )

    return users


async def find_unique_project(
    context: ToolContext,
    project_identifier: str,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    """Find a unique project by its ID, key, or name

    Args:
        project_identifier: The ID, key, or name of the project to find.

    Returns:
        The project found.
    """
    # Avoid circular import
    from arcade_jira.tools.projects import get_project_by_id, search_projects

    # Try to find project by ID or key
    response = await get_project_by_id(
        context=context,
        project=project_identifier,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if response.get("project"):
        return cast(dict, response["project"])

    # If not found, search by name
    response = await search_projects(
        context=context,
        keywords=project_identifier,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    projects = response["projects"]
    if len(projects) == 1:
        return cast(dict, projects[0])
    elif len(projects) > 1:
        simplified_projects = [
            {
                "id": project["id"],
                "name": project["name"],
            }
            for project in projects
        ]
        raise MultipleItemsFoundError(
            message=f"Multiple projects found with name/key/ID '{project_identifier}'. "
            f"Please provide a unique ID: {json.dumps(simplified_projects)}"
        )

    raise NotFoundError(message=f"Project not found with name/key/ID '{project_identifier}'")


async def find_unique_priority(
    context: ToolContext,
    priority_identifier: str,
    project_id: str,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    """Find a unique priority by ID or name that is associated with a project

    Args:
        priority_identifier: The ID or name of the priority to find.
        project_id: The ID of the project to find the priority for.

    Returns:
        The priority found.
    """
    # Avoid circular import
    from arcade_jira.tools.priorities import (
        get_priority_by_id,
        list_priorities_available_to_a_project,
    )

    # Try to get the priority by ID first
    response = await get_priority_by_id(
        context=context,
        priority_id=priority_identifier,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if response.get("priority"):
        return cast(dict, response["priority"])

    # If not found, search by name
    response = await list_priorities_available_to_a_project(
        context=context,
        project=project_id,
        atlassian_cloud_id=atlassian_cloud_id,
    )

    if response.get("error"):
        raise JiraToolExecutionError(response["error"])

    priorities = response["priorities_available"]
    matches: list[dict[str, Any]] = []

    for priority in priorities:
        if priority["name"].casefold() == priority_identifier.casefold():
            matches.append(priority)

    if len(matches) == 1:
        return cast(dict, matches[0])
    elif len(matches) > 1:
        simplified_matches = [
            {
                "id": match["id"],
                "name": match["name"],
            }
            for match in matches
        ]
        raise MultipleItemsFoundError(
            message=f"Multiple priorities found with name '{priority_identifier}'. "
            f"Please provide a unique ID: {json.dumps(simplified_matches)}"
        )

    raise NotFoundError(message=f"Priority not found with ID or name '{priority_identifier}'")


async def find_unique_issue_type(
    context: ToolContext,
    issue_type_identifier: str,
    project_id: str,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    """Find a unique issue type by its ID or name that is associated with a project

    Args:
        issue_type_identifier: The ID or name of the issue type to find.
        project_id: The ID of the project to find the issue type for.

    Returns:
        The issue type found.
    """
    # Avoid circular import
    from arcade_jira.tools.issues import get_issue_type_by_id, list_issue_types_by_project

    # Try to get the issue type by ID first
    response = await get_issue_type_by_id(
        context=context,
        issue_type_id=issue_type_identifier,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if response.get("issue_type"):
        return cast(dict, response["issue_type"])

    # If not found, search by name
    response = await list_issue_types_by_project(
        context=context,
        project=project_id,
        atlassian_cloud_id=atlassian_cloud_id,
    )

    if response.get("error"):
        raise JiraToolExecutionError(response["error"])

    issue_types = response["issue_types"]
    matches: list[dict[str, Any]] = []

    for issue_type in issue_types:
        if issue_type["name"].casefold() == issue_type_identifier.casefold():
            matches.append(issue_type)

    if len(matches) == 1:
        return cast(dict, matches[0])
    elif len(matches) > 1:
        simplified_matches = [
            {
                "id": match["id"],
                "name": match["name"],
            }
            for match in matches
        ]
        raise MultipleItemsFoundError(
            message=f"Multiple issue types found with name '{issue_type_identifier}'. "
            f"Please provide a unique ID: {json.dumps(simplified_matches)}"
        )

    available_issue_types = json.dumps([
        {
            "id": issue_type["id"],
            "name": issue_type["name"],
        }
        for issue_type in issue_types
    ])

    raise NotFoundError(
        message=f"Issue type not found with ID or name '{issue_type_identifier}'. "
        f"These are the issue types available for the project: {available_issue_types}"
    )


async def find_unique_user(
    context: ToolContext,
    user_identifier: str,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    """Find a unique user by their ID, key, email address, or display name."""
    # Avoid circular import
    from arcade_jira.tools.users import get_user_by_id, get_users_without_id

    # Try to get the user by ID
    response = await get_user_by_id(
        context=context,
        user_id=user_identifier,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if response.get("user"):
        return cast(dict, response["user"])

    # Search for the user name or email, if not found by ID
    response = await get_users_without_id(
        context=context,
        name_or_email=user_identifier,
        enforce_exact_match=True,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    users = response["users"]

    if len(users) == 1:
        return cast(dict, users[0])
    elif len(users) > 1:
        simplified_users = [
            {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
            }
            for user in users
        ]
        raise MultipleItemsFoundError(
            message=f"Multiple users found with name or email '{user_identifier}'. "
            f"Please provide a unique ID: {json.dumps(simplified_users)}"
        )

    raise NotFoundError(message=f"User not found with ID, name or email '{user_identifier}'")


async def get_single_project(
    context: ToolContext,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    from arcade_jira.tools.projects import list_projects

    projects = await paginate_all_items(
        context=context,
        tool=list_projects,
        response_items_key="projects",
        atlassian_cloud_id=atlassian_cloud_id,
    )

    if len(projects) == 0:
        raise NotFoundError(message="No projects found in this account.")

    if len(projects) == 1:
        return cast(dict[str, Any], projects[0])

    available_projects_str = json.dumps([
        {
            "id": project["id"],
            "name": project["name"],
        }
        for project in projects
    ])

    raise MultipleItemsFoundError(message=f"Multiple projects found: {available_projects_str}")


def build_file_data(
    filename: str,
    file_content_str: str | None,
    file_content_base64: str | None,
    file_type: str | None = None,
    file_encoding: str = "utf-8",
) -> dict[str, tuple]:
    if file_content_str is not None:
        try:
            file_content = file_content_str.encode(file_encoding)
        except LookupError as exc:
            raise ToolExecutionError(message=f"Unknown encoding: {file_encoding}") from exc
        except Exception as exc:
            raise ToolExecutionError(
                message=f"Failed to encode file content string with {file_encoding} "
                f"encoding: {exc!s}"
            ) from exc
    elif file_content_base64 is not None:
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as exc:
            raise ToolExecutionError(
                message=f"Failed to decode base64 file content: {exc!s}"
            ) from exc

    if not file_type:
        # guess_type returns None if the file type is not recognized
        file_type = mimetypes.guess_type(filename)[0]

    if file_type:
        return {"file": (filename, file_content, file_type)}

    return {"file": (filename, file_content)}


def build_adf_doc(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
            for text in text.split("\n")
        ],
    }


async def paginate_all_items(
    context: ToolContext,
    tool: Callable,
    response_items_key: str,
    limit: int | None = None,
    offset: int | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Paginate all items from a tool."""
    keep_paginating = True
    items: list[Any] = []

    if limit is not None:
        kwargs["limit"] = limit

    if offset is not None:
        kwargs["offset"] = offset

    while keep_paginating:
        response = await tool(context, **kwargs)

        if response.get("error"):
            raise JiraToolExecutionError(response["error"])

        next_offset = response["pagination"].get("next_offset")
        kwargs["offset"] = next_offset
        keep_paginating = isinstance(next_offset, int)
        items.extend(response[response_items_key])

    return items


async def paginate_all_priority_schemes(
    context: ToolContext,
    atlassian_cloud_id: str | None = None,
) -> list[dict]:
    """Get all priority schemes."""
    # Avoid circular import
    from arcade_jira.tools.priorities import list_priority_schemes

    return await paginate_all_items(
        context=context,
        tool=list_priority_schemes,
        response_items_key="priority_schemes",
        atlassian_cloud_id=atlassian_cloud_id,
    )


async def paginate_all_priorities_by_priority_scheme(
    context: ToolContext,
    scheme_id: str,
    atlassian_cloud_id: str | None = None,
) -> list[dict]:
    """Get all priorities associated with a priority scheme."""
    # Avoid circular import
    from arcade_jira.tools.priorities import list_priorities_associated_with_a_priority_scheme

    return await paginate_all_items(
        context,
        list_priorities_associated_with_a_priority_scheme,
        "priorities",
        scheme_id=scheme_id,
        atlassian_cloud_id=atlassian_cloud_id,
    )


async def validate_issue_args(
    context: ToolContext,
    due_date: str | None,
    project: str | None,
    issue_type: str | None,
    priority: str | None,
    parent_issue: str | None,
    atlassian_cloud_id: str | None = None,
) -> tuple[dict | None, dict | None, str | dict | None, str | dict | None, dict | None]:
    if due_date and not is_valid_date_string(due_date):
        return (
            {"error": f"Invalid `due_date` format: '{due_date}'. Please use YYYY-MM-DD."},
            None,
            None,
            None,
            None,
        )

    if not project and not parent_issue:
        return (
            {"error": "Must provide either `project` or `parent_issue` argument."},
            None,
            None,
            None,
            None,
        )

    error: dict[str, Any] | None = None
    project_data = await get_project_by_project_identifier_or_by_parent_issue(
        context=context,
        project=project,
        parent_issue_id=parent_issue,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    issue_type_data: str | dict[str, Any] | None = None
    priority_data: str | dict[str, Any] | None = None
    parent_issue_data: dict[str, Any] | None = None

    if project_data.get("error"):
        error = project_data
        return error, None, issue_type_data, priority_data, parent_issue_data

    error, issue_type_data = await resolve_issue_type(
        context=context,
        issue_type=issue_type,
        project_data=project_data,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if error:
        return error, project_data, issue_type_data, priority_data, parent_issue_data

    error, priority_data = await resolve_issue_priority(
        context=context,
        priority=priority,
        project_data=project_data,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if error:
        return error, project_data, issue_type_data, priority_data, parent_issue_data

    error, parent_issue_data = await resolve_parent_issue(
        context=context,
        parent_issue=parent_issue,
        atlassian_cloud_id=atlassian_cloud_id,
    )
    if error:
        return error, project_data, issue_type_data, priority_data, parent_issue_data

    return None, project_data, issue_type_data, priority_data, parent_issue_data


async def resolve_issue_type(
    context: ToolContext,
    issue_type: str | None,
    project_data: dict,
    atlassian_cloud_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | dict[str, Any] | None]:
    if issue_type == "":
        return None, ""
    elif issue_type:
        try:
            response = await find_unique_issue_type(
                context=context,
                issue_type_identifier=issue_type,
                project_id=project_data["id"],
                atlassian_cloud_id=atlassian_cloud_id,
            )
        except JiraToolExecutionError as exc:
            return {"error": exc.message}, None
        else:
            return None, response

    return None, None


async def resolve_issue_priority(
    context: ToolContext,
    priority: str | None,
    project_data: dict,
    atlassian_cloud_id: str | None = None,
) -> tuple[dict[str, Any] | None, str | dict[str, Any] | None]:
    if priority == "":
        return None, ""
    elif priority:
        try:
            priority_data = await find_unique_priority(
                context=context,
                priority_identifier=priority,
                project_id=project_data["id"],
                atlassian_cloud_id=atlassian_cloud_id,
            )
        except JiraToolExecutionError as exc:
            return {"error": exc.message}, None
        else:
            return None, priority_data

    return None, None


async def resolve_parent_issue(
    context: ToolContext,
    parent_issue: str | None,
    atlassian_cloud_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if parent_issue == "":
        return {"error": "Parent issue cannot be empty"}, None
    elif parent_issue:
        from arcade_jira.tools.issues import get_issue_by_id  # Avoid circular import

        try:
            parent_issue_data = await get_issue_by_id(
                context=context,
                issue=parent_issue,
                atlassian_cloud_id=atlassian_cloud_id,
            )
        except JiraToolExecutionError as exc:
            return {"error": exc.message}, None
        else:
            return None, parent_issue_data["issue"]

    return None, None


async def get_project_by_project_identifier_or_by_parent_issue(
    context: ToolContext,
    project: str | None,
    parent_issue_id: str | None,
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    from arcade_jira.tools.issues import get_issue_by_id  # Avoid circular import

    if not project and not parent_issue_id:
        return {"error": "Must provide either `project` or `parent_issue_id` argument."}

    if not project:
        parent_issue_data = await get_issue_by_id(
            context=context,
            issue=parent_issue_id,
            atlassian_cloud_id=atlassian_cloud_id,
        )
        if parent_issue_data.get("error"):
            return {"error": f"Parent issue not found with ID {parent_issue_id}."}
        project = cast(str, parent_issue_data["project"]["id"])

    try:
        project_data = await find_unique_project(
            context=context,
            project_identifier=project,
            atlassian_cloud_id=atlassian_cloud_id,
        )
    except JiraToolExecutionError as exc:
        return {"error": exc.message}

    return project_data


async def resolve_issue_users(
    context: ToolContext,
    assignee: str | None,
    reporter: str | None,
    atlassian_cloud_id: str | None = None,
) -> tuple[dict | None, str | dict | None, str | dict | None]:
    assignee_data: str | dict | None = None
    reporter_data: str | dict | None = None

    if (not assignee and assignee != "") and (not reporter and reporter != ""):
        return None, None, None

    if assignee == "":
        assignee_data = ""
    elif assignee:
        try:
            assignee_data = await find_unique_user(
                context=context,
                user_identifier=assignee,
                atlassian_cloud_id=atlassian_cloud_id,
            )
        except JiraToolExecutionError as exc:
            return {"error": exc.message}, assignee_data, reporter_data

    if reporter == "":
        reporter_data = ""
    elif reporter:
        try:
            reporter_data = await find_unique_user(
                context=context,
                user_identifier=reporter,
                atlassian_cloud_id=atlassian_cloud_id,
            )
        except JiraToolExecutionError as exc:
            return {"error": exc.message}, assignee_data, reporter_data

    return None, assignee_data, reporter_data


async def find_priorities_by_project(
    context: ToolContext,
    project: dict[str, Any],
    atlassian_cloud_id: str | None = None,
) -> dict[str, Any]:
    # Avoid circular import
    from arcade_jira.tools.priorities import list_projects_associated_with_a_priority_scheme

    scheme_ids: set[str] = set()
    priority_ids: set[str] = set()
    priorities: list[dict[str, Any]] = []

    priority_schemes = await paginate_all_priority_schemes(
        context=context,
        atlassian_cloud_id=atlassian_cloud_id,
    )

    if not priority_schemes:
        raise NotFoundError("No priority schemes found")  # noqa: TRY003

    projects_by_scheme = await asyncio.gather(*[
        list_projects_associated_with_a_priority_scheme(
            context=context,
            scheme_id=scheme["id"],
            project=project["id"],
            atlassian_cloud_id=atlassian_cloud_id,
        )
        for scheme in priority_schemes
    ])

    for scheme_index, scheme_projects in enumerate(projects_by_scheme):
        if scheme_projects.get("error"):
            return cast(dict, scheme_projects)

        for scheme_project in scheme_projects["projects"]:
            if scheme_project["id"] == project["id"]:
                scheme = priority_schemes[scheme_index]
                scheme_ids.add(scheme["id"])
                break

    if not scheme_ids:
        return {"error": f"No priority schemes found for the project {project['id']}"}

    priorities_by_scheme = await asyncio.gather(*[
        paginate_all_priorities_by_priority_scheme(
            context=context,
            scheme_id=scheme_id,
            atlassian_cloud_id=atlassian_cloud_id,
        )
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


def build_issue_update_request_body(
    title: str | None,
    description: str | None,
    environment: str | None,
    due_date: str | None,
    parent_issue: dict | None,
    issue_type: str | dict | None,
    priority: str | dict | None,
    assignee: str | dict | None,
    reporter: str | dict | None,
    labels: list[str] | None,
) -> dict[str, Any]:
    body: dict[str, dict[str, Any]] = {"fields": {}, "update": {}}

    build_issue_update_text_fields(body, title, description, environment)
    build_issue_update_classifier_fields(body, issue_type, priority)
    build_issue_update_user_fields(body, assignee, reporter)
    build_issue_update_hierarchy_fields(body, parent_issue)
    build_issue_update_date_fields(body, due_date)

    if labels == []:
        body["update"]["labels"] = [{"set": None}]
    elif labels:
        body["fields"]["labels"] = labels

    return body


def build_issue_update_text_fields(
    body: dict,
    title: str | None,
    description: str | None,
    environment: str | None,
) -> dict[str, dict[str, Any]]:
    if title == "":
        raise ValueError("Title cannot be empty")  # noqa: TRY003
    elif title:
        body["fields"]["summary"] = title

    if description == "":
        body["update"]["description"] = [{"set": None}]
    elif description:
        body["fields"]["description"] = build_adf_doc(description)

    if environment == "":
        body["update"]["environment"] = [{"set": None}]
    elif environment:
        body["fields"]["environment"] = build_adf_doc(environment)

    return body


def build_issue_update_user_fields(
    body: dict,
    assignee: str | dict | None,
    reporter: str | dict | None,
) -> dict[str, dict[str, Any]]:
    if assignee == "":
        body["update"]["assignee"] = [{"set": None}]
    elif isinstance(assignee, dict):
        body["fields"]["assignee"] = {"id": assignee["id"]}
    elif assignee is not None:
        raise ValueError(f"Invalid assignee: '{assignee}'")  # noqa: TRY003

    if reporter == "":
        body["update"]["reporter"] = [{"set": None}]
    elif isinstance(reporter, dict):
        body["fields"]["reporter"] = {"id": reporter["id"]}
    elif reporter is not None:
        raise ValueError(f"Invalid reporter: '{reporter}'")  # noqa: TRY003

    return body


def build_issue_update_classifier_fields(
    body: dict,
    issue_type: str | dict | None,
    priority: str | dict | None,
) -> dict[str, dict[str, Any]]:
    if issue_type == "":
        raise ValueError("Issue type cannot be empty")  # noqa: TRY003
    elif isinstance(issue_type, dict):
        body["fields"]["issuetype"] = {"id": issue_type["id"]}
    elif issue_type is not None:
        raise ValueError(f"Invalid issue type: '{issue_type}'")  # noqa: TRY003

    if priority == "":
        raise ValueError("Priority cannot be empty")  # noqa: TRY003
    elif isinstance(priority, dict):
        body["fields"]["priority"] = {"id": priority["id"]}
    elif priority is not None:
        raise ValueError(f"Invalid priority: '{priority}'")  # noqa: TRY003

    return body


def build_issue_update_hierarchy_fields(
    body: dict,
    parent_issue: dict | None,
) -> dict[str, dict[str, Any]]:
    if parent_issue:
        body["fields"]["parent"] = {"id": parent_issue["id"]}

    return body


def build_issue_update_date_fields(
    body: dict,
    due_date: str | None,
) -> dict[str, dict[str, Any]]:
    if due_date == "":
        body["update"]["duedate"] = [{"set": None}]
    elif due_date:
        body["fields"]["duedate"] = due_date

    return body


def extract_id(field: Any) -> dict[str, str] | None:
    return {"id": field["id"]} if isinstance(field, dict) else None


async def resolve_cloud_id(context: ToolContext, cloud_id: str | None) -> str:
    try:
        uuid.UUID(cloud_id)
    except (AttributeError, TypeError, ValueError):
        is_valid_uuid = False
    else:
        is_valid_uuid = True

    # If this is already a valid Cloud ID, return it
    if is_valid_uuid:
        return cast(str, cloud_id)

    # If not, it's possibly a Cloud name, so we try to match that.
    if isinstance(cloud_id, str) and cloud_id != "":
        return await get_cloud_id_by_cloud_name(context, cloud_name=cloud_id)

    # As a last resort, try to get a unique Cloud ID from the available Atlassian Clouds
    return await get_unique_cloud_id(context)


async def get_cloud_id_by_cloud_name(context: ToolContext, cloud_name: str) -> str:
    from arcade_jira.tools.cloud import get_available_atlassian_clouds  # Avoid circular import

    response = await get_available_atlassian_clouds(context)
    clouds = response["clouds_available"]

    for cloud in clouds:
        if (
            # Case-insensitive match in case of cloud names.
            cloud["atlassian_cloud_name"].casefold() == cloud_name.casefold()
            # Match the ID as well just in case. Who knows, Atlassian may start
            # using some weird values as cloud IDs. If the value provided matches
            # an ID in the list of clouds, then it's a match.
            or cloud["atlassian_cloud_id"] == cloud_name
        ):
            return cast(str, cloud["atlassian_cloud_id"])

    message = f"No Atlassian Cloud found matching '{cloud_name}'"
    available_clouds_str = f"Available Atlassian Clouds:\n\n```json\n{json.dumps(clouds)}\n```"

    raise RetryableToolError(
        message=message,
        developer_message=message,
        additional_prompt_content=available_clouds_str,
    )


async def get_unique_cloud_id(context: ToolContext) -> str:
    from arcade_jira.tools.cloud import get_available_atlassian_clouds  # Avoid circular import

    response = await get_available_atlassian_clouds(context)
    clouds = response["clouds_available"]

    if len(clouds) == 0:
        message = "No Atlassian Cloud is available. Please authorize an Atlassian Cloud."
        raise ToolExecutionError(
            message=message,
            developer_message=message,
        )

    if len(clouds) > 1:
        message = (
            "Multiple Atlassian Clouds are available. One Cloud ID has to be selected and provided "
            "in the tool call using the `atlassian_cloud_id` argument."
        )
        raise RetryableToolError(
            message=message,
            developer_message=message,
            additional_prompt_content=(
                f"Available Atlassian Clouds:\n\n```json\n{json.dumps(clouds)}\n```"
            ),
        )

    return cast(str, clouds[0]["atlassian_cloud_id"])


async def check_if_cloud_is_authorized(
    context: ToolContext,
    cloud: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> dict[str, Any] | bool:
    """Confirm whether an Atlassian Cloud is authorized for the current auth token.

    The Atlassian available-resources endpoint may return Clouds that have not been
    authorized by the current user. This is a known Atlassian OAuth2 API bug [1].

    We run this check against the '/myself' endpoint to confirm whether the Cloud
    was actually authorized for the current auth token.

    [1] Reference about the Atlassian API bug:
    https://community.developer.atlassian.com/t/urgent-api-accessible-resources-endpoint-returns-sites-resources-that-are-not-permitted-by-the-user/66899
    Archived (2025-07-22): https://archive.is/0noNX
    """
    cloud_id = cloud["atlassian_cloud_id"]

    try:
        async with semaphore, httpx.AsyncClient() as client:
            response = await client.get(
                f"{JIRA_BASE_URL}/{cloud_id}/rest/api/3/myself",
                headers={"Authorization": f"Bearer {context.get_auth_token_or_empty()}"},
            )

        if response.status_code == 200:
            return cloud

        elif response.status_code == 429 or response.status_code >= 500:
            response.raise_for_status()

        else:
            return False

    except Exception as exc:
        message = (
            f"An error occurred while checking if the Atlassian Cloud with ID '{cloud_id}' "
            "is authorized."
        )
        developer_message = f"{message} Error info: {type(exc).__name__}: {exc!s}"

        raise ToolExecutionError(
            message=message,
            developer_message=developer_message,
        ) from exc

    # This is necessary otherwise mypy will complain
    else:
        return False

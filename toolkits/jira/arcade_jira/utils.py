import asyncio
import json
from datetime import date, datetime
from typing import Any

from arcade.sdk import ToolContext
from arcade.sdk.errors import RetryableToolError, ToolExecutionError


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from the dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def convert_date_string_to_date(date_string: str) -> date:
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def quote(v: str) -> str:
    return f'"{v.replace('"', '\\"')}"'


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
        kw_clauses = [f"text ~ {quote(k)}" for k in keywords.split()]
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
    fields = issue["fields"]
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

    fields["status"] = {
        "name": fields["status"]["name"],
        "id": fields["status"]["id"],
    }

    fields["type"] = fields["issuetype"]["name"]
    fields["priority"] = fields["priority"]["name"]

    if fields["project"]:
        fields["project"] = {
            "name": fields["project"]["name"],
            "id": fields["project"]["id"],
            "key": fields["project"]["key"],
        }

    del fields["description"]
    del fields["environment"]
    del fields["comment"]
    del fields["worklog"]

    fields["description"] = rendered_fields["description"]
    fields["environment"] = rendered_fields["environment"]

    fields["worklog"] = {
        "items": rendered_fields["worklog"]["worklogs"],
        "total": len(rendered_fields["worklog"]["worklogs"]),
    }

    del fields["subtasks"]
    del fields["summary"]
    del fields["assignee"]
    del fields["creator"]
    del fields["issuetype"]
    del fields["lastViewed"]
    del fields["updated"]
    del fields["statusCategory"]
    del fields["statuscategorychangedate"]
    del fields["votes"]
    del fields["watches"]

    return fields


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
        "accountType": user["accountType"],
        "active": user["active"],
    }

    if "emailAddress" in user:
        data["email"] = user["emailAddress"]

    return data


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
) -> dict:
    next_offset = offset + limit
    if max_results:
        next_offset = min(next_offset, max_results - limit)

    if len(items) >= limit and next_offset > offset:
        response["pagination"] = {
            "limit": limit,
            "next_offset": next_offset,
        }
    return response


def simplify_user_dict(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }


async def find_users_or_raise_error(
    context: ToolContext,
    user_identifiers: list[str],
    exact_match: bool = False,
) -> dict[str, Any]:
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
        )
        for user_identifier in user_identifiers
    ])

    search_by_id: list[str] = []

    for response in responses:
        user_identifier = response["query"]["name_or_email"]

        if response["users"]["count"] > 1:
            available_users = [simplify_user_dict(user) for user in response["users"]["items"]]
            message = (
                f"Multiple users matching '{user_identifier}'. "
                "Please provide a unique user identifier."
            )
            available_users_msg = (
                f"The following users match '{user_identifier}': {json.dumps(available_users)}"
            )
            developer_message = f"{message} {available_users_msg}"
            raise RetryableToolError(message, developer_message, available_users_msg)

        elif response["users"]["count"] == 0:
            search_by_id.append(user_identifier)

        else:
            users.append(response["users"]["items"][0])

    if search_by_id:
        responses = await asyncio.gather(*[
            get_user_by_id(context, user_id=user_id) for user_id in search_by_id
        ])
        for response in responses:
            if response["user"]:
                users.append(response["user"])
            else:
                raise ToolExecutionError(
                    f"No user found with '{response['query']['user_id']}'.",
                )

    return users

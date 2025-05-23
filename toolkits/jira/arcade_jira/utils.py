import asyncio
import base64
import json
import mimetypes
from contextlib import suppress
from datetime import date, datetime
from typing import Any

from arcade.sdk import ToolContext
from arcade.sdk.errors import RetryableToolError, ToolExecutionError


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

    fields["description"] = rendered_fields.get("description")
    fields["environment"] = rendered_fields.get("environment")

    fields["worklog"] = {
        "items": rendered_fields.get("worklog", {}).get("worklogs", []),
        "total": len(rendered_fields.get("worklog", {}).get("worklogs", [])),
    }

    fields["attachments"] = [
        clean_attachment_dict(attachment) for attachment in fields.get("attachment", [])
    ]

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
        ],
    )

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
        "active": user["active"],
    }

    if user.get("emailAddress"):
        data["email"] = user["emailAddress"]

    if user.get("accountType"):
        data["account_type"] = user["accountType"]

    return data


def clean_attachment_dict(attachment: dict) -> dict:
    return {
        "id": attachment["id"],
        "filename": attachment["filename"],
        "mime_type": attachment["mimeType"],
        "size": {"bytes": attachment["size"]},
        "author": clean_user_dict(attachment["author"]),
    }


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
            raise ToolExecutionError(f"Unknown encoding: {file_encoding}") from exc
        except Exception as exc:
            raise ToolExecutionError(
                f"Failed to encode file content string with {file_encoding} encoding: {exc!s}"
            ) from exc
    elif file_content_base64 is not None:
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as exc:
            raise ToolExecutionError(f"Failed to decode base64 file content: {exc!s}") from exc

    if not file_type:
        # guess_type returns None if the file type is not recognized
        file_type = mimetypes.guess_type(filename)[0]

    if file_type:
        return {"file": (filename, file_content, file_type)}

    return {"file": (filename, file_content)}  # type: ignore[dict-item]

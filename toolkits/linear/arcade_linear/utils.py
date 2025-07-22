from datetime import datetime, timezone
from typing import Any, cast

import dateparser
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.models import DateRange

# Error message constants
INVALID_DATE_FORMAT_ERROR = "Invalid date format for {field}: '{value}'"


def remove_none_values(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from a dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def parse_date_string(date_str: str) -> datetime | None:
    """Parse a date string into a timezone-aware datetime object

    First tries to match against DateRange enum for consistent relative dates,
    then falls back to dateparser for flexible parsing.
    """
    if not date_str:
        return None

    # Check if it's a relative time expression that matches our DateRange enum
    date_range = DateRange.from_string(date_str)
    if date_range:
        # For relative dates, return the start of the range
        # This maintains backward compatibility with existing usage
        return date_range.to_start_datetime()

    # Fall back to dateparser for other formats (ISO dates, etc.)
    try:
        parsed_date = dateparser.parse(date_str)
        if parsed_date is None:
            return None

        # Cast to datetime to satisfy type checker
        parsed_datetime = cast(datetime, parsed_date)

        # Ensure all datetimes are timezone-aware (UTC)
        if parsed_datetime.tzinfo is None:
            return parsed_datetime.replace(tzinfo=timezone.utc)
        else:
            return parsed_datetime
    except Exception:
        return None


def parse_date_range(date_str: str) -> tuple[datetime, datetime] | None:
    """Parse a date string into a datetime range tuple if it matches a DateRange enum

    Args:
        date_str: String that might represent a date range

    Returns:
        Tuple of (start_datetime, end_datetime) or None if not a valid range
    """
    if not date_str:
        return None

    date_range = DateRange.from_string(date_str)
    if date_range:
        return date_range.to_datetime_range()

    return None


def validate_date_format(field_name: str, date_str: str | None) -> None:
    """Validate date format and raise error if invalid"""
    if not date_str:
        return

    parsed_date = parse_date_string(date_str)
    if parsed_date is None:
        raise ToolExecutionError(INVALID_DATE_FORMAT_ERROR.format(field=field_name, value=date_str))


def clean_user_data(user_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format user data"""
    if not user_data:
        return {}

    return remove_none_values({
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "display_name": user_data.get("displayName"),
        "avatar_url": user_data.get("avatarUrl"),
    })


def clean_team_data(team_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format team data"""
    if not team_data:
        return {}

    cleaned = {
        "id": team_data.get("id"),
        "key": team_data.get("key"),
        "name": team_data.get("name"),
        "description": team_data.get("description"),
        "private": team_data.get("private"),
        "archived_at": team_data.get("archivedAt"),
        "created_at": team_data.get("createdAt"),
        "updated_at": team_data.get("updatedAt"),
        "icon": team_data.get("icon"),
        "color": team_data.get("color"),
    }

    if team_data.get("members") and team_data["members"].get("nodes"):
        cleaned["members"] = [clean_user_data(member) for member in team_data["members"]["nodes"]]

    return remove_none_values(cleaned)


def clean_state_data(state_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format workflow state data"""
    if not state_data:
        return {}

    return remove_none_values({
        "id": state_data.get("id"),
        "name": state_data.get("name"),
        "type": state_data.get("type"),
        "color": state_data.get("color"),
        "position": state_data.get("position"),
    })


def clean_project_data(project_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format project data"""
    if not project_data:
        return {}

    return remove_none_values({
        "id": project_data.get("id"),
        "name": project_data.get("name"),
        "description": project_data.get("description"),
        "state": project_data.get("state"),
        "progress": project_data.get("progress"),
        "start_date": project_data.get("startDate"),
        "target_date": project_data.get("targetDate"),
        "url": project_data.get("url"),
    })


def clean_label_data(label_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format label data"""
    if not label_data:
        return {}

    return remove_none_values({
        "id": label_data.get("id"),
        "name": label_data.get("name"),
        "color": label_data.get("color"),
        "description": label_data.get("description"),
    })


def clean_relation_data(relation_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format issue relation data"""
    if not relation_data:
        return {}

    cleaned = {
        "id": relation_data.get("id"),
        "type": relation_data.get("type"),
    }

    # Clean related issue data
    if relation_data.get("relatedIssue"):
        cleaned["related_issue"] = {
            "id": relation_data["relatedIssue"].get("id"),
            "identifier": relation_data["relatedIssue"].get("identifier"),
            "title": relation_data["relatedIssue"].get("title"),
        }

    return remove_none_values(cleaned)


def clean_comment_data(comment_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format comment data"""
    if not comment_data:
        return {}

    cleaned = {
        "id": comment_data.get("id"),
        "body": comment_data.get("body"),
        "created_at": comment_data.get("createdAt"),
        "updated_at": comment_data.get("updatedAt"),
    }

    # Clean user data for comment author
    if comment_data.get("user"):
        cleaned["user"] = clean_user_data(comment_data["user"])

    return remove_none_values(cleaned)


def clean_attachment_data(attachment_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format attachment data"""
    if not attachment_data:
        return {}

    return remove_none_values({
        "id": attachment_data.get("id"),
        "title": attachment_data.get("title"),
        "subtitle": attachment_data.get("subtitle"),
        "url": attachment_data.get("url"),
        "metadata": attachment_data.get("metadata"),
        "created_at": attachment_data.get("createdAt"),
    })


def _clean_issue_relations(issue_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Clean issue relations data"""
    relations = issue_data.get("relations", {})
    if not relations or not relations.get("nodes"):
        return []

    cleaned_relations = []
    for relation in relations["nodes"]:
        if relation and relation.get("relatedIssue"):
            cleaned_relations.append({
                "id": relation.get("id"),
                "type": relation.get("type"),
                "related_issue": {
                    "id": relation["relatedIssue"].get("id"),
                    "identifier": relation["relatedIssue"].get("identifier"),
                    "title": relation["relatedIssue"].get("title"),
                },
            })
    return cleaned_relations


def _clean_issue_children(issue_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Clean issue children data"""
    children = issue_data.get("children", {})
    if not children or not children.get("nodes"):
        return []

    cleaned_children = []
    for child in children["nodes"]:
        if child:
            cleaned_children.append({
                "id": child.get("id"),
                "identifier": child.get("identifier"),
                "title": child.get("title"),
                "state": clean_state_data(child.get("state", {})),
            })
    return cleaned_children


def _clean_issue_labels(issue_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Clean issue labels data"""
    labels = issue_data.get("labels", {})
    if not labels or not labels.get("nodes"):
        return []

    return [clean_label_data(label) for label in labels["nodes"] if label]


def _clean_issue_comments(issue_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Clean issue comments data"""
    comments = issue_data.get("comments", {})
    if not comments or not comments.get("nodes"):
        return []

    return [clean_comment_data(comment) for comment in comments["nodes"] if comment]


def _clean_issue_attachments(issue_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Clean issue attachments data"""
    attachments = issue_data.get("attachments", {})
    if not attachments or not attachments.get("nodes"):
        return []

    return [clean_attachment_data(attachment) for attachment in attachments["nodes"] if attachment]


def clean_issue_data(issue_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format issue data for consistent output"""
    if not issue_data:
        return {}

    # Clean basic issue data
    cleaned_issue = {
        "id": issue_data.get("id"),
        "identifier": issue_data.get("identifier"),
        "title": issue_data.get("title"),
        "description": issue_data.get("description"),
        "priority": issue_data.get("priority"),
        "priority_label": issue_data.get("priorityLabel"),
        "estimate": issue_data.get("estimate"),
        "sort_order": issue_data.get("sortOrder"),
        "created_at": issue_data.get("createdAt"),
        "updated_at": issue_data.get("updatedAt"),
        "completed_at": issue_data.get("completedAt"),
        "canceled_at": issue_data.get("canceledAt"),
        "due_date": issue_data.get("dueDate"),
        "url": issue_data.get("url"),
        "branch_name": issue_data.get("branchName"),
        "creator": clean_user_data(issue_data.get("creator", {})),
        "assignee": clean_user_data(issue_data.get("assignee", {})),
        "state": clean_state_data(issue_data.get("state", {})),
        "team": clean_team_data(issue_data.get("team", {})),
        "project": clean_project_data(issue_data.get("project", {})),
        "parent": clean_issue_data(issue_data.get("parent", {}))
        if issue_data.get("parent")
        else None,
        "labels": _clean_issue_labels(issue_data),
        "comments": _clean_issue_comments(issue_data),
        "attachments": _clean_issue_attachments(issue_data),
        "relations": _clean_issue_relations(issue_data),
        "children": _clean_issue_children(issue_data),
    }

    return remove_none_values(cleaned_issue)


def add_pagination_info(response: dict[str, Any], page_info: dict[str, Any]) -> dict[str, Any]:
    """Add pagination information to response"""
    response["pagination"] = {
        "has_next_page": page_info.get("hasNextPage", False),
        "has_previous_page": page_info.get("hasPreviousPage", False),
        "start_cursor": page_info.get("startCursor"),
        "end_cursor": page_info.get("endCursor"),
    }
    return response

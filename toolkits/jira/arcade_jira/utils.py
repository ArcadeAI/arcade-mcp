from datetime import date, datetime


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
        ("issue_type", issue_type),
        ("parent_issue", parent_issue),
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
        fields["assignee"] = {
            "name": fields["assignee"]["displayName"],
            "email": fields["assignee"]["emailAddress"],
        }

    if fields["creator"]:
        fields["creator"] = {
            "name": fields["creator"]["displayName"],
            "email": fields["creator"]["emailAddress"],
        }

    if fields["reporter"]:
        fields["reporter"] = {
            "name": fields["reporter"]["displayName"],
            "email": fields["reporter"]["emailAddress"],
        }

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


def clean_comment_dict(comment: dict) -> dict:
    return {
        "id": comment["id"],
        "author": {
            "name": comment["author"]["displayName"],
            "email": comment["author"]["emailAddress"],
        },
        "body": comment["body"]["content"],
        "created_at": comment["created"],
        "updated_at": comment["updated"],
    }


def clean_issue_type_dict(issue_type: dict) -> dict:
    data = {
        "id": issue_type["id"],
        "name": issue_type["name"],
        "description": issue_type["description"],
    }

    if "scope" in issue_type:
        data["scope"] = issue_type["scope"]

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

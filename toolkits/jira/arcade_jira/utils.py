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
    assignee: str | None = None,
    project: str | None = None,
    labels: list[str] | None = None,
) -> str:
    clauses: list[str] = []

    if keywords:
        kw_clauses = [f"text ~ {quote(k)}" for k in keywords.split()]
        clauses.append("(" + " AND ".join(kw_clauses) + ")")

    if due_from:
        clauses.append(f'duedate >= "{due_from.isoformat()}"')
    if due_until:
        clauses.append(f'duedate <= "{due_until.isoformat()}"')

    if status:
        clauses.append(f"status = {quote(status.value)}")

    if assignee:
        quotations = "" if assignee.isalnum() else quote(assignee)
        clauses.append(f"assignee = {quotations or assignee}")

    if project:
        clauses.append(f"project = {quote(project)}")

    if labels:
        label_list = ",".join(quote(label) for label in labels)
        clauses.append(f"labels IN ({label_list})")

    return " AND ".join(clauses) if clauses else ""


def clean_issue_dict(issue: dict) -> dict:
    fields = issue["fields"]

    fields["id"] = issue["id"]
    fields["key"] = issue["key"]

    fields["title"] = fields["summary"]

    fields["comments"] = {
        "items": fields["comment"]["comments"],
        "total": len(fields["comment"]["comments"]),
    }

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
    fields["is_subtask"] = fields["issuetype"]["subtask"]
    fields["priority"] = fields["priority"]["name"]

    if fields["project"]:
        fields["project"] = {
            "name": fields["project"]["name"],
            "id": fields["project"]["id"],
            "key": fields["project"]["key"],
        }

    if isinstance(fields.get("renderedFields"), dict):
        rendered = fields["renderedFields"]

        if rendered.get("description"):
            fields["description"] = rendered["description"]

        if rendered.get("comment", {}).get("comments"):
            fields["comments"] = rendered["comment"]["comments"]

        if rendered.get("worklog", {}).get("worklogs"):
            fields["worklog"] = rendered["worklog"]["worklogs"]

    del fields["summary"]
    del fields["comment"]
    del fields["assignee"]
    del fields["creator"]
    del fields["issuetype"]
    del fields["lastViewed"]
    del fields["updated"]
    del fields["statusCategory"]
    del fields["statuscategorychangedate"]
    del fields["votes"]
    del fields["watches"]
    del fields["renderedFields"]

    return fields

from datetime import date, datetime


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from the dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def convert_date_string_to_date(date_string: str) -> date:
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def quote(v: str) -> str:
    return f'"{v.replace('"', '\\"')}"'


def build_search_issues_jql(
    keywords: list[str] | None = None,
    due_from: date | None = None,
    due_until: date | None = None,
    start_from: date | None = None,
    start_until: date | None = None,
    statuses: list[str] | None = None,
    assignee: str | None = None,
    projects: list[str] | None = None,
    labels: list[str] | None = None,
) -> str:
    clauses: list[str] = []

    if keywords:
        kw_clauses = [f"text ~ {quote(k)}" for k in keywords]
        clauses.append("(" + " AND ".join(kw_clauses) + ")")

    if due_from:
        clauses.append(f'duedate >= "{due_from.isoformat()}"')
    if due_until:
        clauses.append(f'duedate <= "{due_until.isoformat()}"')

    if start_from:
        clauses.append(f'"Start date" >= "{start_from.isoformat()}"')
    if start_until:
        clauses.append(f'"Start date" <= "{start_until.isoformat()}"')

    if statuses:
        status_list = ",".join(quote(s) for s in statuses)
        clauses.append(f"status IN ({status_list})")

    if assignee:
        quotations = "" if assignee.isalnum() else quote(assignee)
        clauses.append(f"assignee = {quotations or assignee}")

    if projects:
        proj_list = ",".join(quote(p) for p in projects)
        clauses.append(f"project IN ({proj_list})")

    if labels:
        label_list = ",".join(quote(label) for label in labels)
        clauses.append(f"labels IN ({label_list})")

    return " AND ".join(clauses) if clauses else ""

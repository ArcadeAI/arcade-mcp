from typing import Any

from arcade_asana.constants import TASK_OPT_FIELDS


def remove_none_values(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def build_task_search_query_params(
    keywords: str,
    completed: bool,
    assignee_ids: list[str] | None,
    project_ids: list[str] | None,
    team_ids: list[str] | None,
    tags: list[str] | None,
    due_on: str | None,
    due_on_or_after: str | None,
    due_on_or_before: str | None,
    start_on: str | None,
    start_on_or_after: str | None,
    start_on_or_before: str | None,
) -> dict[str, Any]:
    query_params = {
        "text": keywords,
        "opt_fields": TASK_OPT_FIELDS,
        "completed": completed,
    }
    if assignee_ids:
        query_params["assignee.any"] = ",".join(assignee_ids)
    if project_ids:
        query_params["projects.any"] = ",".join(project_ids)
    if team_ids:
        query_params["team.any"] = ",".join(team_ids)
    if tags:
        query_params["tags.any"] = ",".join(tags)

    query_params = build_task_search_date_params(
        query_params,
        due_on,
        due_on_or_after,
        due_on_or_before,
        start_on,
        start_on_or_after,
        start_on_or_before,
    )

    return query_params


def build_task_search_date_params(
    query_params: dict,
    due_on: str,
    due_on_or_after: str,
    due_on_or_before: str,
    start_on: str,
    start_on_or_after: str,
    start_on_or_before: str,
) -> dict:
    if due_on:
        query_params["due_on"] = due_on
    if due_on_or_after:
        query_params["due_on.after"] = due_on_or_after
    if due_on_or_before:
        query_params["due_on.before"] = due_on_or_before
    if start_on:
        query_params["start_on"] = start_on
    if start_on_or_after:
        query_params["start_on.after"] = start_on_or_after
    if start_on_or_before:
        query_params["start_on.before"] = start_on_or_before

    return query_params

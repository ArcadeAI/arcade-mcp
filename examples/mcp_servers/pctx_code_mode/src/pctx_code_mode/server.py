#!/usr/bin/env python3
"""
ProjectTracker MCP server.

A project-management tool server with rich schemas: projects, sprints,
tasks (with subtasks, acceptance criteria, labels), comments, time entries,
and sprint velocity metrics.

Usage:
    uv run src/pctx_code_mode/server.py          # stdio (default)
    uv run src/pctx_code_mode/server.py http     # HTTP streaming
"""

import json
import sys
from typing import Annotated

from arcade_mcp_server import MCPApp
from pctx_client import tool as pctx_tool

from pctx_code_mode.store import get_store

app = MCPApp(name="ProjectTracker", version="1.0.0", log_level="WARNING")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def create_project(
    name: Annotated[str, "Project name (1-120 characters)"],
    description: Annotated[str, "Full project description including goals and scope"],
    owner_id: Annotated[str, "User ID of the project owner"],
    status: Annotated[
        str,
        "Initial project status: planning, active, on_hold, completed, archived",
    ] = "planning",
    tags: Annotated[
        str,
        "Comma-separated tags for categorisation (e.g. frontend,q1-2025,mobile)",
    ] = "",
    member_ids: Annotated[
        str,
        "Comma-separated user IDs of initial project members (owner is always included)",
    ] = "",
    settings: Annotated[
        str,
        (
            "JSON object with project-level settings. "
            'Supported keys: "velocity_unit" ("hours"|"points"), '
            '"sprint_length_days" (int), '
            '"default_priority" ("critical"|"high"|"medium"|"low"), '
            '"require_estimate" (bool), '
            '"review_required" (bool). '
            'Example: {"velocity_unit":"hours","sprint_length_days":14}'
        ),
    ] = "{}",
) -> dict:
    """
    Create a new project. Returns the full project record including the
    generated project_id needed for subsequent sprint and task operations.
    """
    store = get_store()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    member_list = list({owner_id} | {m.strip() for m in member_ids.split(",") if m.strip()})
    try:
        settings_dict = json.loads(settings) if settings.strip() else {}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid settings JSON: {exc}"}

    valid_statuses = {"planning", "active", "on_hold", "completed", "archived"}
    if status not in valid_statuses:
        return {"error": f"status must be one of {sorted(valid_statuses)}, got '{status}'"}

    project = store.create_project(
        name=name.strip(),
        description=description.strip(),
        owner_id=owner_id.strip(),
        status=status,
        tags=tag_list,
        settings=settings_dict,
        sprint_ids=[],
        member_ids=member_list,
    )
    return project.to_dict()


@pctx_tool
@app.tool
def get_project(
    project_id: Annotated[str, "ID of the project to retrieve"],
) -> dict:
    """Retrieve full project details including sprint IDs, member list, and settings."""
    store = get_store()
    project = store.get_project(project_id)
    if not project:
        return {"error": f"Project '{project_id}' not found"}
    return project.to_dict()


@pctx_tool
@app.tool
def list_projects(
    status_filter: Annotated[
        str,
        "Comma-separated statuses to include (e.g. active,planning). Empty = all statuses.",
    ] = "",
    owner_id: Annotated[str, "Filter to projects owned by this user ID. Empty = all owners."] = "",
    tag: Annotated[str, "Return only projects that include this tag. Empty = no filter."] = "",
    limit: Annotated[int, "Maximum number of projects to return (1-200)"] = 50,
) -> dict:
    """
    List projects with optional filtering. Returns {projects: [...], total, returned, filters}.
    Access the array via result.projects.
    """
    store = get_store()
    projects = list(store.projects.values())

    statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
    if statuses:
        projects = [p for p in projects if p.status in statuses]
    if owner_id.strip():
        projects = [p for p in projects if p.owner_id == owner_id.strip()]
    if tag.strip():
        projects = [p for p in projects if tag.strip() in p.tags]

    projects.sort(key=lambda p: p.updated_at, reverse=True)
    total = len(projects)
    projects = projects[:limit]

    return {
        "projects": [p.to_dict() for p in projects],
        "total": total,
        "returned": len(projects),
        "filters": {
            "status_filter": statuses or None,
            "owner_id": owner_id or None,
            "tag": tag or None,
        },
    }


# ---------------------------------------------------------------------------
# Sprints
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def create_sprint(
    project_id: Annotated[str, "ID of the parent project"],
    name: Annotated[str, "Sprint name (e.g. 'Sprint 2', 'Q2 2025 Hardening')"],
    start_date: Annotated[str, "Sprint start date in YYYY-MM-DD format"],
    end_date: Annotated[str, "Sprint end date in YYYY-MM-DD format"],
    goals: Annotated[
        str,
        "Comma-separated sprint goals. Each goal should be a concise, measurable outcome.",
    ] = "",
    capacity_hours: Annotated[
        float,
        "Total available team-hours for this sprint across all members. Used for utilisation metrics.",
    ] = 0.0,
) -> dict:
    """
    Create a new sprint inside an existing project. The sprint starts in
    'planning' status. Returns the full sprint record including the
    generated sprint_id needed for task creation.
    """
    store = get_store()
    project = store.get_project(project_id)
    if not project:
        return {"error": f"Project '{project_id}' not found"}

    goal_list = [g.strip() for g in goals.split(",") if g.strip()]
    sprint = store.create_sprint(
        project_id=project_id,
        name=name.strip(),
        status="planning",
        start_date=start_date.strip(),
        end_date=end_date.strip(),
        goals=goal_list,
        capacity_hours=max(0.0, capacity_hours),
        task_ids=[],
        retrospective_notes="",
    )
    return sprint.to_dict()


@pctx_tool
@app.tool
def get_sprint(
    sprint_id: Annotated[str, "ID of the sprint to retrieve"],
) -> dict:
    """Retrieve full sprint details including task IDs, goals, and status."""
    store = get_store()
    sprint = store.get_sprint(sprint_id)
    if not sprint:
        return {"error": f"Sprint '{sprint_id}' not found"}
    return sprint.to_dict()


@pctx_tool
@app.tool
def activate_sprint(
    sprint_id: Annotated[str, "ID of the sprint to move from planning to active"],
) -> dict:
    """
    Transition a sprint from 'planning' to 'active'. Only one sprint per
    project should be active at a time. Returns the updated sprint record.
    """
    store = get_store()
    sprint = store.get_sprint(sprint_id)
    if not sprint:
        return {"error": f"Sprint '{sprint_id}' not found"}
    if sprint.status != "planning":
        return {"error": f"Sprint is already '{sprint.status}', must be 'planning' to activate"}
    result = store.update_task  # just touching the store instance
    sprint.status = "active"
    from pctx_code_mode.store import _now
    sprint.updated_at = _now()
    return sprint.to_dict()


@pctx_tool
@app.tool
def close_sprint(
    sprint_id: Annotated[str, "ID of the active sprint to close"],
    carry_over_policy: Annotated[
        str,
        (
            "What to do with incomplete (non-done, non-cancelled) tasks: "
            "'next_sprint' moves them to another sprint, "
            "'backlog' detaches them from any sprint, "
            "'cancel' marks them as cancelled."
        ),
    ] = "backlog",
    next_sprint_id: Annotated[
        str,
        "Sprint ID to receive carried-over tasks. Required when carry_over_policy='next_sprint'.",
    ] = "",
    retrospective_notes: Annotated[
        str,
        "Free-form retrospective text (what went well, what to improve, action items).",
    ] = "",
) -> dict:
    """
    Close a sprint and handle incomplete tasks per the carry-over policy.
    Returns {sprint, summary: {total_tasks, completed_tasks, carried_over_tasks, cancelled_tasks, completion_rate}, carry_over_task_ids, carry_over_policy}.
    """
    store = get_store()
    sprint = store.get_sprint(sprint_id)
    if not sprint:
        return {"error": f"Sprint '{sprint_id}' not found"}

    valid_policies = {"next_sprint", "backlog", "cancel"}
    if carry_over_policy not in valid_policies:
        return {"error": f"carry_over_policy must be one of {sorted(valid_policies)}"}

    if carry_over_policy == "next_sprint" and not next_sprint_id.strip():
        return {"error": "next_sprint_id is required when carry_over_policy='next_sprint'"}

    tasks = [store.tasks[tid] for tid in sprint.task_ids if tid in store.tasks]
    incomplete = [t for t in tasks if t.status not in ("done", "cancelled")]
    completed = [t for t in tasks if t.status == "done"]

    from pctx_code_mode.store import _now
    now = _now()

    carry_over_ids: list[str] = []
    for task in incomplete:
        if carry_over_policy == "next_sprint":
            target = store.sprints.get(next_sprint_id.strip())
            if target and task.task_id not in target.task_ids:
                target.task_ids.append(task.task_id)
            task.sprint_id = next_sprint_id.strip() or None
            carry_over_ids.append(task.task_id)
        elif carry_over_policy == "backlog":
            task.sprint_id = None
            task.status = "backlog"
            carry_over_ids.append(task.task_id)
        else:  # cancel
            task.status = "cancelled"

        task.updated_at = now

    sprint.status = "completed"
    sprint.retrospective_notes = retrospective_notes
    sprint.updated_at = now

    return {
        "sprint": sprint.to_dict(),
        "summary": {
            "total_tasks": len(tasks),
            "completed_tasks": len(completed),
            "carried_over_tasks": len(carry_over_ids),
            "cancelled_tasks": len(incomplete) - len(carry_over_ids),
            "completion_rate": round(len(completed) / len(tasks), 4) if tasks else 0.0,
        },
        "carry_over_task_ids": carry_over_ids,
        "carry_over_policy": carry_over_policy,
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def create_task(
    sprint_id: Annotated[str, "ID of the sprint this task belongs to. Use 'backlog' to create an unsprinted task."],
    title: Annotated[str, "Short, imperative task title (1-200 characters)"],
    description: Annotated[
        str,
        "Detailed description including context, technical notes, and definition of done.",
    ],
    priority: Annotated[
        str,
        "Task priority: critical (P0), high (P1), medium (P2), low (P3)",
    ] = "medium",
    assignee_id: Annotated[
        str,
        "User ID to assign immediately. Leave empty to leave unassigned.",
    ] = "",
    labels: Annotated[
        str,
        "Comma-separated labels (e.g. bug,frontend,needs-design,blocked). Max 10 labels.",
    ] = "",
    estimate_hours: Annotated[
        float,
        "Hour estimate for completing the task. Use 0 if not yet estimated.",
    ] = 0.0,
    parent_task_id: Annotated[
        str,
        "ID of an existing task to nest this as a subtask under. Leave empty for a top-level task.",
    ] = "",
    acceptance_criteria: Annotated[
        str,
        (
            "JSON array of acceptance-criteria strings. Each entry is a testable condition. "
            'Example: ["API returns 200 on success", "Error state shows toast notification"]'
        ),
    ] = "[]",
) -> dict:
    """
    Create a new task (or subtask) inside a sprint. Returns the full task
    record including the generated task_id.
    """
    store = get_store()

    valid_priorities = {"critical", "high", "medium", "low"}
    if priority not in valid_priorities:
        return {"error": f"priority must be one of {sorted(valid_priorities)}, got '{priority}'"}

    actual_sprint_id: str | None = None
    if sprint_id.strip() and sprint_id.strip() != "backlog":
        sprint = store.get_sprint(sprint_id.strip())
        if not sprint:
            return {"error": f"Sprint '{sprint_id}' not found"}
        actual_sprint_id = sprint_id.strip()
        project_id = sprint.project_id
    elif parent_task_id.strip():
        parent = store.get_task(parent_task_id.strip())
        if not parent:
            return {"error": f"Parent task '{parent_task_id}' not found"}
        project_id = parent.project_id
        actual_sprint_id = parent.sprint_id
    else:
        return {"error": "Either a valid sprint_id or a parent_task_id is required"}

    label_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()][:10]

    try:
        criteria = json.loads(acceptance_criteria) if acceptance_criteria.strip() else []
        if not isinstance(criteria, list):
            criteria = []
    except json.JSONDecodeError:
        criteria = []

    task = store.create_task(
        sprint_id=actual_sprint_id,
        project_id=project_id,
        title=title.strip(),
        description=description.strip(),
        status="backlog",
        priority=priority,
        assignee_id=assignee_id.strip() or None,
        labels=label_list,
        estimate_hours=max(0.0, estimate_hours),
        parent_task_id=parent_task_id.strip() or None,
        acceptance_criteria=criteria,
    )
    return task.to_dict()


@pctx_tool
@app.tool
def get_task(
    task_id: Annotated[str, "ID of the task to retrieve"],
) -> dict:
    """
    Retrieve full task details including description, acceptance criteria,
    subtask IDs, comment count, and time-log summary.
    """
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}
    d = task.to_dict(include_full=True)
    # Inline subtask summaries for convenience
    d["subtasks"] = [
        store.tasks[sid].to_dict(include_full=False)
        for sid in task.subtask_ids
        if sid in store.tasks
    ]
    # Inline recent comments (last 5)
    d["recent_comments"] = [
        store.comments[cid].to_dict()
        for cid in task.comment_ids[-5:]
        if cid in store.comments
    ]
    # Time entry summary
    entries = [store.time_entries[eid] for eid in task.time_entry_ids if eid in store.time_entries]
    d["time_log"] = {
        "total_logged_hours": task.logged_hours,
        "entry_count": len(entries),
        "entries": [e.to_dict() for e in entries[-10:]],
    }
    return d


@pctx_tool
@app.tool
def update_task(
    task_id: Annotated[str, "ID of the task to update"],
    title: Annotated[str, "New title. Empty string = no change."] = "",
    description: Annotated[str, "New description. Empty string = no change."] = "",
    status: Annotated[
        str,
        "New status: backlog, todo, in_progress, in_review, done, cancelled. Empty = no change.",
    ] = "",
    priority: Annotated[
        str,
        "New priority: critical, high, medium, low. Empty = no change.",
    ] = "",
    assignee_id: Annotated[
        str,
        "New assignee user ID. Pass 'unassign' to remove the current assignee. Empty = no change.",
    ] = "",
    labels: Annotated[
        str,
        "Replacement comma-separated labels. Overwrites existing labels. Empty = no change.",
    ] = "",
    estimate_hours: Annotated[
        float,
        "Updated hour estimate. Pass -1 to clear the estimate. 0 = no change.",
    ] = 0.0,
) -> dict:
    """
    Update one or more fields of an existing task. Only non-empty / non-zero
    arguments are applied. Returns {task: <full task object>, changes: {field: {from, to}}}.
    Access the updated task via result.task, e.g. result.task.status.
    """
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    updates: dict = {}

    if title.strip():
        updates["title"] = title.strip()
    if description.strip():
        updates["description"] = description.strip()

    valid_statuses = {"backlog", "todo", "in_progress", "in_review", "done", "cancelled"}
    if status.strip():
        if status.strip() not in valid_statuses:
            return {"error": f"status must be one of {sorted(valid_statuses)}"}
        updates["status"] = status.strip()

    valid_priorities = {"critical", "high", "medium", "low"}
    if priority.strip():
        if priority.strip() not in valid_priorities:
            return {"error": f"priority must be one of {sorted(valid_priorities)}"}
        updates["priority"] = priority.strip()

    if assignee_id.strip():
        updates["assignee_id"] = None if assignee_id.strip() == "unassign" else assignee_id.strip()

    if labels.strip():
        updates["labels"] = [lbl.strip() for lbl in labels.split(",") if lbl.strip()][:10]

    if estimate_hours == -1:
        updates["estimate_hours"] = 0.0
    elif estimate_hours > 0:
        updates["estimate_hours"] = estimate_hours

    if not updates:
        return {"task": task.to_dict(), "changes": {}, "message": "No changes applied"}

    result = store.update_task(task_id, updates)
    if result is None:
        return {"error": f"Task '{task_id}' disappeared during update"}

    updated_task, changes = result
    return {"task": updated_task.to_dict(), "changes": changes}


@pctx_tool
@app.tool
def move_task(
    task_id: Annotated[str, "ID of the task to relocate"],
    target_sprint_id: Annotated[
        str,
        "Sprint ID to move the task into. Pass 'backlog' to detach from any sprint.",
    ],
    new_status: Annotated[
        str,
        "Optional new status after move: backlog, todo, in_progress, in_review, done, cancelled. Empty = keep current status.",
    ] = "",
) -> dict:
    """
    Move a task from its current sprint to a different sprint (or backlog).
    Optionally update its status at the same time. Returns {task, moved_from, moved_to}.
    """
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    old_sprint_id = task.sprint_id

    if target_sprint_id.strip() == "backlog":
        # Remove from current sprint
        if old_sprint_id and old_sprint_id in store.sprints:
            sprint = store.sprints[old_sprint_id]
            sprint.task_ids = [tid for tid in sprint.task_ids if tid != task_id]
        task.sprint_id = None
    else:
        target = store.get_sprint(target_sprint_id.strip())
        if not target:
            return {"error": f"Target sprint '{target_sprint_id}' not found"}
        # Remove from old sprint
        if old_sprint_id and old_sprint_id in store.sprints:
            old_sprint = store.sprints[old_sprint_id]
            old_sprint.task_ids = [tid for tid in old_sprint.task_ids if tid != task_id]
        # Add to new sprint
        if task_id not in target.task_ids:
            target.task_ids.append(task_id)
        task.sprint_id = target_sprint_id.strip()

    updates: dict = {}
    if new_status.strip():
        valid = {"backlog", "todo", "in_progress", "in_review", "done", "cancelled"}
        if new_status.strip() not in valid:
            return {"error": f"new_status must be one of {sorted(valid)}"}
        updates["status"] = new_status.strip()

    from pctx_code_mode.store import _now
    task.updated_at = _now()

    if updates:
        store.update_task(task_id, updates)

    return {
        "task": task.to_dict(),
        "moved_from": old_sprint_id,
        "moved_to": task.sprint_id,
    }


@pctx_tool
@app.tool
def add_subtask(
    parent_task_id: Annotated[str, "ID of the parent task to attach this subtask to"],
    title: Annotated[str, "Short subtask title"],
    description: Annotated[str, "Subtask description"] = "",
    assignee_id: Annotated[str, "User ID to assign this subtask to"] = "",
    estimate_hours: Annotated[float, "Hour estimate for this subtask"] = 0.0,
    priority: Annotated[str, "Priority: critical, high, medium, low"] = "medium",
) -> dict:
    """
    Create a subtask nested under an existing task. The subtask inherits
    the parent's sprint and project. Returns the full subtask record.
    """
    store = get_store()
    parent = store.get_task(parent_task_id)
    if not parent:
        return {"error": f"Parent task '{parent_task_id}' not found"}

    valid_priorities = {"critical", "high", "medium", "low"}
    if priority not in valid_priorities:
        return {"error": f"priority must be one of {sorted(valid_priorities)}"}

    task = store.create_task(
        sprint_id=parent.sprint_id,
        project_id=parent.project_id,
        title=title.strip(),
        description=description.strip(),
        status="backlog",
        priority=priority,
        assignee_id=assignee_id.strip() or None,
        labels=[],
        estimate_hours=max(0.0, estimate_hours),
        parent_task_id=parent_task_id,
        acceptance_criteria=[],
    )
    return {
        "subtask": task.to_dict(),
        "parent_task_id": parent_task_id,
        "parent_subtask_count": len(parent.subtask_ids),
    }


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def add_comment(
    task_id: Annotated[str, "ID of the task to comment on"],
    author_id: Annotated[str, "User ID of the comment author"],
    body: Annotated[str, "Comment body (Markdown supported)"],
    attachments: Annotated[
        str,
        (
            "JSON array of attachment objects. "
            'Each object must have "name" (string) and "url" (string). '
            'Example: [{"name": "screenshot.png", "url": "https://..."}]'
        ),
    ] = "[]",
) -> dict:
    """
    Add a comment to a task. Returns the created comment record and the
    updated comment count on the task.
    """
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}

    try:
        attachment_list = json.loads(attachments) if attachments.strip() else []
        if not isinstance(attachment_list, list):
            attachment_list = []
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid attachments JSON: {exc}"}

    comment = store.add_comment(
        task_id=task_id,
        author_id=author_id.strip(),
        body=body.strip(),
        attachments=attachment_list,
    )
    if comment is None:
        return {"error": f"Task '{task_id}' not found"}

    return {
        "comment": comment.to_dict(),
        "task_comment_count": len(task.comment_ids),
    }


# ---------------------------------------------------------------------------
# Time tracking
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def log_time(
    task_id: Annotated[str, "ID of the task to log time against"],
    user_id: Annotated[str, "User ID performing the work"],
    hours: Annotated[float, "Hours worked (e.g. 1.5 = 1 hour 30 minutes). Must be > 0."],
    description: Annotated[str, "Brief description of the work done in this session"],
    work_date: Annotated[
        str,
        "Date the work was performed in YYYY-MM-DD format. Use today's date if unsure.",
    ] = "",
) -> dict:
    """
    Record a time entry on a task. Accumulates into the task's logged_hours.
    Returns the time entry and updated hour totals for the task and its sprint.
    """
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        return {"error": f"Task '{task_id}' not found"}
    if hours <= 0:
        return {"error": "hours must be greater than 0"}

    from datetime import date
    effective_date = work_date.strip() if work_date.strip() else date.today().isoformat()

    entry = store.log_time(
        task_id=task_id,
        user_id=user_id.strip(),
        hours=hours,
        description=description.strip(),
        work_date=effective_date,
    )
    if entry is None:
        return {"error": f"Task '{task_id}' not found"}

    # Sprint total
    sprint_logged = 0.0
    if task.sprint_id and task.sprint_id in store.sprints:
        sprint = store.sprints[task.sprint_id]
        sprint_tasks = [store.tasks[tid] for tid in sprint.task_ids if tid in store.tasks]
        sprint_logged = sum(t.logged_hours for t in sprint_tasks)

    return {
        "entry": entry.to_dict(),
        "task_total_logged_hours": task.logged_hours,
        "sprint_total_logged_hours": round(sprint_logged, 2),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def get_sprint_metrics(
    sprint_id: Annotated[str, "ID of the sprint to analyse"],
    include_burndown: Annotated[
        bool,
        "Include daily burndown data points (ideal vs actual remaining hours)",
    ] = True,
    include_task_breakdown: Annotated[
        bool,
        "Include task counts segmented by status and priority, plus top-contributor list",
    ] = True,
) -> dict:
    """
    Compute velocity, completion rate, utilisation, burndown, and task
    breakdowns for a sprint. Ideal for generating progress reports or
    deciding whether to close/extend a sprint.
    """
    store = get_store()
    metrics = store.compute_sprint_metrics(
        sprint_id=sprint_id,
        include_burndown=include_burndown,
        include_task_breakdown=include_task_breakdown,
    )
    if metrics is None:
        return {"error": f"Sprint '{sprint_id}' not found"}
    return metrics


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@pctx_tool
@app.tool
def search_tasks(
    query: Annotated[
        str,
        "Full-text search across task titles and descriptions. Leave empty for no text filter.",
    ] = "",
    project_id: Annotated[str, "Restrict to tasks in this project. Empty = all projects."] = "",
    sprint_id: Annotated[str, "Restrict to tasks in this sprint. Empty = all sprints."] = "",
    assignee_id: Annotated[str, "Only return tasks assigned to this user ID."] = "",
    status: Annotated[
        str,
        "Comma-separated statuses to include (e.g. in_progress,in_review). Empty = all.",
    ] = "",
    priority: Annotated[
        str,
        "Comma-separated priorities to include (e.g. critical,high). Empty = all.",
    ] = "",
    labels: Annotated[
        str,
        "Comma-separated labels; returns tasks that have ALL of them. Empty = no label filter.",
    ] = "",
    has_estimate: Annotated[bool, "If True, only return tasks that have an estimate set (> 0)."] = False,
    is_overdue: Annotated[
        bool,
        "If True, only return incomplete tasks whose sprint has passed its end_date.",
    ] = False,
    sort_by: Annotated[
        str,
        "Sort field: updated_at (default), created_at, priority, estimate_hours",
    ] = "updated_at",
    limit: Annotated[int, "Maximum results to return (1-100)"] = 20,
) -> dict:
    """
    Search tasks across the entire store with fine-grained filters.
    Returns a list of task summaries (without full description/criteria),
    total count, and the filters that were applied.
    """
    store = get_store()

    statuses = [s.strip() for s in status.split(",") if s.strip()]
    priorities = [p.strip() for p in priority.split(",") if p.strip()]
    label_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()]

    valid_sort = {"updated_at", "created_at", "priority", "estimate_hours"}
    if sort_by not in valid_sort:
        sort_by = "updated_at"

    return store.search_tasks(
        query=query.strip(),
        project_id=project_id.strip(),
        sprint_id=sprint_id.strip(),
        assignee_id=assignee_id.strip(),
        statuses=statuses,
        priorities=priorities,
        labels=label_list,
        has_estimate=has_estimate,
        is_overdue=is_overdue,
        sort_by=sort_by,
        limit=max(1, min(100, limit)),
    )


# ---------------------------------------------------------------------------
# pctx Tool registry
#
# All tools are decorated with @pctx_tool (above @app.tool), so each name
# below is a pctx_client.Tool instance.  Consumers that want direct Code Mode
# access without going through the MCP transport can do:
#
#   from pctx_code_mode.server import pctx_tools
#   async with Pctx(tools=pctx_tools, url=...) as pctx:
#       result = await pctx.execute_typescript("...")
# ---------------------------------------------------------------------------

pctx_tools = [
    create_project,
    get_project,
    list_projects,
    create_sprint,
    get_sprint,
    activate_sprint,
    close_sprint,
    create_task,
    get_task,
    update_task,
    move_task,
    add_subtask,
    add_comment,
    log_time,
    get_sprint_metrics,
    search_tasks,
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    transport = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARCADE_SERVER_TRANSPORT", "stdio")
    host = os.environ.get("ARCADE_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("ARCADE_SERVER_PORT", "8000"))
    app.run(transport=transport, host=host, port=port)
"""Attio activity operations - notes and tasks."""

from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_attio.tools.records import _attio_request


@tool(requires_secrets=["ATTIO_API_KEY"])
async def create_note(
    context: ToolContext,
    parent_object: Annotated[str, "Object slug: 'people', 'companies', or 'deals'"],
    parent_record_id: Annotated[str, "Record UUID to attach note to"],
    title: Annotated[str, "Note title"],
    content: Annotated[str, "Note body text"],
    format_type: Annotated[str, "'plaintext' or 'markdown'"] = "plaintext",
) -> Annotated[dict, "Created note info"]:
    """
    Add a note to an Attio record.

    Notes are useful for logging activities, meeting notes, and outreach history.
    """
    body = {
        "data": {
            "parent_object": parent_object,
            "parent_record_id": parent_record_id,
            "title": title,
            "content": content,
            "format": format_type,
        }
    }

    response = await _attio_request("POST", "/notes", body)
    note = response.get("data", {})

    return {
        "note_id": note.get("id", {}).get("note_id", ""),
        "status": "created",
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def create_task(
    context: ToolContext,
    content: Annotated[str, "Task description"],
    assignee_id: Annotated[str, "Workspace member UUID (required by Attio API)"],
    deadline: Annotated[
        str, "Due date in ISO format (e.g., '2026-01-20T00:00:00.000Z') - REQUIRED"
    ],
    linked_records: Annotated[
        list[dict] | None,
        "Records to link: [{'target_object': 'companies', 'target_record_id': '...'}]",
    ] = None,
) -> Annotated[dict, "Created task info"]:
    """
    Create a task in Attio linked to record(s).

    Tasks are useful for follow-ups, reminders, and action items.
    Note: Attio API requires deadline_at to be set.
    """
    body = {
        "data": {
            "content": content,
            "format": "plaintext",
            "is_completed": False,
            "deadline_at": deadline,
            "assignees": [
                {"referenced_actor_type": "workspace-member", "referenced_actor_id": assignee_id}
            ],
            "linked_records": linked_records or [],
        }
    }

    response = await _attio_request("POST", "/tasks", body)
    task = response.get("data", {})

    return {
        "task_id": task.get("id", {}).get("task_id", ""),
        "status": "created",
        "deadline": deadline,
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def list_tasks(
    context: ToolContext,
    assignee_id: Annotated[str | None, "Filter by assignee UUID"] = None,
    is_completed: Annotated[bool | None, "Filter by completion status"] = None,
    limit: Annotated[int, "Max tasks to return"] = 50,
) -> Annotated[dict, "Tasks with optional filtering"]:
    """
    Get tasks from Attio with optional filtering.

    Can filter by assignee and/or completion status.
    """
    params = [f"limit={limit}"]
    if assignee_id:
        params.append(f"assignee={assignee_id}")
    if is_completed is not None:
        params.append(f"is_completed={str(is_completed).lower()}")

    query = "&".join(params)
    response = await _attio_request("GET", f"/tasks?{query}")

    tasks = []
    for t in response.get("data", []):
        tasks.append({
            "task_id": t.get("id", {}).get("task_id", ""),
            "content": t.get("content", ""),
            "deadline": t.get("deadline_at"),
            "is_completed": t.get("is_completed", False),
        })

    return {"total": len(tasks), "tasks": tasks}

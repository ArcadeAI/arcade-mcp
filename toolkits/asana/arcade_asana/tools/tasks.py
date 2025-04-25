from datetime import datetime
from typing import Annotated, Any

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2
from arcade.sdk.errors import ToolExecutionError

from arcade_asana.models import AsanaClient
from arcade_asana.utils import remove_none_values


@tool(requires_auth=OAuth2(id="arcade-asana", scopes=["tasks:write"]))
async def create_task(
    context: ToolContext,
    name: Annotated[str, "The name of the task"],
    start_date: Annotated[
        str | None, "The start date of the task in the format YYYY-MM-DD. Example: '2025-01-01'."
    ] = None,
    due_date: Annotated[
        str | None, "The due date of the task in the format YYYY-MM-DD. Example: '2025-01-01'."
    ] = None,
    description: Annotated[str | None, "The description of the task."] = None,
    parent_task_id: Annotated[str | None, "The ID of the parent task."] = None,
    workspace_id: Annotated[str | None, "The ID of the workspace to associate the task to."] = None,
    project_ids: Annotated[
        list[str] | None, "The IDs of the projects to associate the task to."
    ] = None,
    assignee_id: Annotated[
        str | None,
        "The ID of the user to assign the task to. "
        "Provide 'me' to assign the task to the current user.",
    ] = None,
    tags: Annotated[list[str] | None, "The tags to associate with the task."] = None,
) -> Annotated[
    dict[str, Any],
    "Creates a task in Asana",
]:
    """Creates a task in Asana"""
    client = AsanaClient(context.get_auth_token_or_empty())

    try:
        datetime.strptime(due_date, "%Y-%m-%d")
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise ToolExecutionError(
            "Invalid date format. Use the format YYYY-MM-DD for both start_date and due_date."
        )

    if assignee_id == "me":
        assignee_id = await client.get_current_user()["gid"]

    task_data = {
        "name": name,
        "due_date": due_date,
        "notes": description,
        "parent": parent_task_id,
        "projects": project_ids,
        "workspace": workspace_id,
        "assignee": assignee_id,
        "tags": tags,
    }

    response = await client.post("/tasks", json_data=remove_none_values(task_data))
    return {
        "status": {"success": True, "message": "task created successfully"},
        "task": response["data"],
    }

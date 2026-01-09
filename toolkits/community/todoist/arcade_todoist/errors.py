from arcade_tdk.errors import ToolExecutionError


class ProjectNotFoundError(ToolExecutionError):
    """Raised when a project is not found."""

    def __init__(self, project_name: str, partial_matches: list[str] | None = None):
        if partial_matches:
            matches_str = "', '".join(partial_matches)
            super().__init__(
                "Project not found",
                developer_message=(
                    f"Project '{project_name}' not found, but found partial matches: "
                    f"{matches_str}. "
                    f"Please specify the exact project name."
                ),
            )
        else:
            super().__init__(
                "Project not found",
                developer_message=(
                    f"Project '{project_name}' not found. "
                    f"Ask the user to create the project first."
                ),
            )


class TaskNotFoundError(ToolExecutionError):
    """Raised when a task is not found."""

    def __init__(self, task_description: str, partial_matches: list[str] | None = None):
        if partial_matches:
            matches_str = "', '".join(partial_matches)
            super().__init__(
                "Task not found",
                developer_message=(
                    f"Task '{task_description}' not found, but found partial matches: "
                    f"{matches_str}. "
                    f"Please specify the exact task description."
                ),
            )
        else:
            super().__init__(
                "Task not found", developer_message=f"Task '{task_description}' not found."
            )


class MultipleTasksFoundError(ToolExecutionError):
    """Raised when multiple tasks match the search criteria."""

    def __init__(self, task_description: str, task_matches: list[dict]):
        matches_str = "', '".join([task["content"] for task in task_matches])
        super().__init__(
            "Multiple tasks found",
            developer_message=(
                f"Multiple tasks found for '{task_description}': '{matches_str}'. "
                f"Please specify the exact task description to choose one."
            ),
        )

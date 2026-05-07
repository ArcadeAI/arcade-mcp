# ---------------------------------------------------------------------------
# Project Types
# ---------------------------------------------------------------------------
from typing import Any, Literal, TypedDict

ProjectStatus = Literal["planning", "active", "on_hold", "completed", "archived"]


class ProjectCreate(TypedDict):
    name: str
    description: str
    owner_id: str
    status: ProjectStatus
    tags: list[str]
    settings: dict[str, Any]
    sprint_ids: list[str]
    member_ids: list[str]


class Project(ProjectCreate):
    project_id: str
    created_at: str
    updated_at: str


class ListProjectsFilters(TypedDict):
    status_filter: list[str] | None
    owner_id: str | None
    tag: str | None


class ListProjectsResult(TypedDict):
    projects: list[Project]
    total: int
    returned: int
    filters: ListProjectsFilters


# ---------------------------------------------------------------------------
# Sprint Types
# ---------------------------------------------------------------------------


class SprintCreate(TypedDict):
    project_id: str
    name: str
    status: str  # planning | active | completed
    start_date: str
    end_date: str
    goals: list[str]
    capacity_hours: float
    task_ids: list[str]
    retrospective_notes: str


class Sprint(SprintCreate):
    sprint_id: str
    created_at: str
    updated_at: str


class CloseSprintSummary(TypedDict):
    total_tasks: int
    completed_tasks: int
    carried_over_tasks: int
    cancelled_tasks: int
    completion_rate: float


class CloseSprintResult(TypedDict):
    sprint: Sprint
    summary: CloseSprintSummary
    carry_over_task_ids: list[str]
    carry_over_policy: str


# ---------------------------------------------------------------------------
# Comment Types
# ---------------------------------------------------------------------------


class Comment(TypedDict):
    comment_id: str
    task_id: str
    author_id: str
    body: str
    attachments: list[dict[str, str]]
    created_at: str
    updated_at: str


class AddCommentResult(TypedDict):
    comment: Comment
    task_comment_count: int


# ---------------------------------------------------------------------------
# Task Types
# ---------------------------------------------------------------------------


class TaskCreate(TypedDict):
    sprint_id: str | None
    project_id: str
    title: str
    description: str
    status: str  # backlog | todo | in_progress | in_review | done | cancelled
    priority: str  # critical | high | medium | low
    assignee_id: str | None
    labels: list[str]
    estimate_hours: float
    parent_task_id: str | None
    acceptance_criteria: list[str]


class Task(TaskCreate):
    task_id: str
    subtask_ids: list[str]
    comment_ids: list[str]
    time_entry_ids: list[str]
    logged_hours: float
    created_at: str
    updated_at: str


class TimeEntry(TypedDict):
    entry_id: str
    task_id: str
    user_id: str
    hours: float
    description: str
    work_date: str
    created_at: str


class TimeLogSummary(TypedDict):
    total_logged_hours: float
    entry_count: int
    entries: list[TimeEntry]


class GetTaskResult(Task):
    subtasks: list[Task]
    recent_comments: list[Comment]
    time_log: TimeLogSummary


class UpdateTaskResult(TypedDict):
    task: Task
    changes: dict[str, Any]
    message: str | None


class MoveTaskResult(TypedDict):
    task: Task
    moved_from: str | None
    moved_to: str | None


class AddSubtaskResult(TypedDict):
    subtask: Task
    parent_task_id: str
    parent_subtask_count: int


class SearchTasksFilters(TypedDict):
    project_id: str | None
    sprint_id: str | None
    assignee_id: str | None
    statuses: list[str] | None
    priorities: list[str] | None
    labels: list[str] | None


class SearchTasksResult(TypedDict):
    tasks: list[Task]
    total: int
    returned: int
    filters_applied: SearchTasksFilters


# ---------------------------------------------------------------------------
# Log Time Types
# ---------------------------------------------------------------------------


class LogTimeResult(TypedDict):
    entry: TimeEntry
    task_total_logged_hours: float
    sprint_total_logged_hours: float

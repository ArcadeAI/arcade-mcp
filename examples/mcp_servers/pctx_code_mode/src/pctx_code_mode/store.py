"""
In-memory store for the ProjectTracker MCP server.

Seeded with stable demo data so evaluations can use predictable IDs.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, cast

from typing_extensions import Unpack

from pctx_code_mode.params import (
    Comment,
    Project,
    ProjectCreate,
    Sprint,
    SprintCreate,
    Task,
    TaskCreate,
    TimeEntry,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class ProjectStore:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.sprints: dict[str, Sprint] = {}
        self.tasks: dict[str, Task] = {}
        self.comments: dict[str, Comment] = {}
        self.time_entries: dict[str, TimeEntry] = {}
        self._seed()

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Pre-populate with stable demo data so evals have predictable IDs."""

        proj = Project(
            project_id="proj_webapp_001",
            name="WebApp Redesign",
            description=(
                "Full redesign of the customer-facing web application focusing on "
                "performance, accessibility (WCAG AA), and a modern design system."
            ),
            owner_id="user_alice",
            status="active",
            tags=["frontend", "ux", "q1-2025"],
            settings={
                "velocity_unit": "hours",
                "sprint_length_days": 14,
                "default_priority": "medium",
                "require_estimate": False,
                "review_required": True,
            },
            sprint_ids=["spr_001"],
            member_ids=["user_alice", "user_bob", "user_carol"],
            created_at="2025-01-01T09:00:00+00:00",
            updated_at="2025-01-15T14:30:00+00:00",
        )
        self.projects["proj_webapp_001"] = proj

        sprint = Sprint(
            sprint_id="spr_001",
            project_id="proj_webapp_001",
            name="Sprint 1 — Foundation",
            status="active",
            start_date="2025-01-13",
            end_date="2025-01-26",
            goals=[
                "Deliver responsive navigation component",
                "Complete hero section design and implementation",
                "Set up CI/CD pipeline",
            ],
            capacity_hours=80.0,
            task_ids=["task_001", "task_002", "task_003", "task_004"],
            retrospective_notes="",
            created_at="2025-01-10T08:00:00+00:00",
            updated_at="2025-01-13T09:00:00+00:00",
        )
        self.sprints["spr_001"] = sprint

        seed_tasks: list[Task] = [
            Task(
                task_id="task_001",
                sprint_id="spr_001",
                project_id="proj_webapp_001",
                title="Design hero section",
                description=(
                    "Create a responsive hero section with animated headline, "
                    "CTA button, and background illustration. Must pass WCAG AA."
                ),
                status="in_progress",
                priority="high",
                assignee_id="user_alice",
                labels=["design", "frontend", "wcag"],
                estimate_hours=8.0,
                parent_task_id=None,
                subtask_ids=[],
                acceptance_criteria=[
                    "Hero renders correctly at 320px, 768px, and 1440px breakpoints",
                    "CTA button has visible focus ring",
                    "Background image has meaningful alt text",
                    "Animation respects prefers-reduced-motion media query",
                ],
                comment_ids=[],
                time_entry_ids=[],
                logged_hours=3.5,
                created_at="2025-01-13T09:30:00+00:00",
                updated_at="2025-01-15T16:00:00+00:00",
            ),
            Task(
                task_id="task_002",
                sprint_id="spr_001",
                project_id="proj_webapp_001",
                title="Implement navigation component",
                description=(
                    "Build top navigation bar with responsive hamburger menu, "
                    "active-link highlighting, and full keyboard navigation support."
                ),
                status="todo",
                priority="medium",
                assignee_id="user_bob",
                labels=["frontend", "component", "a11y"],
                estimate_hours=6.0,
                parent_task_id=None,
                subtask_ids=[],
                acceptance_criteria=[
                    "Tab order is logical and follows visual flow",
                    "Hamburger menu closes on ESC key press",
                    "Active route is visually indicated with aria-current",
                ],
                comment_ids=[],
                time_entry_ids=[],
                logged_hours=0.0,
                created_at="2025-01-13T09:45:00+00:00",
                updated_at="2025-01-13T09:45:00+00:00",
            ),
            Task(
                task_id="task_003",
                sprint_id="spr_001",
                project_id="proj_webapp_001",
                title="Write unit tests for auth module",
                description=(
                    "Add comprehensive unit tests covering login, logout, "
                    "token refresh, session expiry, and all error states."
                ),
                status="backlog",
                priority="high",
                assignee_id=None,
                labels=["testing", "auth", "backend"],
                estimate_hours=5.0,
                parent_task_id=None,
                subtask_ids=[],
                acceptance_criteria=[
                    "Line coverage >= 90% on auth module",
                    "All happy paths and error states covered",
                    "Token expiry edge case explicitly tested",
                ],
                comment_ids=[],
                time_entry_ids=[],
                logged_hours=0.0,
                created_at="2025-01-13T10:00:00+00:00",
                updated_at="2025-01-13T10:00:00+00:00",
            ),
            Task(
                task_id="task_004",
                sprint_id="spr_001",
                project_id="proj_webapp_001",
                title="Fix mobile layout regression — Safari iOS",
                description=(
                    "Safari on iOS 17 clips the footer on pages with a sticky header. "
                    "Root cause is an overflow issue with the sticky positioning context."
                ),
                status="in_review",
                priority="critical",
                assignee_id="user_alice",
                labels=["bug", "mobile", "safari", "css"],
                estimate_hours=3.0,
                parent_task_id=None,
                subtask_ids=[],
                acceptance_criteria=[
                    "Footer fully visible on iPhone 12, 13, and 14 viewport",
                    "No horizontal scrollbar appears in Safari iOS",
                    "Regression test added to E2E suite",
                ],
                comment_ids=[],
                time_entry_ids=[],
                logged_hours=2.0,
                created_at="2025-01-14T11:00:00+00:00",
                updated_at="2025-01-15T09:00:00+00:00",
            ),
        ]

        for task in seed_tasks:
            self.tasks[task["task_id"]] = task

    # ------------------------------------------------------------------
    # Project helpers
    # ------------------------------------------------------------------

    def create_project(self, **kwargs: Unpack[ProjectCreate]) -> Project:
        project_id = _uid("proj")
        now = _now()
        proj: Project = {
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
        self.projects[project_id] = proj
        return proj

    def get_project(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    # ------------------------------------------------------------------
    # Sprint helpers
    # ------------------------------------------------------------------

    def create_sprint(self, **kwargs: Unpack[SprintCreate]) -> Sprint:
        sprint_id = _uid("spr")
        now = _now()
        sprint: Sprint = {
            "sprint_id": sprint_id,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
        self.sprints[sprint_id] = sprint
        proj = self.projects.get(sprint["project_id"])
        if proj:
            proj["sprint_ids"].append(sprint_id)
            proj["updated_at"] = now
        return sprint

    def get_sprint(self, sprint_id: str) -> Sprint | None:
        return self.sprints.get(sprint_id)

    # ------------------------------------------------------------------
    # Task helpers
    # ------------------------------------------------------------------

    def create_task(self, **kwargs: Unpack[TaskCreate]) -> Task:
        task_id = _uid("task")
        now = _now()
        task: Task = {
            "task_id": task_id,
            "comment_ids": [],
            "time_entry_ids": [],
            "subtask_ids": [],
            "logged_hours": 0.0,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
        self.tasks[task_id] = task
        # Register in sprint
        sprint = self.sprints.get(task.get("sprint_id") or "")
        if sprint:
            sprint["task_ids"].append(task_id)
            sprint["updated_at"] = now
        # Register as subtask on parent
        parent_id = task.get("parent_task_id")
        if parent_id:
            parent = self.tasks.get(parent_id)
            if parent:
                parent["subtask_ids"].append(task_id)
                parent["updated_at"] = now
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def update_task(
        self, task_id: str, updates: dict[str, Any]
    ) -> tuple[Task, dict[str, Any]] | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        task_dict = cast(dict[str, Any], task)
        changes: dict[str, Any] = {}
        for key, new_val in updates.items():
            old_val = task_dict.get(key)
            if old_val != new_val:
                changes[key] = {"from": old_val, "to": new_val}
                task_dict[key] = new_val
        task["updated_at"] = _now()
        return task, changes

    # ------------------------------------------------------------------
    # Comment helpers
    # ------------------------------------------------------------------

    def add_comment(
        self, task_id: str, author_id: str, body: str, attachments: list[dict[str, str]]
    ) -> Comment | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        comment_id = _uid("cmt")
        now = _now()
        comment = Comment(
            comment_id=comment_id,
            task_id=task_id,
            author_id=author_id,
            body=body,
            attachments=attachments,
            created_at=now,
            updated_at=now,
        )
        self.comments[comment_id] = comment
        task["comment_ids"].append(comment_id)
        task["updated_at"] = now
        return comment

    # ------------------------------------------------------------------
    # Time tracking helpers
    # ------------------------------------------------------------------

    def log_time(
        self, task_id: str, user_id: str, hours: float, description: str, work_date: str
    ) -> TimeEntry | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        entry_id = _uid("te")
        now = _now()
        entry = TimeEntry(
            entry_id=entry_id,
            task_id=task_id,
            user_id=user_id,
            hours=hours,
            description=description,
            work_date=work_date,
            created_at=now,
        )
        self.time_entries[entry_id] = entry
        task["time_entry_ids"].append(entry_id)
        task["logged_hours"] += hours
        task["updated_at"] = now
        return entry

    # ------------------------------------------------------------------
    # Sprint metrics
    # ------------------------------------------------------------------

    def compute_sprint_metrics(
        self, sprint_id: str, include_burndown: bool, include_task_breakdown: bool
    ) -> dict[str, Any] | None:
        sprint = self.sprints.get(sprint_id)
        if not sprint:
            return None

        tasks = [self.tasks[tid] for tid in sprint["task_ids"] if tid in self.tasks]
        total = len(tasks)
        done = sum(1 for t in tasks if t["status"] == "done")
        cancelled = sum(1 for t in tasks if t["status"] == "cancelled")
        carry_over = total - done - cancelled
        estimated = sum(t["estimate_hours"] for t in tasks)
        logged = sum(t["logged_hours"] for t in tasks)

        metrics: dict[str, Any] = {
            "sprint_id": sprint_id,
            "sprint_name": sprint["name"],
            "status": sprint["status"],
            "total_tasks": total,
            "completed_tasks": done,
            "cancelled_tasks": cancelled,
            "carry_over_tasks": carry_over,
            "completion_rate": round(done / total, 4) if total else 0.0,
            "hours_estimated": estimated,
            "hours_logged": logged,
            "velocity": logged,
            "capacity_hours": sprint["capacity_hours"],
            "utilization_rate": round(logged / sprint["capacity_hours"], 4)
            if sprint["capacity_hours"]
            else 0.0,
        }

        if include_burndown:
            # Synthetic burndown: linear ideal line vs stepwise actual
            metrics["burndown"] = [
                {
                    "date": sprint["start_date"],
                    "remaining_ideal": estimated,
                    "remaining_actual": estimated,
                },
                {
                    "date": sprint["end_date"],
                    "remaining_ideal": 0.0,
                    "remaining_actual": max(0.0, estimated - logged),
                },
            ]

        if include_task_breakdown:
            by_status: dict[str, int] = {}
            by_priority: dict[str, int] = {}
            for t in tasks:
                by_status[t["status"]] = by_status.get(t["status"], 0) + 1
                by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1

            # Contributor summary
            contributor_hours: dict[str, float] = {}
            contributor_done: dict[str, int] = {}
            for t in tasks:
                uid = t["assignee_id"] or "unassigned"
                contributor_hours[uid] = contributor_hours.get(uid, 0.0) + t["logged_hours"]
                if t["status"] == "done":
                    contributor_done[uid] = contributor_done.get(uid, 0) + 1

            metrics["task_breakdown"] = {
                "by_status": by_status,
                "by_priority": by_priority,
            }
            metrics["top_contributors"] = [
                {
                    "user_id": uid,
                    "hours_logged": round(contributor_hours[uid], 2),
                    "tasks_completed": contributor_done.get(uid, 0),
                }
                for uid in sorted(contributor_hours, key=lambda u: -contributor_hours[u])
            ]

        return metrics

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_tasks(
        self,
        *,
        query: str,
        project_id: str,
        sprint_id: str,
        assignee_id: str,
        statuses: list[str],
        priorities: list[str],
        labels: list[str],
        has_estimate: bool,
        is_overdue: bool,
        sort_by: str,
        limit: int,
    ) -> dict[str, Any]:
        results = list(self.tasks.values())

        if project_id:
            results = [t for t in results if t["project_id"] == project_id]
        if sprint_id:
            results = [t for t in results if t["sprint_id"] == sprint_id]
        if assignee_id:
            results = [t for t in results if t["assignee_id"] == assignee_id]
        if statuses:
            results = [t for t in results if t["status"] in statuses]
        if priorities:
            results = [t for t in results if t["priority"] in priorities]
        if labels:
            results = [t for t in results if all(lbl in t["labels"] for lbl in labels)]
        if has_estimate:
            results = [t for t in results if t["estimate_hours"] > 0]
        if is_overdue:
            results = [t for t in results if t["status"] not in ("done", "cancelled")]
        if query:
            q = query.lower()
            results = [
                t for t in results if q in t["title"].lower() or q in t["description"].lower()
            ]

        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if sort_by == "priority":
            results.sort(key=lambda t: priority_order.get(t["priority"], 99))
        elif sort_by == "estimate_hours":
            results.sort(key=lambda t: -t["estimate_hours"])
        elif sort_by == "created_at":
            results.sort(key=lambda t: t["created_at"], reverse=True)
        else:
            results.sort(key=lambda t: t["updated_at"], reverse=True)

        total = len(results)
        results = results[:limit]

        return {
            "tasks": [dict(t) for t in results],
            "total": total,
            "returned": len(results),
            "filters_applied": {
                "project_id": project_id or None,
                "sprint_id": sprint_id or None,
                "assignee_id": assignee_id or None,
                "statuses": statuses or None,
                "priorities": priorities or None,
                "labels": labels or None,
            },
        }


# Module-level singleton so all tool calls share the same state
_store = ProjectStore()


def get_store() -> ProjectStore:
    return _store

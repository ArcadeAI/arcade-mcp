"""
ProjectTracker MCP tool-selection evaluations (direct MCP — no Code Mode).

Tests that an LLM picks the correct MCP tool and arguments across chains of
1–8 steps. This benchmark does NOT use pctx Code Mode; the model calls tools
directly. For the Code Mode benchmark see eval_pctx_code_mode_live.py.

Workflows:
  1. project_setup       – 3 steps: create project → sprint → task
  2. task_lifecycle      – 5 steps: get → comment → log time → review → done
  3. sprint_management   – 6 steps: list → get sprint → create → move → metrics → search
  4. full_sprint_cycle   – 8 steps: full lifecycle using every tool

Run:
    OPENAI_BASE_URL=https://openrouter.ai/api/v1 \\
    arcade evals examples/evals/eval_project_tracker_mcp.py \\
        -p openai:gpt-4o \\
        -k openai:YOUR_KEY \\
        -d
"""

import asyncio
import json
import os

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedMCPToolCall,
    NumericCritic,
    SimilarityCritic,
    tool_eval,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXAMPLES_DIR = os.path.dirname(os.path.dirname(__file__))
SERVER_PATH = os.path.join(EXAMPLES_DIR, "mcp_servers", "pctx_code_mode")
SERVER_COMMAND = ["uv", "run", "--directory", SERVER_PATH, "src/pctx_code_mode/server.py"]

rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
    fail_on_tool_selection=True,
)


# ---------------------------------------------------------------------------
# Helpers – compact JSON strings for additional_messages tool responses
# ---------------------------------------------------------------------------


def _j(obj: dict) -> str:
    return json.dumps(obj)


# Fixed fake IDs used across suites (stable across runs)
_PROJ_PIPE = "proj_pipe_9f3a1b2c"
_SPR_PIPE = "spr_pipe_4d5e6f7a"

_PROJ_AUTH = "proj_auth_aa1122bb"
_SPR_AUTH = "spr_auth_cc3344dd"
_TASK_JWT = "task_jwt_ee5566ff"
_TASK_SUB = "task_sub_gg7788hh"


async def _load_server(suite: EvalSuite) -> bool:
    try:
        await asyncio.wait_for(
            suite.add_mcp_stdio_server(
                command=SERVER_COMMAND,
                env={"PYTHONUNBUFFERED": "1"},
            ),
            timeout=20.0,
        )
        print("  ✓ ProjectTracker MCP server loaded")
        return True
    except asyncio.TimeoutError:
        print("  ✗ Server load timed out")
    except Exception as exc:
        print(f"  ✗ Server load failed: {type(exc).__name__}: {exc}")
    return False


# ===========================================================================
# Suite 1 – Project Setup  (3-step chain)
# ===========================================================================


@tool_eval()
async def eval_project_setup() -> EvalSuite:
    """Create a project, a sprint inside it, then a task inside the sprint."""
    suite = EvalSuite(
        name="Project Setup (3-step chain)",
        system_message=(
            "You are a project-management assistant. "
            "Use the ProjectTracker tools to set up new projects and sprints."
        ),
        rubric=rubric,
    )
    if not await _load_server(suite):
        return suite

    # ------------------------------------------------------------------
    # Step 1 – create the project
    # ------------------------------------------------------------------
    suite.add_case(
        name="1/3 · Create project",
        user_message=(
            "Create a new project called 'Data Pipeline v2' owned by user_carol. "
            "Add tags: data,etl,infra. Set sprint length to 7 days in the settings."
        ),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateProject",
                args={
                    "name": "Data Pipeline v2",
                    "owner_id": "user_carol",
                    "tags": "data,etl,infra",
                    "settings": '{"sprint_length_days": 7}',
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="owner_id", weight=0.3),
            SimilarityCritic(critic_field="tags", weight=0.2),
            SimilarityCritic(critic_field="settings", weight=0.2),
        ],
    )

    # ------------------------------------------------------------------
    # Step 2 – create a sprint in the newly created project
    # ------------------------------------------------------------------
    proj_response = _j({
        "project_id": _PROJ_PIPE,
        "name": "Data Pipeline v2",
        "owner_id": "user_carol",
        "status": "planning",
        "tags": ["data", "etl", "infra"],
        "settings": {"sprint_length_days": 7},
        "sprint_count": 0,
        "created_at": "2025-04-01T09:00:00+00:00",
    })

    suite.add_case(
        name="2/3 · Create sprint in new project",
        user_message=(
            f"Now create Sprint 1 in project {_PROJ_PIPE} "
            "running from 2025-04-07 to 2025-04-14 with 40 hours capacity. "
            "Goals: 'Build Kafka ingestion layer,Deploy to staging'."
        ),
        additional_messages=[
            {
                "role": "user",
                "content": "Create a new project called 'Data Pipeline v2' owned by user_carol with tags data,etl,infra.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s1_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_CreateProject",
                            "arguments": '{"name":"Data Pipeline v2","owner_id":"user_carol","tags":"data,etl,infra","settings":"{\\"sprint_length_days\\":7}"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": proj_response,
                "tool_call_id": "call_s1_1",
                "name": "ProjectTracker_CreateProject",
            },
            {"role": "assistant", "content": f"Project created with ID `{_PROJ_PIPE}`."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateSprint",
                args={
                    "project_id": _PROJ_PIPE,
                    "name": "Sprint 1",
                    "start_date": "2025-04-07",
                    "end_date": "2025-04-14",
                    "capacity_hours": 40.0,
                    "goals": "Build Kafka ingestion layer,Deploy to staging",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="project_id", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.15),
            BinaryCritic(critic_field="end_date", weight=0.15),
            NumericCritic(critic_field="capacity_hours", weight=0.2, value_range=(35.0, 45.0)),
            SimilarityCritic(critic_field="goals", weight=0.2),
        ],
    )

    # ------------------------------------------------------------------
    # Step 3 – create a task inside the new sprint
    # ------------------------------------------------------------------
    sprint_response = _j({
        "sprint_id": _SPR_PIPE,
        "project_id": _PROJ_PIPE,
        "name": "Sprint 1",
        "status": "planning",
        "start_date": "2025-04-07",
        "end_date": "2025-04-14",
        "goals": ["Build Kafka ingestion layer", "Deploy to staging"],
        "capacity_hours": 40.0,
        "task_count": 0,
    })

    suite.add_case(
        name="3/3 · Create first task in sprint",
        user_message=(
            f"Add a high-priority task 'Implement Kafka consumer' to sprint {_SPR_PIPE}, "
            "assigned to user_dave, 6-hour estimate, labels: backend,kafka."
        ),
        additional_messages=[
            {
                "role": "user",
                "content": "Create a new project called 'Data Pipeline v2' owned by user_carol.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s1_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_CreateProject",
                            "arguments": '{"name":"Data Pipeline v2","owner_id":"user_carol"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": proj_response,
                "tool_call_id": "call_s1_1",
                "name": "ProjectTracker_CreateProject",
            },
            {"role": "assistant", "content": f"Project `{_PROJ_PIPE}` created."},
            {
                "role": "user",
                "content": f"Create Sprint 1 in {_PROJ_PIPE} from 2025-04-07 to 2025-04-14.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s1_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_CreateSprint",
                            "arguments": f'{{"project_id":"{_PROJ_PIPE}","name":"Sprint 1","start_date":"2025-04-07","end_date":"2025-04-14","capacity_hours":40.0}}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": sprint_response,
                "tool_call_id": "call_s1_2",
                "name": "ProjectTracker_CreateSprint",
            },
            {"role": "assistant", "content": f"Sprint `{_SPR_PIPE}` created."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateTask",
                args={
                    "sprint_id": _SPR_PIPE,
                    "title": "Implement Kafka consumer",
                    "priority": "high",
                    "assignee_id": "user_dave",
                    "estimate_hours": 6.0,
                    "labels": "backend,kafka",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.25),
            SimilarityCritic(critic_field="title", weight=0.2),
            BinaryCritic(critic_field="priority", weight=0.2),
            BinaryCritic(critic_field="assignee_id", weight=0.2),
            NumericCritic(critic_field="estimate_hours", weight=0.15, value_range=(5.0, 7.0)),
        ],
    )

    return suite


# ===========================================================================
# Suite 2 – Task Lifecycle  (5-step chain)
# ===========================================================================


@tool_eval()
async def eval_task_lifecycle() -> EvalSuite:
    """
    Work a task from in_progress through review to done using the seeded
    task_001 (Design hero section) in sprint spr_001.
    """
    suite = EvalSuite(
        name="Task Lifecycle (5-step chain)",
        system_message=(
            "You are a project-management assistant. "
            "Help move tasks through their workflow using ProjectTracker tools."
        ),
        rubric=rubric,
    )
    if not await _load_server(suite):
        return suite

    task_001 = _j({
        "task_id": "task_001",
        "sprint_id": "spr_001",
        "project_id": "proj_webapp_001",
        "title": "Design hero section",
        "status": "in_progress",
        "priority": "high",
        "assignee_id": "user_alice",
        "labels": ["design", "frontend", "wcag"],
        "estimate_hours": 8.0,
        "logged_hours": 3.5,
        "acceptance_criteria": [
            "Hero renders correctly at 320px, 768px, and 1440px",
            "CTA button has focus ring",
        ],
        "subtask_count": 0,
        "comment_count": 0,
        "time_log": {"total_logged_hours": 3.5, "entry_count": 1, "entries": []},
    })

    # ------------------------------------------------------------------
    # Step 1 – inspect the task
    # ------------------------------------------------------------------
    suite.add_case(
        name="1/5 · Fetch task details",
        user_message="Show me the full details of task task_001.",
        expected_tool_calls=[
            ExpectedMCPToolCall(tool_name="ProjectTracker_GetTask", args={"task_id": "task_001"})
        ],
        critics=[BinaryCritic(critic_field="task_id", weight=1.0)],
    )

    # ------------------------------------------------------------------
    # Step 2 – leave a progress comment
    # ------------------------------------------------------------------
    suite.add_case(
        name="2/5 · Add progress comment",
        user_message=(
            "Add a comment on task_001 from user_alice: "
            "'Wireframes approved by design team. Starting implementation today.'"
        ),
        additional_messages=[
            {"role": "user", "content": "Show me the full details of task task_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetTask",
                            "arguments": '{"task_id":"task_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": task_001,
                "tool_call_id": "call_s2_1",
                "name": "ProjectTracker_GetTask",
            },
            {
                "role": "assistant",
                "content": "task_001 is 'Design hero section', currently in_progress, assigned to user_alice with 3.5h logged.",
            },
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_AddComment",
                args={
                    "task_id": "task_001",
                    "author_id": "user_alice",
                    "body": "Wireframes approved by design team. Starting implementation today.",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.35),
            BinaryCritic(critic_field="author_id", weight=0.3),
            SimilarityCritic(critic_field="body", weight=0.35),
        ],
    )

    comment_response = _j({
        "comment": {
            "comment_id": "cmt_aabb1122",
            "task_id": "task_001",
            "author_id": "user_alice",
            "body": "Wireframes approved by design team. Starting implementation today.",
        },
        "task_comment_count": 1,
    })

    # ------------------------------------------------------------------
    # Step 3 – log 4 hours of implementation work
    # ------------------------------------------------------------------
    suite.add_case(
        name="3/5 · Log implementation hours",
        user_message=(
            "Log 4 hours on task_001 for user_alice today (2025-01-16). "
            "Description: 'Implemented hero layout and responsive breakpoints'."
        ),
        additional_messages=[
            {"role": "user", "content": "Show me task_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetTask",
                            "arguments": '{"task_id":"task_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": task_001,
                "tool_call_id": "call_s2_1",
                "name": "ProjectTracker_GetTask",
            },
            {"role": "assistant", "content": "task_001 is in_progress."},
            {"role": "user", "content": "Add a comment from user_alice: 'Wireframes approved.'"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_AddComment",
                            "arguments": '{"task_id":"task_001","author_id":"user_alice","body":"Wireframes approved."}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": comment_response,
                "tool_call_id": "call_s2_2",
                "name": "ProjectTracker_AddComment",
            },
            {"role": "assistant", "content": "Comment added."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_LogTime",
                args={
                    "task_id": "task_001",
                    "user_id": "user_alice",
                    "hours": 4.0,
                    "work_date": "2025-01-16",
                    "description": "Implemented hero layout and responsive breakpoints",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.25),
            BinaryCritic(critic_field="user_id", weight=0.2),
            NumericCritic(critic_field="hours", weight=0.25, value_range=(3.5, 4.5)),
            BinaryCritic(critic_field="work_date", weight=0.15),
            SimilarityCritic(critic_field="description", weight=0.15),
        ],
    )

    log_response = _j({
        "entry": {"entry_id": "te_aabb1122", "task_id": "task_001", "hours": 4.0},
        "task_total_logged_hours": 7.5,
        "sprint_total_logged_hours": 9.5,
    })

    # ------------------------------------------------------------------
    # Step 4 – move to in_review
    # ------------------------------------------------------------------
    suite.add_case(
        name="4/5 · Move task to in_review",
        user_message="task_001 is ready for review. Update its status to in_review.",
        additional_messages=[
            {"role": "user", "content": "Show me task_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetTask",
                            "arguments": '{"task_id":"task_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": task_001,
                "tool_call_id": "call_s2_1",
                "name": "ProjectTracker_GetTask",
            },
            {"role": "assistant", "content": "task_001 is in_progress."},
            {"role": "user", "content": "Add a comment."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_AddComment",
                            "arguments": '{"task_id":"task_001","author_id":"user_alice","body":"Wireframes approved."}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": comment_response,
                "tool_call_id": "call_s2_2",
                "name": "ProjectTracker_AddComment",
            },
            {"role": "assistant", "content": "Comment added."},
            {"role": "user", "content": "Log 4 hours."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_3",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_LogTime",
                            "arguments": '{"task_id":"task_001","user_id":"user_alice","hours":4.0,"work_date":"2025-01-16","description":"Implemented hero layout"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": log_response,
                "tool_call_id": "call_s2_3",
                "name": "ProjectTracker_LogTime",
            },
            {"role": "assistant", "content": "4 hours logged. Total: 7.5h."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_UpdateTask",
                args={"task_id": "task_001", "status": "in_review"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="status", weight=0.5),
        ],
    )

    review_response = _j({
        "task": {"task_id": "task_001", "status": "in_review", "logged_hours": 7.5},
        "changes": {"status": {"from": "in_progress", "to": "in_review"}},
    })

    # ------------------------------------------------------------------
    # Step 5 – mark done after review passes
    # ------------------------------------------------------------------
    suite.add_case(
        name="5/5 · Mark task done",
        user_message="The review passed. Mark task_001 as done.",
        additional_messages=[
            {"role": "user", "content": "Show me task_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetTask",
                            "arguments": '{"task_id":"task_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": task_001,
                "tool_call_id": "call_s2_1",
                "name": "ProjectTracker_GetTask",
            },
            {"role": "assistant", "content": "task_001 is in_progress."},
            {"role": "user", "content": "Add a comment, log time, then move to in_review."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_AddComment",
                            "arguments": '{"task_id":"task_001","author_id":"user_alice","body":"Wireframes approved."}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": comment_response,
                "tool_call_id": "call_s2_2",
                "name": "ProjectTracker_AddComment",
            },
            {"role": "assistant", "content": "Comment added."},
            {"role": "user", "content": "Log 4 hours."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_3",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_LogTime",
                            "arguments": '{"task_id":"task_001","user_id":"user_alice","hours":4.0,"work_date":"2025-01-16","description":"Hero layout"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": log_response,
                "tool_call_id": "call_s2_3",
                "name": "ProjectTracker_LogTime",
            },
            {"role": "assistant", "content": "Logged."},
            {"role": "user", "content": "Move to in_review."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s2_4",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_UpdateTask",
                            "arguments": '{"task_id":"task_001","status":"in_review"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": review_response,
                "tool_call_id": "call_s2_4",
                "name": "ProjectTracker_UpdateTask",
            },
            {"role": "assistant", "content": "task_001 is now in_review."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_UpdateTask",
                args={"task_id": "task_001", "status": "done"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="status", weight=0.5),
        ],
    )

    return suite


# ===========================================================================
# Suite 3 – Sprint Management  (6-step chain)
# ===========================================================================


@tool_eval()
async def eval_sprint_management() -> EvalSuite:
    """
    Manage an active sprint: list projects, inspect the sprint, add a task,
    move an existing task, pull metrics, then search for high-priority work.
    Uses the seeded data (proj_webapp_001 / spr_001).
    """
    suite = EvalSuite(
        name="Sprint Management (6-step chain)",
        system_message=(
            "You are a project-management assistant. "
            "Use ProjectTracker tools to manage sprint work."
        ),
        rubric=rubric,
    )
    if not await _load_server(suite):
        return suite

    projects_response = _j({
        "projects": [
            {
                "project_id": "proj_webapp_001",
                "name": "WebApp Redesign",
                "status": "active",
                "owner_id": "user_alice",
                "sprint_count": 1,
                "tags": ["frontend", "ux"],
            }
        ],
        "total": 1,
    })
    sprint_response = _j({
        "sprint_id": "spr_001",
        "project_id": "proj_webapp_001",
        "name": "Sprint 1 — Foundation",
        "status": "active",
        "start_date": "2025-01-13",
        "end_date": "2025-01-26",
        "goals": ["Deliver responsive navigation", "Complete hero section"],
        "capacity_hours": 80.0,
        "task_count": 4,
        "task_ids": ["task_001", "task_002", "task_003", "task_004"],
    })

    # ------------------------------------------------------------------
    # Step 1
    # ------------------------------------------------------------------
    suite.add_case(
        name="1/6 · List active projects",
        user_message="List all active projects.",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_ListProjects",
                args={"status_filter": "active"},
            )
        ],
        critics=[BinaryCritic(critic_field="status_filter", weight=1.0)],
    )

    # ------------------------------------------------------------------
    # Step 2
    # ------------------------------------------------------------------
    suite.add_case(
        name="2/6 · Get sprint details",
        user_message="Get the details of sprint spr_001.",
        additional_messages=[
            {"role": "user", "content": "List all active projects."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_ListProjects",
                            "arguments": '{"status_filter":"active"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": projects_response,
                "tool_call_id": "call_s3_1",
                "name": "ProjectTracker_ListProjects",
            },
            {
                "role": "assistant",
                "content": "Found 1 active project: proj_webapp_001 (WebApp Redesign).",
            },
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(tool_name="ProjectTracker_GetSprint", args={"sprint_id": "spr_001"})
        ],
        critics=[BinaryCritic(critic_field="sprint_id", weight=1.0)],
    )

    # ------------------------------------------------------------------
    # Step 3 – add a new critical task to the sprint
    # ------------------------------------------------------------------
    suite.add_case(
        name="3/6 · Add critical task to sprint",
        user_message=(
            "Add a critical task 'Set up Sentry error monitoring' to sprint spr_001. "
            "Labels: ops,monitoring. Estimate 4 hours."
        ),
        additional_messages=[
            {"role": "user", "content": "List active projects."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_ListProjects",
                            "arguments": '{"status_filter":"active"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": projects_response,
                "tool_call_id": "call_s3_1",
                "name": "ProjectTracker_ListProjects",
            },
            {"role": "assistant", "content": "proj_webapp_001 is active."},
            {"role": "user", "content": "Get sprint spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetSprint",
                            "arguments": '{"sprint_id":"spr_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": sprint_response,
                "tool_call_id": "call_s3_2",
                "name": "ProjectTracker_GetSprint",
            },
            {"role": "assistant", "content": "spr_001 is active with 4 tasks, ending 2025-01-26."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateTask",
                args={
                    "sprint_id": "spr_001",
                    "priority": "critical",
                    "estimate_hours": 4.0,
                    "labels": "ops,monitoring",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.3),
            BinaryCritic(critic_field="priority", weight=0.3),
            NumericCritic(critic_field="estimate_hours", weight=0.2, value_range=(3.0, 5.0)),
            SimilarityCritic(critic_field="labels", weight=0.2),
        ],
    )

    new_task_response = _j({
        "task_id": "task_sentry_00ff1122",
        "sprint_id": "spr_001",
        "title": "Set up Sentry error monitoring",
        "status": "backlog",
        "priority": "critical",
    })

    # ------------------------------------------------------------------
    # Step 4 – pull task_003 from backlog into the sprint
    # ------------------------------------------------------------------
    suite.add_case(
        name="4/6 · Move backlog task into sprint",
        user_message="Move task_003 into sprint spr_001 and set its status to todo.",
        additional_messages=[
            {"role": "user", "content": "List active projects."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_ListProjects",
                            "arguments": '{"status_filter":"active"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": projects_response,
                "tool_call_id": "call_s3_1",
                "name": "ProjectTracker_ListProjects",
            },
            {"role": "assistant", "content": "proj_webapp_001 is active."},
            {"role": "user", "content": "Get sprint spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetSprint",
                            "arguments": '{"sprint_id":"spr_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": sprint_response,
                "tool_call_id": "call_s3_2",
                "name": "ProjectTracker_GetSprint",
            },
            {"role": "assistant", "content": "spr_001 active."},
            {"role": "user", "content": "Add critical Sentry task."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_3",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_CreateTask",
                            "arguments": '{"sprint_id":"spr_001","title":"Set up Sentry","priority":"critical","estimate_hours":4.0}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": new_task_response,
                "tool_call_id": "call_s3_3",
                "name": "ProjectTracker_CreateTask",
            },
            {"role": "assistant", "content": "Critical Sentry task created."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_MoveTask",
                args={"task_id": "task_003", "target_sprint_id": "spr_001", "new_status": "todo"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.35),
            BinaryCritic(critic_field="target_sprint_id", weight=0.35),
            BinaryCritic(critic_field="new_status", weight=0.3),
        ],
    )

    move_response = _j({
        "task": {"task_id": "task_003", "sprint_id": "spr_001", "status": "todo"},
        "moved_from": None,
        "moved_to": "spr_001",
    })

    # ------------------------------------------------------------------
    # Step 5 – pull sprint metrics
    # ------------------------------------------------------------------
    suite.add_case(
        name="5/6 · Get sprint metrics",
        user_message=("Get sprint metrics for spr_001, including burndown and task breakdown."),
        additional_messages=[
            {"role": "user", "content": "List active projects then manage spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_ListProjects",
                            "arguments": '{"status_filter":"active"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": projects_response,
                "tool_call_id": "call_s3_1",
                "name": "ProjectTracker_ListProjects",
            },
            {"role": "assistant", "content": "Found proj_webapp_001."},
            {"role": "user", "content": "Get spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetSprint",
                            "arguments": '{"sprint_id":"spr_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": sprint_response,
                "tool_call_id": "call_s3_2",
                "name": "ProjectTracker_GetSprint",
            },
            {"role": "assistant", "content": "Sprint active."},
            {"role": "user", "content": "Add Sentry task, move task_003."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_3",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_CreateTask",
                            "arguments": '{"sprint_id":"spr_001","title":"Sentry","priority":"critical"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": new_task_response,
                "tool_call_id": "call_s3_3",
                "name": "ProjectTracker_CreateTask",
            },
            {"role": "assistant", "content": "Sentry task added."},
            {"role": "user", "content": "Move task_003 into spr_001 as todo."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_4",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_MoveTask",
                            "arguments": '{"task_id":"task_003","target_sprint_id":"spr_001","new_status":"todo"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": move_response,
                "tool_call_id": "call_s3_4",
                "name": "ProjectTracker_MoveTask",
            },
            {"role": "assistant", "content": "task_003 moved to spr_001."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_GetSprintMetrics",
                args={
                    "sprint_id": "spr_001",
                    "include_burndown": True,
                    "include_task_breakdown": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.5),
            BinaryCritic(critic_field="include_burndown", weight=0.25),
            BinaryCritic(critic_field="include_task_breakdown", weight=0.25),
        ],
    )

    metrics_response = _j({
        "sprint_id": "spr_001",
        "total_tasks": 6,
        "completed_tasks": 1,
        "completion_rate": 0.1667,
        "hours_estimated": 30.0,
        "hours_logged": 5.5,
        "velocity": 5.5,
        "task_breakdown": {
            "by_status": {"in_progress": 1, "todo": 2, "backlog": 2, "in_review": 1},
            "by_priority": {"critical": 2, "high": 2, "medium": 1, "low": 0},
        },
    })

    # ------------------------------------------------------------------
    # Step 6 – search for high/critical open tasks
    # ------------------------------------------------------------------
    suite.add_case(
        name="6/6 · Search high-priority open tasks",
        user_message=(
            "Search for all high and critical tasks in spr_001 that are in_progress "
            "or in_review, sorted by priority."
        ),
        additional_messages=[
            {"role": "user", "content": "List active projects then get spr_001 details."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_1",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_ListProjects",
                            "arguments": '{"status_filter":"active"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": projects_response,
                "tool_call_id": "call_s3_1",
                "name": "ProjectTracker_ListProjects",
            },
            {"role": "assistant", "content": "Found proj_webapp_001."},
            {"role": "user", "content": "Get spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_2",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetSprint",
                            "arguments": '{"sprint_id":"spr_001"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": sprint_response,
                "tool_call_id": "call_s3_2",
                "name": "ProjectTracker_GetSprint",
            },
            {"role": "assistant", "content": "Sprint active."},
            {"role": "user", "content": "Add Sentry task and move task_003."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_3",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_MoveTask",
                            "arguments": '{"task_id":"task_003","target_sprint_id":"spr_001","new_status":"todo"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": move_response,
                "tool_call_id": "call_s3_3",
                "name": "ProjectTracker_MoveTask",
            },
            {"role": "assistant", "content": "Done."},
            {"role": "user", "content": "Get metrics for spr_001."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_s3_4",
                        "type": "function",
                        "function": {
                            "name": "ProjectTracker_GetSprintMetrics",
                            "arguments": '{"sprint_id":"spr_001","include_burndown":true,"include_task_breakdown":true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": metrics_response,
                "tool_call_id": "call_s3_4",
                "name": "ProjectTracker_GetSprintMetrics",
            },
            {"role": "assistant", "content": "Sprint is 16.7% complete. 2 critical tasks, 2 high."},
        ],
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_SearchTasks",
                args={
                    "sprint_id": "spr_001",
                    "priority": "high,critical",
                    "status": "in_progress,in_review",
                    "sort_by": "priority",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.3),
            SimilarityCritic(critic_field="priority", weight=0.25),
            SimilarityCritic(critic_field="status", weight=0.25),
            BinaryCritic(critic_field="sort_by", weight=0.2),
        ],
    )

    return suite


# ===========================================================================
# Suite 4 – Full Sprint Cycle  (8-step chain)
# ===========================================================================


@tool_eval()
async def eval_full_sprint_cycle() -> EvalSuite:
    """
    Complete sprint lifecycle using every tool category:
    create project → sprint → task → subtask → log time → done → close sprint → metrics.
    """
    suite = EvalSuite(
        name="Full Sprint Cycle (8-step chain)",
        system_message=(
            "You are a project-management assistant. "
            "Use ProjectTracker tools to execute a complete sprint lifecycle."
        ),
        rubric=rubric,
    )
    if not await _load_server(suite):
        return suite

    # Pre-built fake responses for each prior step
    proj_r = _j({
        "project_id": _PROJ_AUTH,
        "name": "Auth Service Rewrite",
        "owner_id": "user_eve",
        "status": "planning",
        "tags": ["security", "backend"],
    })
    spr_r = _j({
        "sprint_id": _SPR_AUTH,
        "project_id": _PROJ_AUTH,
        "name": "Sprint 1",
        "status": "planning",
        "start_date": "2025-05-01",
        "end_date": "2025-05-14",
        "capacity_hours": 60.0,
        "task_count": 0,
    })
    task_r = _j({
        "task_id": _TASK_JWT,
        "sprint_id": _SPR_AUTH,
        "project_id": _PROJ_AUTH,
        "title": "Replace jsonwebtoken with jose",
        "status": "backlog",
        "priority": "high",
        "assignee_id": "user_eve",
        "estimate_hours": 8.0,
        "labels": ["security", "backend"],
    })
    subtask_r = _j({
        "subtask": {
            "task_id": _TASK_SUB,
            "parent_task_id": _TASK_JWT,
            "title": "Update token verification middleware",
            "status": "backlog",
        },
        "parent_task_id": _TASK_JWT,
    })
    log_r = _j({
        "entry": {"entry_id": "te_ee5566ff", "hours": 5.0},
        "task_total_logged_hours": 5.0,
        "sprint_total_logged_hours": 5.0,
    })
    done_r = _j({
        "task": {"task_id": _TASK_JWT, "status": "done", "logged_hours": 5.0},
        "changes": {"status": {"from": "in_progress", "to": "done"}},
    })
    close_r = _j({
        "sprint": {"sprint_id": _SPR_AUTH, "status": "completed"},
        "summary": {
            "total_tasks": 2,
            "completed_tasks": 1,
            "carried_over_tasks": 1,
            "completion_rate": 0.5,
        },
        "carry_over_task_ids": [_TASK_SUB],
    })

    def _prior(steps: list[tuple[str, str, str, str]]) -> list[dict]:
        """Build additional_messages from [(user_msg, tool_name, args_json, response_json)]."""
        msgs: list[dict] = []
        for i, (user_msg, tool_name, args_str, resp_str) in enumerate(steps):
            call_id = f"call_s4_{i + 1}"
            msgs.append({"role": "user", "content": user_msg})
            msgs.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": args_str},
                    }
                ],
            })
            msgs.append({
                "role": "tool",
                "content": resp_str,
                "tool_call_id": call_id,
                "name": tool_name,
            })
            msgs.append({"role": "assistant", "content": "Done."})
        return msgs

    steps_history = [
        (
            "Create Auth Service Rewrite project owned by user_eve.",
            "ProjectTracker_CreateProject",
            '{"name":"Auth Service Rewrite","owner_id":"user_eve","tags":"security,backend"}',
            proj_r,
        ),
        (
            f"Create Sprint 1 in {_PROJ_AUTH} May 1–14 with 60h capacity.",
            "ProjectTracker_CreateSprint",
            f'{{"project_id":"{_PROJ_AUTH}","name":"Sprint 1","start_date":"2025-05-01","end_date":"2025-05-14","capacity_hours":60.0}}',
            spr_r,
        ),
        (
            f"Create high-priority task 'Replace jsonwebtoken with jose' in {_SPR_AUTH} assigned to user_eve.",
            "ProjectTracker_CreateTask",
            f'{{"sprint_id":"{_SPR_AUTH}","title":"Replace jsonwebtoken with jose","priority":"high","assignee_id":"user_eve","estimate_hours":8.0,"labels":"security,backend"}}',
            task_r,
        ),
        (
            f"Add subtask 'Update token verification middleware' under {_TASK_JWT}.",
            "ProjectTracker_AddSubtask",
            f'{{"parent_task_id":"{_TASK_JWT}","title":"Update token verification middleware","assignee_id":"user_eve","estimate_hours":2.0}}',
            subtask_r,
        ),
        (
            f"Log 5 hours on {_TASK_JWT} for user_eve: 'Migrated to jose, updated signing'.",
            "ProjectTracker_LogTime",
            f'{{"task_id":"{_TASK_JWT}","user_id":"user_eve","hours":5.0,"description":"Migrated to jose, updated signing","work_date":"2025-05-05"}}',
            log_r,
        ),
        (
            f"Mark {_TASK_JWT} as done.",
            "ProjectTracker_UpdateTask",
            f'{{"task_id":"{_TASK_JWT}","status":"done"}}',
            done_r,
        ),
        (
            f"Close sprint {_SPR_AUTH}, carry incomplete tasks to backlog. Retro: 'Breaking changes need more lead time.'",
            "ProjectTracker_CloseSprint",
            f'{{"sprint_id":"{_SPR_AUTH}","carry_over_policy":"backlog","retrospective_notes":"Breaking changes need more lead time."}}',
            close_r,
        ),
    ]

    # ------------------------------------------------------------------
    # Step 1
    # ------------------------------------------------------------------
    suite.add_case(
        name="1/8 · Create project",
        user_message="Create a project called 'Auth Service Rewrite' owned by user_eve. Tags: security,backend,breaking-change.",
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateProject",
                args={
                    "name": "Auth Service Rewrite",
                    "owner_id": "user_eve",
                    "tags": "security,backend,breaking-change",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="name", weight=0.35),
            BinaryCritic(critic_field="owner_id", weight=0.35),
            SimilarityCritic(critic_field="tags", weight=0.3),
        ],
    )

    # ------------------------------------------------------------------
    # Step 2
    # ------------------------------------------------------------------
    suite.add_case(
        name="2/8 · Create sprint",
        user_message=f"Create Sprint 1 in project {_PROJ_AUTH} running 2025-05-01 to 2025-05-14 with 60 hour capacity. Goals: 'Replace JWT library,Add refresh token rotation'.",
        additional_messages=_prior(steps_history[:1]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateSprint",
                args={
                    "project_id": _PROJ_AUTH,
                    "name": "Sprint 1",
                    "start_date": "2025-05-01",
                    "end_date": "2025-05-14",
                    "capacity_hours": 60.0,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="project_id", weight=0.3),
            BinaryCritic(critic_field="start_date", weight=0.2),
            BinaryCritic(critic_field="end_date", weight=0.2),
            NumericCritic(critic_field="capacity_hours", weight=0.3, value_range=(55.0, 65.0)),
        ],
    )

    # ------------------------------------------------------------------
    # Step 3
    # ------------------------------------------------------------------
    suite.add_case(
        name="3/8 · Create JWT replacement task",
        user_message=f"In sprint {_SPR_AUTH}, create a high-priority task 'Replace jsonwebtoken with jose', assigned to user_eve, 8h estimate, labels: security,backend,breaking-change.",
        additional_messages=_prior(steps_history[:2]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CreateTask",
                args={
                    "sprint_id": _SPR_AUTH,
                    "priority": "high",
                    "assignee_id": "user_eve",
                    "estimate_hours": 8.0,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.3),
            BinaryCritic(critic_field="priority", weight=0.25),
            BinaryCritic(critic_field="assignee_id", weight=0.25),
            NumericCritic(critic_field="estimate_hours", weight=0.2, value_range=(7.0, 9.0)),
        ],
    )

    # ------------------------------------------------------------------
    # Step 4
    # ------------------------------------------------------------------
    suite.add_case(
        name="4/8 · Add subtask for middleware update",
        user_message=f"Add a subtask 'Update token verification middleware' under task {_TASK_JWT}, assigned to user_eve, 2h estimate.",
        additional_messages=_prior(steps_history[:3]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_AddSubtask",
                args={
                    "parent_task_id": _TASK_JWT,
                    "title": "Update token verification middleware",
                    "assignee_id": "user_eve",
                    "estimate_hours": 2.0,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="parent_task_id", weight=0.35),
            SimilarityCritic(critic_field="title", weight=0.3),
            BinaryCritic(critic_field="assignee_id", weight=0.2),
            NumericCritic(critic_field="estimate_hours", weight=0.15, value_range=(1.5, 2.5)),
        ],
    )

    # ------------------------------------------------------------------
    # Step 5
    # ------------------------------------------------------------------
    suite.add_case(
        name="5/8 · Log implementation hours",
        user_message=f"Log 5 hours on task {_TASK_JWT} for user_eve on 2025-05-05. Description: 'Migrated to jose library, updated signing and verification'.",
        additional_messages=_prior(steps_history[:4]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_LogTime",
                args={
                    "task_id": _TASK_JWT,
                    "user_id": "user_eve",
                    "hours": 5.0,
                    "work_date": "2025-05-05",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.3),
            BinaryCritic(critic_field="user_id", weight=0.25),
            NumericCritic(critic_field="hours", weight=0.3, value_range=(4.5, 5.5)),
            BinaryCritic(critic_field="work_date", weight=0.15),
        ],
    )

    # ------------------------------------------------------------------
    # Step 6
    # ------------------------------------------------------------------
    suite.add_case(
        name="6/8 · Mark task done",
        user_message=f"Task {_TASK_JWT} is complete. Mark it as done.",
        additional_messages=_prior(steps_history[:5]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_UpdateTask",
                args={"task_id": _TASK_JWT, "status": "done"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="task_id", weight=0.5),
            BinaryCritic(critic_field="status", weight=0.5),
        ],
    )

    # ------------------------------------------------------------------
    # Step 7
    # ------------------------------------------------------------------
    suite.add_case(
        name="7/8 · Close the sprint",
        user_message=(
            f"Close sprint {_SPR_AUTH}. Carry any incomplete tasks to the backlog. "
            "Retrospective notes: 'Breaking changes need more lead time. "
            "Add changelog entries next sprint.'"
        ),
        additional_messages=_prior(steps_history[:6]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_CloseSprint",
                args={
                    "sprint_id": _SPR_AUTH,
                    "carry_over_policy": "backlog",
                    "retrospective_notes": "Breaking changes need more lead time. Add changelog entries next sprint.",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.35),
            BinaryCritic(critic_field="carry_over_policy", weight=0.35),
            SimilarityCritic(critic_field="retrospective_notes", weight=0.3),
        ],
    )

    # ------------------------------------------------------------------
    # Step 8
    # ------------------------------------------------------------------
    suite.add_case(
        name="8/8 · Pull final sprint metrics",
        user_message=f"Pull the final metrics for sprint {_SPR_AUTH} with burndown and task breakdown.",
        additional_messages=_prior(steps_history[:7]),
        expected_tool_calls=[
            ExpectedMCPToolCall(
                tool_name="ProjectTracker_GetSprintMetrics",
                args={
                    "sprint_id": _SPR_AUTH,
                    "include_burndown": True,
                    "include_task_breakdown": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sprint_id", weight=0.5),
            BinaryCritic(critic_field="include_burndown", weight=0.25),
            BinaryCritic(critic_field="include_task_breakdown", weight=0.25),
        ],
    )

    return suite

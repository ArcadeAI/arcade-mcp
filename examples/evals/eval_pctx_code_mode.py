"""
ProjectTracker Code Mode evaluations.

Uses pctx Code Mode: the LLM writes TypeScript executed in the pctx sandbox.
Tool calls within the TypeScript are captured via ExecutionTrace and evaluated
using arcade-evals critics and rubrics.

Unlike the standard arcade-evals runner (which captures LLM tool calls directly),
Code Mode requires a custom execution loop:
  LLM generates TypeScript → pctx executes it → trace.events extracted as tool calls
  → EvalCase.evaluate() scores against expected calls using critics and rubrics.

Requires:
  - pctx server running: pctx start
  - OpenRouter (or OpenAI) key: OPENROUTER_API_KEY or OPENAI_API_KEY

Run:
    uv run --directory examples/mcp_servers/pctx_code_mode examples/evals/eval_pctx_code_mode.py
"""

import asyncio
import json
import os
import re
import sys
from typing import Any

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "../mcp_servers/pctx_code_mode/src"),
)

from arcade_evals import BinaryCritic, EvalRubric, SimilarityCritic
from arcade_evals.eval import EvalCase, EvaluationResult, NamedExpectedToolCall
from openai import AsyncOpenAI
from pctx_client import Pctx
from pctx_client.models import CallbackInvocationEvent
from pctx_code_mode.server import pctx_tools

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PCTX_URL = os.environ.get("PCTX_URL", "http://127.0.0.1:8080")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_USING_OPENROUTER = bool(OPENROUTER_API_KEY)
MODEL = os.environ.get("EVAL_MODEL", "openai/gpt-4o" if _USING_OPENROUTER else "gpt-4o")


def _llm_client() -> AsyncOpenAI:
    if _USING_OPENROUTER:
        return AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
    return AsyncOpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def _build_system_prompt(declarations: str) -> str:
    return f"""You are a project-management assistant operating in Code Mode.

You have access to the following TypeScript functions via the `Tools` namespace:
```typescript
{declarations}
```

To complete tasks you MUST write a TypeScript function called `run()` and wrap
it in a JSON object with key "typescript".

The code must follow this exact template:
```
async function run() {{
  // your code here — call Tools.functionName({{...}})
  return {{ ... }};  // always return a plain object or array
}}
```

Rules:
- Always return a value from run() — return the full result object, not a sub-field
- Do not import anything — Tools is globally available
- For multi-step tasks, chain the calls inside a single run() function

Respond ONLY with valid JSON: {{"typescript": "<the full TypeScript code>"}}
"""


# ---------------------------------------------------------------------------
# Rubric — soft failures: code mode may call helper fns in addition to main ones
# ---------------------------------------------------------------------------

rubric = EvalRubric(
    fail_threshold=0.7,
    warn_threshold=0.9,
    fail_on_tool_selection=False,  # score via cost matrix, don't hard-fail
    fail_on_tool_call_quantity=False,  # code may make extra/fewer calls
    tool_selection_weight=1.0,
)

# ---------------------------------------------------------------------------
# Eval cases
# Expected tool names are camelCase TypeScript names from the Tools.* namespace.
# CallbackInvocationEvent.id is the function identifier from pctx trace events.
# ---------------------------------------------------------------------------

_PLACEHOLDER_SYSTEM = ""  # replaced at runtime by _build_system_prompt(declarations)

CASES: list[EvalCase] = [
    EvalCase(
        name="List active projects",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message="List all active projects and return their names and IDs.",
        expected_tool_calls=[
            NamedExpectedToolCall("tools__list_projects", {}),
        ],
        rubric=rubric,
    ),
    EvalCase(
        name="Get sprint details",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message="Get the details of sprint spr_001 and return its name, status, and goals.",
        expected_tool_calls=[
            NamedExpectedToolCall("tools__get_sprint", {"sprint_id": "spr_001"}),
        ],
        critics=[BinaryCritic("sprint_id", 1.0)],
        rubric=rubric,
    ),
    EvalCase(
        name="Create a project",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message=(
            "Create a new project called 'Eval Test Project' owned by user_eval. "
            "Return the project_id."
        ),
        expected_tool_calls=[
            NamedExpectedToolCall(
                "tools__create_project", {"name": "Eval Test Project", "owner_id": "user_eval"}
            ),
        ],
        critics=[
            SimilarityCritic("name", 0.5),
            BinaryCritic("owner_id", 0.5),
        ],
        rubric=rubric,
    ),
    EvalCase(
        name="Task lifecycle — get then update",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message=(
            "Get task task_001, then update its status to in_review. "
            "Return the updated task's status."
        ),
        expected_tool_calls=[
            NamedExpectedToolCall("tools__get_task", {"task_id": "task_001"}),
            NamedExpectedToolCall(
                "tools__update_task", {"task_id": "task_001", "status": "in_review"}
            ),
        ],
        critics=[
            BinaryCritic("task_id", 0.5),
            BinaryCritic("status", 0.5),
        ],
        rubric=rubric,
    ),
    EvalCase(
        name="Sprint metrics",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message=(
            "Get sprint metrics for spr_001 with burndown and task breakdown. "
            "Return the completion_rate and total_tasks."
        ),
        expected_tool_calls=[
            NamedExpectedToolCall(
                "tools__get_sprint_metrics",
                {"sprint_id": "spr_001", "include_burndown": True, "include_task_breakdown": True},
            ),
        ],
        critics=[BinaryCritic("sprint_id", 1.0)],
        rubric=rubric,
    ),
    EvalCase(
        name="Search critical tasks",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message="Search for all critical-priority tasks and return their IDs and titles.",
        expected_tool_calls=[
            NamedExpectedToolCall("tools__search_tasks", {"priority": "critical"}),
        ],
        critics=[BinaryCritic("priority", 1.0)],
        rubric=rubric,
    ),
    EvalCase(
        name="Multi-step: create project + sprint + task",
        system_message=_PLACEHOLDER_SYSTEM,
        user_message=(
            "Do these three steps in sequence:\n"
            "1. Create a project called 'Pipeline Eval' owned by user_pipeline\n"
            "2. Create a sprint called 'Sprint 1' in that project, "
            "   starting 2025-06-01 ending 2025-06-14, capacity 40 hours\n"
            "3. Create a high-priority task 'Build ingestion layer' in that sprint\n"
            "Return the task_id of the created task."
        ),
        expected_tool_calls=[
            NamedExpectedToolCall(
                "tools__create_project", {"name": "Pipeline Eval", "owner_id": "user_pipeline"}
            ),
            NamedExpectedToolCall(
                "tools__create_sprint",
                {
                    "name": "Sprint 1",
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-14",
                    "capacity_hours": 40,
                },
            ),
            NamedExpectedToolCall(
                "tools__create_task",
                {"title": "Build ingestion layer", "priority": "high"},
            ),
        ],
        critics=[
            SimilarityCritic("name", 0.4),
            SimilarityCritic("title", 0.3),
            BinaryCritic("priority", 0.3),
        ],
        rubric=rubric,
    ),
]


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------


def _extract_typescript(raw: str) -> str | None:
    """Extract TypeScript code from LLM response (JSON or markdown fallback)."""
    cleaned = raw.strip()
    try:
        inner = cleaned
        if cleaned.startswith("```"):
            inner = "\n".join(cleaned.split("\n")[1:])
            inner = inner.rsplit("```", 1)[0].strip()
        payload = json.loads(inner)
        return payload.get("typescript") or payload.get("code")
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: extract from markdown code fence
    m = re.search(r"```(?:typescript|ts)?\n(.*?)```", raw, re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_tool_calls(result: Any) -> list[tuple[str, dict[str, Any]]]:
    """Extract (name, args) pairs from CallbackInvocationEvent entries in trace.

    pctx reports callback ids as "namespace__snake_case_name" (e.g. "tools__list_projects").
    """
    calls = []
    for event in result.trace.events:
        if isinstance(event, CallbackInvocationEvent):
            args = event.args if isinstance(event.args, dict) else {}
            calls.append((event.id, args))
    return calls


# ---------------------------------------------------------------------------
# Case runner
# ---------------------------------------------------------------------------


async def _run_case(
    case: EvalCase,
    pctx: Pctx,
    client: AsyncOpenAI,
    system_prompt: str,
) -> tuple[EvaluationResult, list[tuple[str, dict[str, Any]]], str | None]:
    """
    Returns (evaluation_result, actual_calls, failure_detail).
    failure_detail is non-None when execution failed before evaluate() could run.
    """
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case.user_message},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content or ""
    ts_code = _extract_typescript(raw)

    if not ts_code:
        err = f"Could not extract TypeScript from LLM response.\nRaw: {raw[:300]}"
        empty = EvaluationResult(score=0.0, passed=False, failure_reason=err)
        return empty, [], err

    try:
        result = await pctx.execute_typescript(ts_code)
    except Exception as exc:
        err = f"execute_typescript failed: {exc}"
        empty = EvaluationResult(score=0.0, passed=False, failure_reason=err)
        return empty, [], err

    if not result.success:
        err = f"execution error:\n{result.stderr}\ncode:\n{ts_code}"
        empty = EvaluationResult(score=0.0, passed=False, failure_reason=err)
        return empty, [], err

    actual_calls = _extract_tool_calls(result)
    evaluation = case.evaluate(actual_calls)
    return evaluation, actual_calls, None


# ---------------------------------------------------------------------------
# Suite runner + reporting
# ---------------------------------------------------------------------------


def _fmt_calls(calls: list[tuple[str, dict[str, Any]]]) -> str:
    if not calls:
        return "(none)"
    return ", ".join(f"{name}({json.dumps(args, separators=(',', ':'))})" for name, args in calls)


def _fmt_expected(case: EvalCase) -> str:
    return ", ".join(
        f"{tc.name}({json.dumps(tc.args, separators=(',', ':'))})"
        for tc in case.expected_tool_calls
    )


async def run_suite(pctx: Pctx, client: AsyncOpenAI, system_prompt: str) -> None:
    total = len(CASES)
    passed = warned = failed = 0

    print(f"\n{'=' * 60}")
    print(f"  Code Mode Eval  ({total} cases, model={MODEL})")
    print(f"{'=' * 60}\n")

    for i, case in enumerate(CASES, 1):
        evaluation, actual_calls, pre_error = await _run_case(case, pctx, client, system_prompt)

        if evaluation.passed:
            status = "PASS"
            passed += 1
        elif evaluation.warning:
            status = "WARN"
            warned += 1
        else:
            status = "FAIL"
            failed += 1

        score_pct = f"{evaluation.score * 100:.0f}%"
        print(f"[{status}] {i}/{total} · {case.name}  (score={score_pct})")

        if status != "PASS":
            reason = evaluation.failure_reason or pre_error or "score below threshold"
            print(f"       reason : {reason}")
            print(f"       expected: {_fmt_expected(case)}")
            print(f"       actual  : {_fmt_calls(actual_calls)}")
        else:
            print(f"       calls   : {_fmt_calls(actual_calls)}")

        print()

    print(f"{'=' * 60}")
    print(f"  Results: {passed} passed / {warned} warned / {failed} failed  ({total} total)")
    print(f"  Rubric : fail<{rubric.fail_threshold:.0%}  warn<{rubric.warn_threshold:.0%}")
    print(f"{'=' * 60}\n")

    sys.exit(0 if failed == 0 else 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    print(f"Connecting to pctx at {PCTX_URL} …")
    client = _llm_client()

    async with Pctx(tools=pctx_tools, url=PCTX_URL) as pctx:
        fns = await pctx.list_functions()
        print(f"  {len(fns.functions)} functions registered")
        all_names = [f"{f.namespace}.{f.name}" for f in fns.functions]
        details = await pctx.get_function_details(all_names)
        declarations = details.code
        print(f"  type declarations: {len(declarations)} chars\n")

        await run_suite(pctx, client, _build_system_prompt(declarations))


if __name__ == "__main__":
    asyncio.run(main())

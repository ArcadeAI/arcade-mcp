#!/usr/bin/env python3
"""task_augmentation MCP server.

Demonstrates the 2025-11-25 experimental tasks primitive (SEP-1686):

- ``@tool(execution=ToolExecution(taskSupport="optional"))`` — tool may be
  invoked synchronously OR as a long-running task when the client includes
  ``params.task`` on ``tools/call``.
- ``taskSupport="required"`` — tool MUST be invoked as a task.
- ``taskSupport="forbidden"`` — tool MUST be invoked synchronously.

When a tool runs as a task, progress notifications, elicitation requests, and
sampling requests issued from the tool body automatically carry the
``io.modelcontextprotocol/related-task`` ``_meta`` so the client can correlate
them with the originating task id.
"""

import asyncio
import sys
from typing import Annotated

from arcade_mcp_server import Context, MCPApp, ToolExecution, tool

app = MCPApp(
    name="task_augmentation",
    version="1.0.0",
    log_level="DEBUG",
    instructions=(
        "Call `generate_report` with the optional `task` metadata on `tools/call` to "
        "see durable, progress-reporting execution. Call `deep_research` the same way to "
        "see elicitation correlated with a running task. Call `quick_lookup` — attempting "
        "to pass task metadata will be rejected by the server."
    ),
)


# -----------------------------------------------------------------------------
# 1. taskSupport="optional" — synchronous OR background
# -----------------------------------------------------------------------------


@tool(execution=ToolExecution(taskSupport="optional"))
async def generate_report(
    context: Context,
    topic: Annotated[str, "The topic to generate a report about"],
) -> Annotated[dict, "The generated report"]:
    """Simulate a long-running report job.

    When called synchronously (no ``params.task`` on ``tools/call``) this tool
    just runs to completion. When called with ``params.task = {"ttl": ...}`` it
    runs in the background and the client gets an immediate
    ``CreateTaskResult`` with ``_meta.io.modelcontextprotocol/related-task``.
    Progress notifications emitted here will carry the same ``_meta``.
    """
    await context.log.info(f"Starting report generation on topic: {topic}")

    steps = [
        "collecting sources",
        "summarizing findings",
        "cross-referencing citations",
        "drafting outline",
        "writing body",
        "editing prose",
        "formatting output",
        "running fact check",
        "rendering final report",
        "done",
    ]
    total = len(steps)

    for i, step in enumerate(steps, start=1):
        await context.progress.report(i, total=total, message=step)
        # Small delay per step so a client has time to see progress flow through.
        await asyncio.sleep(0.5)

    return {
        "topic": topic,
        "sections": [
            {"title": "Summary", "body": f"A placeholder summary about {topic}."},
            {"title": "Details", "body": "Pretend this is the long body."},
        ],
        "word_count": 1234,
    }


# Register on the MCPApp. The @tool decorator already sets __tool_name__, so
# add_tool will not re-decorate and the __tool_execution__ dunder is preserved.
app.add_tool(generate_report)


# -----------------------------------------------------------------------------
# 2. taskSupport="required" — background only, with mid-run elicitation
# -----------------------------------------------------------------------------


@tool(execution=ToolExecution(taskSupport="required"))
async def deep_research(
    context: Context,
    question: Annotated[str, "The research question"],
) -> Annotated[dict, "The research answer"]:
    """Research something that genuinely needs to run async — includes a mid-run
    elicitation to prove task/elicitation correlation works.

    Because ``taskSupport="required"``, calling this without ``params.task`` on
    ``tools/call`` returns a JSON-RPC error
    (code -32601: "Task augmentation required for this tool").
    """
    await context.log.info(f"Starting deep research: {question!r}")

    await context.progress.report(1, total=4, message="planning")
    await asyncio.sleep(0.4)

    # Elicit a clarification from the human mid-run. The outgoing
    # elicit/create request is auto-tagged with io.modelcontextprotocol/related-task
    # so the client knows which running task the elicitation belongs to.
    elicitation = await context.ui.elicit(
        "Should I favour recent sources or all-time classics?",
        schema={
            "type": "object",
            "properties": {
                "preference": {
                    "type": "string",
                    "oneOf": [
                        {"const": "recent", "title": "Recent (last 2 years)"},
                        {"const": "all_time", "title": "All-time classics"},
                        {"const": "mix", "title": "A mix of both"},
                    ],
                }
            },
            "required": ["preference"],
        },
    )
    if elicitation.action != "accept":
        await context.log.warning("Research cancelled — no clarification provided.")
        return {
            "question": question,
            "status": "cancelled_by_user",
            "reason": elicitation.action,
        }

    preference = elicitation.content.get("preference", "mix")
    await context.progress.report(2, total=4, message=f"searching ({preference})")
    await asyncio.sleep(0.6)
    await context.progress.report(3, total=4, message="synthesising")
    await asyncio.sleep(0.6)
    await context.progress.report(4, total=4, message="writing up")
    await asyncio.sleep(0.3)

    return {
        "question": question,
        "preference": preference,
        "answer": f"Based on {preference} sources, here is a placeholder answer.",
    }


app.add_tool(deep_research)


# -----------------------------------------------------------------------------
# 3. taskSupport="forbidden" — synchronous only
# -----------------------------------------------------------------------------


@tool(execution=ToolExecution(taskSupport="forbidden"))
def quick_lookup(
    key: Annotated[str, "The cache key to look up"],
) -> Annotated[str, "The looked-up value"]:
    """Fast synchronous cache read. Task augmentation is forbidden here — the
    server rejects any ``tools/call`` that carries ``params.task``.
    """
    mock_cache = {"greeting": "hello", "farewell": "goodbye"}
    return mock_cache.get(key, f"<no value for {key!r}>")


app.add_tool(quick_lookup)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # HTTP+SSE gives the best task experience because the long-lived SSE stream
    # lets the client receive task status notifications without polling.
    # stdio also works but the client is expected to call tasks/get periodically.
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    app.run(transport=transport, host="127.0.0.1", port=8000)

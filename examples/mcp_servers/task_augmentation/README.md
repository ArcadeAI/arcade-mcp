# task_augmentation

Demonstrates the **experimental Tasks primitive** introduced in
MCP 2025-11-25 (SEP-1686): durable, long-running tool invocations with
pollable status, separate result retrieval, and cancellation.

## What this example shows

Three tools, each with a different `ToolExecution.taskSupport` policy:

| Tool | `taskSupport` | Behavior |
|---|---|---|
| `generate_report(topic)` | `"optional"` | Runs synchronously by default; runs as a background task when the client adds `params.task` to `tools/call`. Emits 10 progress notifications. |
| `deep_research(question)` | `"required"` | Must be called as a task — the server rejects synchronous calls. Demonstrates mid-run elicitation correlated with the task. |
| `quick_lookup(key)` | `"forbidden"` | Synchronous only — the server rejects task-augmented calls. |

All three tools demonstrate the auto-injected
`io.modelcontextprotocol/related-task` `_meta` on outbound
progress / elicitation / sampling requests when they run under a task.

## Running

```bash
uv sync
uv run python src/task_augmentation/server.py        # HTTP (default here — SEP recommended)
uv run python src/task_augmentation/server.py stdio  # stdio also works
```

## Wire-level walkthrough

The client MUST declare task support for `tools/call` during `initialize`:

```json
{
  "method": "initialize",
  "params": {
    "capabilities": {
      "tasks": {"requests": {"tools/call": {}}}
    }
  }
}
```

### 1. Synchronous call to `generate_report`

```json
{
  "method": "tools/call",
  "params": { "name": "generate_report", "arguments": {"topic": "llamas"} }
}
```

Returns a normal `CallToolResult` after ~5 seconds. Progress notifications
still fire but carry **no** `related-task` `_meta` because there's no task.

### 2. Task-augmented call to `generate_report`

```json
{
  "method": "tools/call",
  "params": {
    "name": "generate_report",
    "arguments": {"topic": "llamas"},
    "task": {"ttl": 300}
  }
}
```

Returns **immediately** with:

```json
{
  "result": {
    "task": {
      "taskId": "task_abc123",
      "status": "working",
      "createdAt": "2026-04-22T...",
      ...
    },
    "_meta": {
      "io.modelcontextprotocol/related-task": {"taskId": "task_abc123"}
    }
  }
}
```

Every progress notification emitted from the tool body now carries the same
`_meta.io.modelcontextprotocol/related-task`, so the client knows the progress
belongs to `task_abc123`.

The client then polls / fetches:

```jsonc
// Poll current status
{"method": "tasks/get", "params": {"taskId": "task_abc123"}}

// Fetch the final tool result (returns CallToolResult once status=completed)
{"method": "tasks/result", "params": {"taskId": "task_abc123"}}

// Cancel early
{"method": "tasks/cancel", "params": {"taskId": "task_abc123"}}
```

On HTTP+SSE, the server *also* pushes `notifications/tasks/status` as the task
progresses, so the client can avoid polling.

### 3. Mid-run elicitation under a task (`deep_research`)

`deep_research` is `taskSupport="required"`. Calling without `params.task`:

```json
{
  "error": {
    "code": -32601,
    "message": "Task augmentation required for this tool"
  }
}
```

Calling with `params.task`: the tool runs in the background, issues a
`elicitation/create` request asking "recent vs. all-time" sources, and the
outbound request carries `_meta.io.modelcontextprotocol/related-task` so the
client UI can present the elicit dialog in the context of the right task.

### 4. Forbidden task metadata (`quick_lookup`)

```json
{
  "method": "tools/call",
  "params": {
    "name": "quick_lookup",
    "arguments": {"key": "greeting"},
    "task": {"ttl": 60}
  }
}
```

Returns:

```json
{
  "error": {
    "code": -32601,
    "message": "Task augmentation forbidden for this tool"
  }
}
```

## Tips for MCP Inspector

Run the server on HTTP, connect MCP Inspector to `http://127.0.0.1:8000/mcp`,
and use the "Tools" panel. Inspector currently treats every `tools/call` as
synchronous — to exercise the task path you need a client that sends
`params.task`. A `curl` + `jq` workflow works fine:

```bash
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"generate_report","arguments":{"topic":"llamas"},"task":{"ttl":300}}}' \
  | jq
```

## The execution= kwarg on @tool

The `execution` parameter on `arcade_tdk.tool` is protocol-specific and opaque
to `arcade-tdk` — it's stashed on the function as `__tool_execution__` and read
by MCP-specific code at serialization time. Pass
`arcade_mcp_server.ToolExecution(...)` for MCP; other protocols can read the
same dunder for their own purposes.

## Related SEPs

- **SEP-1686** — Tasks primitive (the main feature).
- **SEP-1699** — SSE polling/resumption (not implemented in this repo; use
  `tasks/get` to poll).

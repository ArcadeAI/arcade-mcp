# typed_errors

Demonstrates the **typed tool error classes** from `arcade_tdk.errors` and
the MCP 2025-11-25 behaviour change from SEP-1303: input validation errors
now come back as **tool execution errors** (with `isError: true` on the
`CallToolResult`) rather than as JSON-RPC `-32602` errors.

This gives the orchestrator a single, consistent place to reason about
retry-ability, required context, and upstream status.

## Tool → error mapping

| Tool | Error raised | `can_retry` | `errorKind` | Extras |
|---|---|---|---|---|
| `parse_date("not a date")` | `RetryableToolError` | `True` | `TOOL_RUNTIME_RETRY` | `additional_prompt_content` |
| `lookup_user("alice")` | `ContextRequiredToolError` | `False` | `TOOL_RUNTIME_CONTEXT_REQUIRED` | `additional_prompt_content` (required) |
| `fetch_weather("x")` | `UpstreamRateLimitError` (~33% of the time) | `True` | `UPSTREAM_RUNTIME_RATE_LIMIT` | `status_code=429`, `retry_after_ms` |
| `call_upstream_with_expired_token()` | `UpstreamError(status=403)` | `False` | `UPSTREAM_RUNTIME_AUTH_ERROR` | `status_code=403` |
| `call_flaky_upstream()` | `UpstreamError(status=502)` | `True` | `UPSTREAM_RUNTIME_SERVER_ERROR` | `status_code=502` |
| `divide(1, 0)` | `FatalToolError` | `False` | `TOOL_RUNTIME_FATAL` | — |
| `mystery_bug()` | bare `RuntimeError` → wrapped as `FatalToolError` by the adapter chain | `False` | `TOOL_RUNTIME_FATAL` | developer_message carries the full `str(exc)`; `message` only carries the exception TYPE. |

## Running

```bash
uv sync
uv run python src/typed_errors/server.py        # stdio
uv run python src/typed_errors/server.py http   # HTTP
```

## Wire shape

A typed tool error on MCP 2025-11-25 looks like:

```jsonc
{
  "result": {
    "isError": true,
    "content": [
      {
        "type": "text",
        "text": "Could not parse 'not-a-date' as a date."
      }
    ],
    "_meta": {
      "arcade": {
        "errorKind": "TOOL_RUNTIME_RETRY",
        "canRetry": true,
        "additionalPromptContent": "Please retry with an ISO 8601 date string ..."
      }
    }
  }
}
```

Older (2025-06-18) sessions still see validation failures as JSON-RPC
`-32602`, but tool-body errors (everything in this example) have always been
returned as tool results — SEP-1303 just harmonises the validation path
with them.

## Retry policy semantics

- **`can_retry == True`** — the orchestrator MAY call the tool again with
  the same arguments (`RetryableToolError`) or adjusted arguments (when
  `additional_prompt_content` guides the LLM).
- **`can_retry == False`** — the orchestrator MUST NOT silently retry. For
  `ContextRequiredToolError`, it should surface
  `additional_prompt_content` to its planner or to a human. For
  `FatalToolError`, it should give up and report failure.
- **`retry_after_ms`** — on `RetryableToolError` and
  `UpstreamRateLimitError`, the orchestrator SHOULD back off by at least
  this many ms before retrying.

## The data-leak policy

Look at `mystery_bug`. It raises a bare `RuntimeError("surprise!")`. The
`@tool` decorator's fallback adapter wraps it as `FatalToolError`, but it
deliberately puts the exception **type only** in the agent-facing `message`
and keeps the full `str(exc)` in `developer_message` (server logs only).
This is intentional — tool authors often interpolate user input into
exception messages (`raise ValueError(f"Bad password: {password}")`) and
sending that content to the agent is a data-leak vector.

Authorised access to `developer_message` (logs, Datadog, ...) is the
security boundary, not the agent transport. See
`arcade_tdk/tool.py::_raise_as_arcade_error` for the policy.

## Related work

- **SEP-1303** — Input validation errors surface as tool execution errors
  (version-gated; 2025-11-25 clients see the new shape, older clients still
  see `-32602` for validation failures).
- `arcade_core.errors` — The error hierarchy. `ToolExecutionError` is the
  base class; everything in this example subclasses it.
- `arcade_tdk/tool.py` — The adapter chain that catches untyped exceptions
  and maps them through user-supplied / auth-provider / GraphQL / HTTP
  adapters before falling back to `FatalToolError`.

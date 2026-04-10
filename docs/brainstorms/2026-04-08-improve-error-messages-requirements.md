---
date: 2026-04-08
topic: improve-error-messages
---

# Improve Error Messages for Agents and Datadog

## Problem Frame

Tool call errors in production are often too short or generic to be useful. AI agents receiving these errors cannot self-correct, and engineers triaging in Datadog cannot classify failures without digging into raw logs.

The root causes are spread across three libraries:

1. **arcade-core** (`ToolExecutor`) produces generic `message` fields while burying useful detail in `developer_message`
2. **arcade-tdk** (`@tool` decorator fallback) wraps unhandled exceptions with `str(e)` which can be empty, cryptic, or missing context
3. **arcade-mcp-server** (`_handle_call_tool`) serializes `ToolCallError` via `str()` (Pydantic repr) instead of formatting clean agent-facing text and structured JSON

Two audiences consume these errors through different paths:

- **AI agents** via MCP `CallToolResult.content` + `structuredContent` -- token-sensitive, need compact actionable info
- **Engineers** via Datadog (Engine worker path logs `ToolCallOutput.error.message`) -- need classifiable, facet-able detail

Critical gap discovered in toolkit analysis: Toolkit authors (Google Sheets, Confluence, Attio) put recovery hints in `additional_prompt_content` (e.g., available sheet names, valid field options, available Atlassian Clouds). This field exists in `ToolCallError` but is **silently dropped** in the MCP response path -- `_handle_call_tool` uses `str(ToolCallError)` which buries it in a Pydantic repr dump. Agents never see the recovery context that toolkit authors carefully provided.

Evidence: Linear production export with ~500 error samples across 9 tools. Monorepo toolkit source code at `apps/worker/toolkits/` confirms error authoring patterns.

## Requirements

**Fix broken error messages at source**

- R1. `ToolInputError` message must include field names and error types from the Pydantic `ValidationError`, in compact form (no input values, no URLs). Format: `"Invalid input: {field} {msg}; {field} {msg}"`. The `developer_message` continues to carry the full `str(ValidationError)`.
- R2. `ToolOutputFactory.fail()` must guard against empty/whitespace `message`. When `message` is empty, substitute `"Unspecified error during tool execution"`.
- R3. The `@tool` decorator fallback `FatalToolError` (in `_raise_as_arcade_error`) must produce a message with exception type and context: `"{ExceptionType}: {str(e)}"` when `str(e)` is non-empty, or `"{ExceptionType} (no message)"` when empty. The `developer_message` should include `repr(exception)` for full debugging context.

**Fix MCP agent-facing response**

- R4. In `_handle_call_tool` error path (when `result.value` is None and `result.error` exists), `content` must be a clean human-readable text composed from the `ToolCallError` fields in this order, each on a new line, skipping any that are None/empty:
  1. `error.message` (always present)
  2. `error.additional_prompt_content` (critical: this carries recovery hints like available sheet names, valid field options -- toolkit authors rely on this reaching the agent)
  3. `error.developer_message` only when it differs from `message` and adds useful context
  This replaces the current `str(ToolCallError)` Pydantic repr which buries these fields in an unreadable dump.
- R5. In the same path, `structuredContent` must be `error.model_dump(mode="json", exclude_none=True)` instead of `{"error": str(error)}`. This gives agents structured access to `message`, `developer_message`, `kind`, `can_retry`, `additional_prompt_content`, `status_code`, and `extra` as real JSON fields.

**Improve log detail for Datadog**

- R6. In `BaseWorker.call_tool()` error logging, add structured `extra` dict to the warning log with: `error.kind`, `error.message`, `error.developer_message`, `error.status_code`, `error.can_retry`, `tool.name`, `tool.version`, `execution_id`. This enables Datadog faceting without parsing message strings.
- R7. In `_handle_call_tool` MCP error path, add equivalent structured logging with the same fields plus `session_id` when available.

## Success Criteria

- Every error message in the Linear export dataset that was previously generic now carries actionable detail
- Specifically: `"Error in tool input deserialization"` includes field names; `"'values'"` becomes `"KeyError: 'values'"` ; empty messages become `"Unspecified error during tool execution"`
- MCP `structuredContent` for errors is a JSON object with discrete fields, not a stringified Pydantic repr
- No change to error messages that are already informative (upstream errors from adapters, toolkit-raised `ToolExecutionError` with good messages)
- No user data (input values, secrets) leaked into `message` field
- Token impact on agent-facing `content` is minimal: only adds detail where currently missing

## Scope Boundaries

- Not fixing individual toolkit error messages (e.g., Confluence raising `FatalToolError("")`) -- that's toolkit responsibility, and R2+R3 provide the safety net
- Not changing `ErrorHandlingMiddleware` -- it handles non-tool MCP messages and `mask_error_details` defaults to false; it's a separate concern
- Not changing the `ToolCallError` schema or `ErrorKind` enum -- the existing structure is sound, just under-utilized
- Not changing Engine (Go) code -- the Engine already receives full `ToolCallError` JSON via `ToolCallResponse`; Datadog improvements come from richer `message` content (R1-R3) and structured worker logs (R6)
- Not adding new dependencies

## Key Decisions

- **Compact validation summary over full Pydantic string**: Full `str(ValidationError)` includes `input_value` (user data leak risk) and pydantic.dev URLs (token waste). Compact `"{field}: {msg}"` gives agents what they need to self-correct.
- **Fix at source (arcade-core, arcade-tdk) not just at MCP layer**: Every consumer benefits -- Engine, MCP, CLI, future consumers. More effective than downstream patching.
- **`model_dump` for structuredContent**: Zero token overhead (agents parse JSON selectively), enables programmatic error handling by agent frameworks.
- **Don't touch good messages**: Upstream error adapters (Google, HTTP) already produce informative, compact messages. Only fix what's broken.
- **Surface `additional_prompt_content` to agents**: This is the highest-impact fix. Toolkit authors already write recovery hints (available options, valid syntax, retry instructions) but the MCP path drops them. Surfacing this field requires zero toolkit changes and immediately improves agent self-correction for Google Sheets, Confluence, Attio, and all toolkits using `RetryableToolError`.

## Dependencies / Assumptions

- Engine (Go) indexes `output.error.message` from `ToolCallResponse` -- R1-R3 automatically improve what Engine/Datadog sees
- Agents consume `CallToolResult.content` as primary text and `structuredContent` as optional structured data -- R4 improves the primary, R5 improves the optional
- `developer_message` is not currently displayed to end-users anywhere -- safe to surface to agents in MCP `content` since agents are developers' tools

## Outstanding Questions

### Deferred to Planning

- [Affects R6][Technical] Verify whether Loguru's `extra` dict propagates to OTLP log exporter in the current telemetry setup
- [Affects R1][Needs research] Check if any toolkit tests assert on the exact `"Error in tool input deserialization"` string and would break

## Next Steps

→ `/ce:plan` for structured implementation planning

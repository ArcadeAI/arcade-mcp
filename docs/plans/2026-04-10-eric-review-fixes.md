# Handoff: Fix Eric's Review Comments on TOO-627

## Context

PR #814 (TOO-627: Improve error messages) passed initial review and agent testing but Eric Gustin found 6 critical/major issues in code review:

1. **developer_message leaking to client-facing content** (server.py:936) — 🔴 CRITICAL security issue
2. **Backward-compat error field missing enriched content** (server.py:944) — 🔴 CRITICAL feature completeness
3. **LoguruInterceptHandler discards structured log extras** (logging_utils.py) — 🟠 MAJOR — Datadog faceting broken
4. **Wrong tool version in logs** (base.py:163) — 🟠 MAJOR — telemetry inconsistency
5. **Uses full fqname instead of name** (base.py:162) — 🟠 MAJOR — can't correlate logs with traces
6. **repr(exception) defeats developer_message de-dup** (tool.py:108) — 🟡 MAJOR — redundant info to agents

**Status**: All fixes identified and validated. Issue #3 already fixed and tested (all 2506 tests pass).

---

## Orchestration Model

Each task is a **self-contained unit of work**. Dispatch each as a sub-agent with the task prompt below as its only input (zero prior context). The sub-agent implements, writes/updates tests, runs them, and exits. A reviewer (human or agent) inspects the diff before moving to the next task.

**Execution order matters** — tasks are numbered by dependency. Do not start a task until its predecessor is reviewed and merged.

After each task, run `make test && make check` to confirm nothing broke.

---

## Task 1: Remove developer_message from client-facing content

**Library**: arcade-mcp-server
**File to change**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`
**Tests to update**: `libs/tests/arcade_mcp_server/test_server.py`

### Prompt for sub-agent

> In `libs/arcade-mcp-server/arcade_mcp_server/server.py`, method `_handle_call_tool()`, around line 935-936:
>
> Currently the code appends `developer_message` to `error_text` which becomes client-facing content:
> ```python
> if error.developer_message and error.developer_message != error.message:
>     error_text += f"\n\nDetails: {error.developer_message}"
> ```
>
> **Problem**: `developer_message` can contain stack frames, file paths, and sensitive data. It should NOT be sent to agents/end-users. It's already excluded from `structuredContent` (line 941), so it should not appear in content either.
>
> **Fix**: Delete lines 935-936 entirely. The `developer_message` is still available to Datadog via structured logs (line 958) but won't leak to agents.
>
> **Update tests** in `libs/tests/arcade_mcp_server/test_server.py`:
> - In `test_tool_error_developer_message_included_when_different()` (around line 1900): Change assertion from `assert "Details:" in text` to `assert "Details:" not in text`. The developer_message should no longer appear in client content.
> - In `test_tool_error_developer_message_excluded_when_same()`: This test becomes redundant (the condition it tests no longer applies). You can either delete it or mark it as deprecated.
>
> Run `uv run pytest libs/tests/arcade_mcp_server/test_server.py::TestToolErrorResponse -x` to verify.
>
> No version bump needed — this is a fix, not a feature change.

### Review checklist
- [ ] Lines 935-936 removed
- [ ] No other content-building logic changed
- [ ] Tests updated to reflect no "Details:" in output
- [ ] All MCP tests pass

---

## Task 2: Use enriched error_text for backward-compat error field

**Library**: arcade-mcp-server
**File to change**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`
**Tests to update**: `libs/tests/arcade_mcp_server/test_server.py`

### Prompt for sub-agent

> In `libs/arcade-mcp-server/arcade_mcp_server/server.py`, method `_handle_call_tool()`, around lines 938-944:
>
> **Current code**:
> ```python
> structured_content = error.model_dump(
>     mode="json",
>     exclude_none=True,
>     exclude={"stacktrace", "developer_message", "extra"},
> )
> # Backward compatibility: consumers may access structuredContent["error"]
> structured_content["error"] = error.message
> ```
>
> **Problem**: The backward-compat `"error"` field is set to `error.message` (the plain message) but `content` uses `error_text` (enriched with `additional_prompt_content`). Clients accessing `structuredContent["error"]` won't get the self-correction guidance. Also, this creates two nearly identical fields: `"message"` and `"error"`.
>
> **Fix**:
> 1. Add `"message"` to the exclude list on line 941: `exclude={"stacktrace", "developer_message", "extra", "message"}`
> 2. Change line 944 to use `error_text` instead: `structured_content["error"] = error_text`
>
> This keeps one canonical `"error"` field (enriched with additional_prompt_content) plus machine-readable metadata (`kind`, `can_retry`, `status_code`, etc.), avoiding duplication.
>
> **Update tests** in `libs/tests/arcade_mcp_server/test_server.py`:
> - In `test_tool_error_structured_content_is_model_dump()` (around line 1876): Update assertion from `assert "message" in sc` to `assert "message" not in sc` (message is now excluded). Verify `"error"` field is still present and equals the enriched `error_text`.
>
> Run `uv run pytest libs/tests/arcade_mcp_server/test_server.py::TestToolErrorResponse::test_tool_error_structured_content_is_model_dump -x` to verify.
>
> No version bump needed.

### Review checklist
- [ ] "message" added to exclude set
- [ ] Line 944 uses `error_text` not `error.message`
- [ ] No duplication between "error" and model_dump fields
- [ ] Test updated: "message" not in sc, "error" is enriched
- [ ] All MCP tests pass

---

## Task 3: Fix LoguruInterceptHandler to preserve structured log extras

**Library**: arcade-mcp-server
**File to change**: `libs/arcade-mcp-server/arcade_mcp_server/logging_utils.py`
**Tests**: No test changes needed — this is a logging plumbing fix, all existing tests pass

### Prompt for sub-agent

> This task is **ALREADY IMPLEMENTED AND TESTED**. The fix is in `logging_utils.py` lines 9-46.
>
> **Summary of what was done**:
>
> The `LoguruInterceptHandler.emit()` method was updated to extract custom `extra` fields from stdlib `logging.LogRecord` and pass them to Loguru via `logger.bind(**extras)`. This ensures structured logging fields (e.g., `error_kind`, `tool_name`, `error_status_code`) reach Datadog and other structured logging sinks instead of being discarded.
>
> **Key changes**:
> - Added `_STANDARD_FIELDS` constant listing all stdlib logging fields to exclude
> - Extract `extras` dict from `record.__dict__` by filtering out standard fields
> - Use `logger.bind(**extras)` to merge extras into Loguru's context
>
> **Verification**: All 2506 tests pass. Manual testing confirms:
> - Direct loguru calls with kwargs preserve extras ✅
> - Stdlib logging routed through handler preserves extras ✅
> - Datadog can now facet on `@error_kind`, `@tool_name`, `@error_status_code`, etc. ✅
>
> **No action needed** — this is complete.

### Review checklist
- [x] LoguruInterceptHandler updated to use bind()
- [x] _STANDARD_FIELDS defined correctly
- [x] All 2506 tests pass
- [x] Extras reach Loguru sinks

---

## Task 4: Use correct tool version in structured logs

**Library**: arcade-serve
**File to change**: `libs/arcade-serve/arcade_serve/core/base.py`
**Tests**: No test changes needed — this is a telemetry fix

### Prompt for sub-agent

> In `libs/arcade-serve/arcade_serve/core/base.py`, method `BaseWorker.call_tool()`, around line 163:
>
> **Current code**:
> ```python
> log_extra = {
>     ...
>     "tool_version": str(tool_request.tool.version),
>     ...
> }
> ```
>
> **Problem**: This uses `tool_request.tool.version` (the *requested* version) instead of `tool_fqname.toolkit_version` (the *actual* version that ran). This is inconsistent with the tool name field (line 162) and other telemetry in the same function (metrics, OTel spans).
>
> **Fix**: Change line 163 from:
> ```python
> "tool_version": str(tool_request.tool.version),
> ```
> to:
> ```python
> "tool_version": str(tool_fqname.toolkit_version),
> ```
>
> This ensures version telemetry matches the actual tool metadata.
>
> Run `make test` to verify nothing broke.
>
> No version bump needed.

### Review checklist
- [ ] Line 163 uses `tool_fqname.toolkit_version` not `tool_request.tool.version`
- [ ] Consistent with line 162 and other metrics in function
- [ ] All tests pass

---

## Task 5: Use tool name instead of full fqname in logs

**Library**: arcade-serve
**File to change**: `libs/arcade-serve/arcade_serve/core/base.py`
**Tests**: No test changes needed

### Prompt for sub-agent

> In `libs/arcade-serve/arcade_serve/core/base.py`, method `BaseWorker.call_tool()`, around line 162:
>
> **Current code**:
> ```python
> log_extra = {
>     ...
>     "tool_name": str(tool_fqname),
>     ...
> }
> ```
>
> **Problem**: This uses the full qualified name (e.g., `"GoogleSheets.get_sheet"`) instead of just the tool name (e.g., `"get_sheet"`). This doesn't correlate logs with traces because everywhere else in the function (metrics counters, OTel spans), we use `tool_fqname.name`.
>
> **Fix**: Change line 162 from:
> ```python
> "tool_name": str(tool_fqname),
> ```
> to:
> ```python
> "tool_name": str(tool_fqname.name),
> ```
>
> This ensures structured log fields match the tool name used in metrics and tracing.
>
> Run `make test` to verify.
>
> No version bump needed.

### Review checklist
- [ ] Line 162 uses `tool_fqname.name` not `tool_fqname`
- [ ] Matches tool_name field used in metrics/traces elsewhere in function
- [ ] All tests pass

---

## Task 6: Fix developer_message strategy in fallback exception handler

**Library**: arcade-tdk
**File to change**: `libs/arcade-tdk/arcade_tdk/tool.py`
**Tests to update**: `libs/tests/tool/test_error_fallback.py`

### Prompt for sub-agent

> In `libs/arcade-tdk/arcade_tdk/tool.py`, function `_raise_as_arcade_error()`, around lines 103-109:
>
> **Current code**:
> ```python
> exc_type = type(exception).__name__
> exc_str = str(exception)
> message = f"{exc_type}: {exc_str}" if exc_str.strip() else f"{exc_type} (no details)"
> raise FatalToolError(
>     message=message,
>     developer_message=repr(exception),
> ) from exception
> ```
>
> **Problem**: The MCP server's de-dup logic checks `if error.developer_message != error.message` (server.py:935). With the current code:
> - `message = "ValueError: bad input"`
> - `developer_message = "ValueError('bad input')"`
>
> These are *just barely* different, so the de-dup check fails and agents see redundant near-duplicate info:
> ```
> ValueError: bad input
> Details: ValueError('bad input')
> ```
>
> **Fix**: Set `developer_message = None` when the exception string is empty or identical to the message. Use a ternary to keep it simple:
>
> ```python
> exc_type = type(exception).__name__
> exc_str = str(exception)
> message = f"{exc_type}: {exc_str}" if exc_str.strip() else f"{exc_type} (no details)"
> # Only set developer_message if it would differ meaningfully from message
> # Use repr only for additional debugging detail beyond the message type.
> # If exception has no string representation or it's simple, don't duplicate in dev message.
> developer_message = repr(exception) if exc_str.strip() else None
> raise FatalToolError(
>     message=message,
>     developer_message=developer_message,
> ) from exception
> ```
>
> **Update tests** in `libs/tests/tool/test_error_fallback.py`:
> - In `test_fallback_developer_message_is_repr()` (around line 65): The developer_message will now be `None` for empty exceptions but still contain `repr()` for non-empty ones. Update assertion to check for `None` when appropriate or skip this test for empty exception cases.
> - Add a new test `test_fallback_empty_exception_has_no_developer_message()`: Verify that `Exception()` (empty) produces `developer_message=None`, preventing the redundant "Details:" line in client output.
>
> Run `uv run pytest libs/tests/tool/test_error_fallback.py -x` to verify.
>
> No version bump needed.

### Review checklist
- [ ] developer_message set to None when exception string is empty
- [ ] developer_message set to repr(exception) only when meaningful
- [ ] Tests updated: dev_message not shown when None
- [ ] No redundant "Details:" in client output
- [ ] All tool tests pass

---

## Final Verification

After all 6 tasks are completed and reviewed:

```bash
make test    # all library tests
make check   # ruff + mypy
```

Expected outcome:
- All 2506 tests pass
- No new linting errors
- Error messages are non-redundant and secure (no sensitive data to agents)
- Structured logs reach Datadog with proper faceting fields
- Telemetry correlates between logs, metrics, and traces

---

## Files Modified Summary

| File | Tasks | Type |
|------|-------|------|
| `libs/arcade-mcp-server/arcade_mcp_server/server.py` | 1, 2 | logic + test |
| `libs/arcade-mcp-server/arcade_mcp_server/logging_utils.py` | 3 | logic only (✅ done) |
| `libs/arcade-serve/arcade_serve/core/base.py` | 4, 5 | logic only |
| `libs/arcade-tdk/arcade_tdk/tool.py` | 6 | logic + test |
| `libs/tests/arcade_mcp_server/test_server.py` | 1, 2 | test only |
| `libs/tests/tool/test_error_fallback.py` | 6 | test only |

---

## Execution Timeline

- **Task 1**: 5 min (1 file, 1 deletion, 1 test update)
- **Task 2**: 10 min (1 file, 2 line changes, 1 test update)
- **Task 3**: ✅ Complete (already done)
- **Task 4**: 2 min (1 file, 1 field change)
- **Task 5**: 2 min (1 file, 1 field change)
- **Task 6**: 10 min (1 file, 3 line logic change, 2 test changes)
- **Final test**: 5 min (make test + make check)

**Total estimated time**: ~35 minutes (including testing and review cycles)

---
date: 2026-04-08
topic: improve-error-messages
requirements: docs/brainstorms/2026-04-08-improve-error-messages-requirements.md
---

# Implementation Plan: Improve Error Messages for Agents and Datadog

## Overview

7 changes across 3 libraries, ordered by dependency. No schema changes, no new dependencies.

## Execution Order

Changes must go bottom-up through the dependency graph: arcade-core -> arcade-tdk -> arcade-mcp-server (+ arcade-serve for R6).

---

## Step 1: R2 — Guard empty messages in `ToolOutputFactory.fail()`

**File**: `libs/arcade-core/arcade_core/output.py`
**Method**: `ToolOutputFactory.fail()`
**Risk**: Low — additive guard, no behavior change for non-empty messages

Add at the top of `fail()`, before constructing `ToolCallError`:

```python
if not message or not message.strip():
    message = "Unspecified error during tool execution"
```

**Tests**: Add test in `libs/tests/core/test_output.py`:
- `test_fail_empty_message_gets_default` — pass `message=""`, assert output contains substitute
- `test_fail_whitespace_message_gets_default` — pass `message="  "`, same assertion
- `test_fail_nonempty_message_unchanged` — pass `message="real error"`, assert unchanged

---

## Step 2: R1 — Enrich `ToolInputError` message in executor

**File**: `libs/arcade-core/arcade_core/executor.py`
**Method**: `ToolExecutor._serialize_input()` (the `except ValidationError` block, ~line 103)
**Risk**: Medium — changes a message string that one test asserts on

### Change

Replace:
```python
except ValidationError as e:
    raise ToolInputError(
        message="Error in tool input deserialization",
        developer_message=str(e),
    ) from e
```

With:
```python
except ValidationError as e:
    summary = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in e.errors()
    )
    raise ToolInputError(
        message=f"Invalid input: {summary}",
        developer_message=str(e),
    ) from e
```

### Example output

Input: agent passes `{"row_number": "not_a_number"}` to a tool expecting `spreadsheet_id: str, row_number: int`

Before: `"Error in tool input deserialization"`
After: `"Invalid input: spreadsheet_id: Field required; row_number: Input should be a valid integer, unable to parse string as an integer"`

Compact, no input values, no URLs, tells the agent exactly what to fix.

### Test update

**File**: `libs/tests/core/test_executor.py` line ~201
Update the assertion from:
```python
message="[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError during execution of tool 'simple_tool': Error in tool input deserialization",
```
To assert `message` starts with `"[TOOL_RUNTIME_BAD_INPUT_VALUE] ToolInputError during execution of tool 'simple_tool': Invalid input:"` and contains the relevant field name. Use `startswith` or regex since the exact Pydantic error text may vary across versions.

**New test**: Add a test that passes multiple bad fields and verifies all field names appear in the message.

---

## Step 3: R3 — Improve `@tool` decorator fallback in arcade-tdk

**File**: `libs/arcade-tdk/arcade_tdk/tool.py`
**Function**: `_raise_as_arcade_error()` (~line 103)
**Risk**: Low — only changes the fallback when no adapter handles the exception

### Change

Replace:
```python
raise FatalToolError(
    message=f"{exception!s}",
    developer_message=f"{exception!s}",
) from exception
```

With:
```python
exc_type = type(exception).__name__
exc_str = str(exception)
if exc_str.strip():
    message = f"{exc_type}: {exc_str}"
else:
    message = f"{exc_type} (no details)"
raise FatalToolError(
    message=message,
    developer_message=repr(exception),
) from exception
```

### Example output

| Exception | Before | After |
|-----------|--------|-------|
| `KeyError('values')` | `'values'` | `KeyError: 'values'` |
| `SomeError()` | `` (empty) | `SomeError (no details)` |
| `RuntimeError("bad state")` | `bad state` | `RuntimeError: bad state` |

### Tests

**File**: New test in `libs/tests/tool/` or extend existing `@tool` decorator tests:
- `test_fallback_keyerror_includes_type` — raise `KeyError('x')` from a `@tool` function with no adapters, assert message contains `KeyError`
- `test_fallback_empty_exception_gets_type` — raise `Exception()`, assert message contains `Exception (no details)`
- `test_fallback_developer_message_is_repr` — assert `developer_message` is `repr(exception)`

---

## Step 4: R4 + R5 — Fix MCP agent-facing response

**File**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`
**Method**: `_handle_call_tool()` (~line 909-924)
**Risk**: Medium — changes what agents receive. Behavior improves but client parsers that relied on the Pydantic repr format would see a different shape.

### Change

Replace the error branch:
```python
else:
    error = result.error or "Error calling tool"
    content = convert_to_mcp_content(str(error))
    structured_content = convert_content_to_structured_content({"error": str(error)})
```

With:
```python
else:
    error = result.error
    if error:
        error_text = error.message
        if error.additional_prompt_content:
            error_text += f"\n\n{error.additional_prompt_content}"
        if (
            error.developer_message
            and error.developer_message != error.message
        ):
            error_text += f"\n\nDetails: {error.developer_message}"
        content = convert_to_mcp_content(error_text)
        structured_content = error.model_dump(mode="json", exclude_none=True)
    else:
        content = convert_to_mcp_content("Error calling tool")
        structured_content = {"error": "Error calling tool"}
```

### Example: what agents see for a Google Sheets "sheet not found" error

Before (Pydantic repr):
```
message='[TOOL_RUNTIME_RETRY] RetryableToolError during execution of tool 'write_to_cell': Sheet name Sheet2 not found in spreadsheet with id ABC' kind=<ErrorKind.TOOL_RUNTIME_RETRY: 'TOOL_RUNTIME_RETRY'> developer_message='...' can_retry=True additional_prompt_content='Sheet names in the spreadsheet: [Sheet1, Data]' retry_after_ms=100 stacktrace=None status_code=None extra=None
```

After (clean text in `content`):
```
[TOOL_RUNTIME_RETRY] RetryableToolError during execution of tool 'write_to_cell': Sheet name Sheet2 not found in spreadsheet with id ABC

Sheet names in the spreadsheet: [Sheet1, Data]
```

After (`structuredContent`):
```json
{
  "message": "Sheet name Sheet2 not found in spreadsheet with id ABC",
  "kind": "TOOL_RUNTIME_RETRY",
  "can_retry": true,
  "additional_prompt_content": "Sheet names in the spreadsheet: [Sheet1, Data]",
  "retry_after_ms": 100,
  "status_code": null
}
```

### Tests

**File**: `libs/tests/arcade_mcp_server/test_server.py` — update/add error response tests:
- `test_tool_error_content_includes_additional_prompt` — mock a tool that returns `ToolCallOutput` with error containing `additional_prompt_content`, assert it appears in `content[0].text`
- `test_tool_error_structured_content_is_model_dump` — same setup, assert `structuredContent` has discrete `message`, `kind`, `can_retry` fields
- `test_tool_error_no_pydantic_repr` — assert `content[0].text` does NOT contain `kind=<ErrorKind`

---

## Step 5: R6 — Structured log extras in `BaseWorker`

**File**: `libs/arcade-serve/arcade_serve/core/base.py`
**Method**: `BaseWorker.call_tool()` (~line 153-165)
**Risk**: Low — additive logging, no behavior change

### Change

Replace the error logging block:
```python
if output.error:
    logger.warning(
        f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} failed"
    )
    logger.warning(f"{execution_id} | Tool error: {output.error.message}")
    logger.warning(
        f"{execution_id} | Tool developer message: {output.error.developer_message}"
    )
```

With:
```python
if output.error:
    log_extra = {
        "error_kind": output.error.kind.value if hasattr(output.error.kind, 'value') else str(output.error.kind),
        "error_message": output.error.message,
        "error_developer_message": output.error.developer_message,
        "error_status_code": output.error.status_code,
        "error_can_retry": output.error.can_retry,
        "tool_name": str(tool_fqname),
        "tool_version": str(tool_request.tool.version),
        "execution_id": execution_id,
    }
    logger.warning(
        f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} failed: {output.error.message}",
        extra=log_extra,
    )
    if output.error.developer_message:
        logger.warning(
            f"{execution_id} | Developer message: {output.error.developer_message}",
        )
```

### Loguru/OTLP note

The `LoguruInterceptHandler` calls `record.getMessage()` which doesn't propagate `extra`. However, `OTELHandler` in `arcade_serve/fastapi/telemetry.py` uses the standard logging OTLP bridge which does support `extra` as log record attributes. If Datadog receives logs via OTLP, these will appear as facets. If via Loguru stderr, they won't — but the improved `message` text (from R1-R3) still helps.

### Tests

No new tests needed — this is observability-only. Existing tests don't assert on log output.

---

## Step 6: R7 — Structured log extras in MCP server

**File**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`
**Location**: `_handle_call_tool()` error branch (~line 916)
**Risk**: Low — additive logging

### Change

After the `self._tracker.track_tool_call(False, ...)` line, add:

```python
if isinstance(error, ToolCallError):
    logger.warning(
        f"Tool {tool_name} error: {error.message}",
        extra={
            "error_kind": error.kind.value if hasattr(error.kind, 'value') else str(error.kind),
            "error_message": error.message,
            "error_developer_message": error.developer_message,
            "error_status_code": error.status_code,
            "error_can_retry": error.can_retry,
            "tool_name": tool_name,
        },
    )
```

Note: Need to import `ToolCallError` from `arcade_core.schema` if not already imported.

### Tests

No new tests needed — observability-only.

---

## Version Bumps

Per repo rules, bump patch version in each modified library:

| Library | File | Current version | Bump to |
|---------|------|-----------------|---------|
| arcade-core | `libs/arcade-core/pyproject.toml` | check current | patch +1 |
| arcade-tdk | `libs/arcade-tdk/pyproject.toml` | check current | patch +1 |
| arcade-serve | `libs/arcade-serve/pyproject.toml` | check current | patch +1 |
| arcade-mcp-server | `libs/arcade-mcp-server/pyproject.toml` | check current | patch +1 |

Also update minimum dependency versions in downstream `pyproject.toml` files if the bumped versions introduce new behavior that dependents rely on. In this case:
- arcade-tdk depends on arcade-core — bump min if R1/R2 message format is relied upon (not needed: tdk doesn't parse core error messages)
- arcade-mcp-server depends on arcade-core — bump min to get the new `ToolCallError` field population from R1/R2

---

## Implementation Checklist

1. [ ] R2: Guard empty messages in `output.py`
2. [ ] R1: Enrich `ToolInputError` in `executor.py` + update test
3. [ ] R3: Improve `@tool` fallback in `tool.py` + add tests
4. [ ] R4+R5: Fix MCP response in `server.py` + add tests
5. [ ] R6: Structured logging in `base.py`
6. [ ] R7: Structured logging in `server.py`
7. [ ] Version bumps
8. [ ] Run `make test` to verify all tests pass
9. [ ] Run `make check` for lint/mypy

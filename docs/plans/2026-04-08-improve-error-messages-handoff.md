# Handoff: Improve Error Messages for Agents and Datadog

## Context

Tool call errors in production are generic or missing detail. Agents can't self-correct, Datadog can't facet. The fix spans 4 libraries in this monorepo.

**Requirements**: `docs/brainstorms/2026-04-08-improve-error-messages-requirements.md`
**Full plan**: `docs/plans/2026-04-08-improve-error-messages-plan.md`

## Orchestration Model

Each task below is a **self-contained unit of work**. Dispatch each as a sub-agent with the task prompt below as its only input (zero prior context). The sub-agent implements, writes tests, runs them, and exits. A reviewer (human or agent) inspects the diff before moving to the next task.

**Execution order matters** — tasks are numbered by dependency. Do not start a task until its predecessor is reviewed and merged.

After each task, run `make test && make check` to confirm nothing broke.

---

## Task 1: Guard empty error messages

**Library**: arcade-core
**Files to change**: `libs/arcade-core/arcade_core/output.py`
**Files to add tests**: `libs/tests/core/test_output.py`

### Prompt for sub-agent

> In `libs/arcade-core/arcade_core/output.py`, method `ToolOutputFactory.fail()`:
>
> Add a guard at the top of `fail()` before constructing `ToolCallError`: if `message` is empty or whitespace-only, replace it with `"Unspecified error during tool execution"`.
>
> Add tests in `libs/tests/core/test_output.py`:
> - `test_fail_empty_message_gets_default`: pass `message=""`, assert the output error message is the substitute string
> - `test_fail_whitespace_message_gets_default`: pass `message="  "`, same
> - `test_fail_nonempty_message_unchanged`: pass `message="real error"`, assert unchanged
>
> Run `uv run pytest libs/tests/core/test_output.py -x` to verify.
> Bump the patch version in `libs/arcade-core/pyproject.toml`.

### Review checklist
- [ ] Guard covers both `""` and `"   "`
- [ ] No other behavior changed
- [ ] Tests pass

---

## Task 2: Enrich input validation error messages

**Library**: arcade-core
**Files to change**: `libs/arcade-core/arcade_core/executor.py`
**Files to update tests**: `libs/tests/core/test_executor.py`

### Prompt for sub-agent

> In `libs/arcade-core/arcade_core/executor.py`, method `ToolExecutor._serialize_input()`, the `except ValidationError` block (~line 103):
>
> Replace the generic message `"Error in tool input deserialization"` with a compact summary of which fields failed and why. Build it from `e.errors()`:
>
> ```python
> summary = "; ".join(
>     f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
>     for err in e.errors()
> )
> raise ToolInputError(
>     message=f"Invalid input: {summary}",
>     developer_message=str(e),
> ) from e
> ```
>
> This gives agents field-level feedback like `"Invalid input: spreadsheet_id: Field required; row_number: Input should be a valid integer"`. It excludes `input_value` (user data) and pydantic URLs (token waste).
>
> Update the test in `libs/tests/core/test_executor.py` (~line 201) that asserts on the exact string `"Error in tool input deserialization"`. Change the assertion to verify the message starts with `"Invalid input:"` and contains the failing field name (`inp`). Use `assert "Invalid input:" in output.error.message` rather than exact string match, since Pydantic error text can vary across versions.
>
> Add a new test `test_multiple_bad_fields_in_input_error` that passes multiple invalid fields and verifies all field names appear in the message.
>
> Run `uv run pytest libs/tests/core/test_executor.py -x` to verify.
> Version was already bumped in Task 1.

### Review checklist
- [ ] No `input_value` in the message (no user data leak)
- [ ] No pydantic.dev URLs in the message
- [ ] Field names present for each validation error
- [ ] `developer_message` still has full `str(ValidationError)`
- [ ] Updated test is not brittle (no exact string match on pydantic text)

---

## Task 3: Improve `@tool` decorator error fallback

**Library**: arcade-tdk
**Files to change**: `libs/arcade-tdk/arcade_tdk/tool.py`
**Files to add tests**: `libs/tests/tool/` (add or extend)

### Prompt for sub-agent

> In `libs/arcade-tdk/arcade_tdk/tool.py`, function `_raise_as_arcade_error()` (~line 103):
>
> The current fallback raises `FatalToolError(message=f"{exception!s}", developer_message=f"{exception!s}")`. This produces empty or cryptic messages for exceptions like `KeyError('values')` → `"'values'"` or `Exception()` → `""`.
>
> Replace with:
>
> ```python
> exc_type = type(exception).__name__
> exc_str = str(exception)
> if exc_str.strip():
>     message = f"{exc_type}: {exc_str}"
> else:
>     message = f"{exc_type} (no details)"
> raise FatalToolError(
>     message=message,
>     developer_message=repr(exception),
> ) from exception
> ```
>
> Add tests (find existing `@tool` tests or create new ones in `libs/tests/tool/`):
> - `test_fallback_keyerror_includes_type`: a `@tool` function raises bare `KeyError('x')` with no error adapters, assert the resulting error message contains `"KeyError"`
> - `test_fallback_empty_exception_shows_type`: a `@tool` function raises `Exception()`, assert message contains `"Exception (no details)"`
> - `test_fallback_developer_message_is_repr`: assert `developer_message` equals `repr(exception)`
>
> Run `uv run pytest libs/tests/tool/ -x` to verify.
> Bump the patch version in `libs/arcade-tdk/pyproject.toml`.

### Review checklist
- [ ] `KeyError('values')` → message is `"KeyError: 'values'"` not `"'values'"`
- [ ] Empty exception → message is `"{Type} (no details)"` not `""`
- [ ] `developer_message` has `repr()` for full debugging
- [ ] Exceptions that already map via adapters are NOT affected (the change is only in the final fallback)

---

## Task 4: Fix MCP agent-facing error response

**Library**: arcade-mcp-server
**Files to change**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`
**Files to update tests**: `libs/tests/arcade_mcp_server/test_server.py`

### Prompt for sub-agent

> In `libs/arcade-mcp-server/arcade_mcp_server/server.py`, method `_handle_call_tool()`, the error branch starting at ~line 909 (the `else` block when `result.value` is None):
>
> **Problem**: Currently does `str(error)` on a `ToolCallError` Pydantic model, producing an unreadable repr dump. The field `additional_prompt_content` (which carries recovery hints like available sheet names) is buried and never shown cleanly to agents.
>
> **Replace the block**:
> ```python
> else:
>     error = result.error or "Error calling tool"
>     content = convert_to_mcp_content(str(error))
>     structured_content = convert_content_to_structured_content({"error": str(error)})
> ```
>
> **With**:
> ```python
> else:
>     error = result.error
>     if error:
>         error_text = error.message
>         if error.additional_prompt_content:
>             error_text += f"\n\n{error.additional_prompt_content}"
>         if (
>             error.developer_message
>             and error.developer_message != error.message
>         ):
>             error_text += f"\n\nDetails: {error.developer_message}"
>         content = convert_to_mcp_content(error_text)
>         structured_content = error.model_dump(mode="json", exclude_none=True)
>     else:
>         content = convert_to_mcp_content("Error calling tool")
>         structured_content = {"error": "Error calling tool"}
> ```
>
> `ToolCallError` is imported from `arcade_core.schema` — verify the import exists or add it.
>
> **Add/update tests** in `libs/tests/arcade_mcp_server/test_server.py`:
> - `test_tool_error_content_includes_additional_prompt`: mock a tool returning `ToolCallOutput` with error that has `additional_prompt_content="Available options: X, Y"`, assert it appears in the response `content[0].text`
> - `test_tool_error_structured_content_is_model_dump`: same setup, assert `structuredContent` has discrete `message`, `kind` keys (not a string)
> - `test_tool_error_content_no_pydantic_repr`: assert `content[0].text` does NOT contain `kind=<ErrorKind` (the Pydantic repr pattern)
> - `test_tool_error_developer_message_included_when_different`: error with different `developer_message`, assert "Details:" appears
> - `test_tool_error_developer_message_excluded_when_same`: error where `developer_message == message`, assert "Details:" does NOT appear
>
> Run `uv run pytest libs/tests/arcade_mcp_server/ -x` to verify.
> Bump the patch version in `libs/arcade-mcp-server/pyproject.toml`.

### Review checklist
- [ ] `additional_prompt_content` appears in `content` text (the critical fix)
- [ ] `structuredContent` is a real JSON object with `message`, `kind`, `can_retry` fields
- [ ] No Pydantic repr in `content` text
- [ ] `developer_message` only shown when it adds value (differs from `message`)
- [ ] Fallback `"Error calling tool"` still works when `result.error` is None

---

## Task 5: Add structured log extras in BaseWorker

**Library**: arcade-serve
**Files to change**: `libs/arcade-serve/arcade_serve/core/base.py`

### Prompt for sub-agent

> In `libs/arcade-serve/arcade_serve/core/base.py`, method `BaseWorker.call_tool()`, the error logging block (~line 153-165):
>
> The current code logs error message and developer_message as separate unstructured `logger.warning()` calls. Add a structured `extra` dict to the first warning call for Datadog faceting:
>
> Replace:
> ```python
> if output.error:
>     logger.warning(
>         f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} failed"
>     )
>     logger.warning(f"{execution_id} | Tool error: {output.error.message}")
>     logger.warning(
>         f"{execution_id} | Tool developer message: {output.error.developer_message}"
>     )
> ```
>
> With:
> ```python
> if output.error:
>     log_extra = {
>         "error_kind": output.error.kind.value if hasattr(output.error.kind, "value") else str(output.error.kind),
>         "error_message": output.error.message,
>         "error_developer_message": output.error.developer_message,
>         "error_status_code": output.error.status_code,
>         "error_can_retry": output.error.can_retry,
>         "tool_name": str(tool_fqname),
>         "tool_version": str(tool_request.tool.version),
>         "execution_id": execution_id,
>     }
>     logger.warning(
>         f"{execution_id} | Tool {tool_fqname} version {tool_request.tool.version} failed: {output.error.message}",
>         extra=log_extra,
>     )
>     if output.error.developer_message:
>         logger.warning(
>             f"{execution_id} | Developer message: {output.error.developer_message}",
>         )
> ```
>
> Keep the existing `logger.debug` calls for `duration`, `output.value`, and `stacktrace` unchanged.
>
> Run `uv run pytest libs/tests/ -x` to verify nothing broke.
> Bump the patch version in `libs/arcade-serve/pyproject.toml`.

### Review checklist
- [ ] `extra` dict has all fields listed
- [ ] Debug-level logs unchanged
- [ ] No test regressions

---

## Task 6: Add structured log extras in MCP server

**Library**: arcade-mcp-server
**Files to change**: `libs/arcade-mcp-server/arcade_mcp_server/server.py`

### Prompt for sub-agent

> In `libs/arcade-mcp-server/arcade_mcp_server/server.py`, method `_handle_call_tool()`, in the error branch (~after line 916 where `self._tracker.track_tool_call(False, "error during tool execution")` is called):
>
> Add structured error logging. Import `ToolCallError` from `arcade_core.schema` if not already imported.
>
> Add after the tracker call:
> ```python
> if isinstance(error, ToolCallError):
>     logger.warning(
>         f"Tool {tool_name} error: {error.message}",
>         extra={
>             "error_kind": error.kind.value if hasattr(error.kind, "value") else str(error.kind),
>             "error_message": error.message,
>             "error_developer_message": error.developer_message,
>             "error_status_code": error.status_code,
>             "error_can_retry": error.can_retry,
>             "tool_name": tool_name,
>         },
>     )
> ```
>
> Note: `error` here is `result.error` which is a `ToolCallError` Pydantic model (from `arcade_core.schema`), not a Python exception.
>
> Run `uv run pytest libs/tests/arcade_mcp_server/ -x` to verify.
> Version was already bumped in Task 4.

### Review checklist
- [ ] Import added if needed
- [ ] Only logs when `error` is a `ToolCallError` instance
- [ ] No test regressions

---

## Final Verification

After all 6 tasks are reviewed and merged:

```bash
make test    # all library tests
make check   # ruff + mypy
```

Verify with a sample from the Linear data — the 3 worst error patterns should now produce:

| Before | After |
|--------|-------|
| `"Error in tool input deserialization"` | `"Invalid input: spreadsheet_id: Field required; row_number: Input should be a valid integer"` |
| `"'values'"` | `"KeyError: 'values'"` |
| `"FatalToolError during execution of tool 'get_space': "` | `"FatalToolError during execution of tool 'get_space': SomeException (no details)"` |

And agents now see `additional_prompt_content` (e.g., available sheet names) instead of a Pydantic repr dump.

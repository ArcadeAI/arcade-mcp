---
name: build-error-adapter
description: Build new Arcade error adapters from scratch using the monorepo's established patterns. Use when adding provider integrations, mapping SDK exceptions, or extending HTTP/GraphQL/auth adapter behavior.
---

# Build Error Adapter

Use this workflow to create new error adapters that fit Arcade TDK conventions.

## Quick Context

- Adapter protocol: `libs/arcade-tdk/arcade_tdk/error_adapters/base.py`
- Adapter chain builder: `libs/arcade-tdk/arcade_tdk/tool.py` (`_build_adapter_chain`)
- Existing references:
  - `libs/arcade-tdk/arcade_tdk/providers/http/error_adapter.py`
  - `libs/arcade-tdk/arcade_tdk/providers/graphql/error_adapter.py`
  - `libs/arcade-tdk/arcade_tdk/providers/google/error_adapter.py`
  - `libs/arcade-tdk/arcade_tdk/providers/microsoft/error_adapter.py`
  - `libs/arcade-tdk/arcade_tdk/providers/slack/error_adapter.py`

## Rules To Follow

1. Keep imports at top-level only (no inline imports), except optional dependency imports that must be lazy by design.
2. Adapter interface contract:
   - `slug` class attribute
   - `from_exception(self, exc: Exception) -> ToolRuntimeError | None`
3. Return `None` when the exception is not recognized for that adapter.
4. Return a `ToolRuntimeError` subclass for recognized exceptions (`UpstreamError`, `UpstreamRateLimitError`, etc.).
5. Preserve privacy:
   - Agent-facing `message` must be safe.
   - Put raw vendor detail into `developer_message` when needed.
6. Add tests for every new mapping path.
7. If `libs/arcade-tdk` code changes, bump `libs/arcade-tdk/pyproject.toml` version once.

## Implementation Pattern

### 1) Create adapter skeleton

```python
from arcade_core.errors import ToolRuntimeError


class VendorErrorAdapter:
    slug = "_vendor"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        # recognize typed vendor exceptions
        # return mapped ToolRuntimeError
        return None
```

### 2) Use typed exception matching

- Match most specific subclasses first.
- Keep a final typed fallback for broad vendor exceptions.
- Avoid broad `except Exception` handling inside `from_exception`.

Example ordering:

1. Rate limit subtype
2. Auth subtype
3. Timeout/transport subtype
4. General vendor exception fallback

### 3) Normalize metadata

Follow the HTTP/GraphQL adapters:

- Include `extra["service"] = self.slug`
- Include `extra["error_type"] = type(exc).__name__` for non-status failures
- Include sanitized endpoint/method when available

### 4) Map status-like semantics consistently

- 429 -> `UpstreamRateLimitError` with `retry_after_ms`
- 5xx/transient transport -> retryable `UpstreamError` (`status_code >= 500`)
- 4xx client/config issues -> non-retryable `UpstreamError`

Use deterministic mappings so retry behavior is predictable (`UpstreamError` derives retryability from status code).

### 5) Optional dependency handling

For SDK-specific adapters, lazy-import the SDK module inside `from_exception`.

- If import fails, log and return `None`.
- Do not raise import errors from adapter code paths.

## Chain Integration Pattern

Adapters are executed in order in `_build_adapter_chain`:

1. user-provided adapters
2. auth-provider adapter (if mapped)
3. `GraphQLErrorAdapter`
4. `HTTPErrorAdapter` fallback

Integrate your adapter in one of two ways:

- User opt-in: pass via `@tool(adapters=[...])`
- Auth-driven: wire it in `error_adapters/utils.py` if tied to a specific auth provider

Deduplication is by adapter type, first occurrence wins.

## Required Test Matrix

Create/extend tests in `libs/tests/sdk/` (or relevant area):

- recognized typed exception -> expected `ToolRuntimeError` subclass
- expected `status_code`, `kind`, `can_retry`
- expected `extra` keys (`service`, `error_type`, endpoint/method when applicable)
- unknown exception returns `None`
- optional dependency missing path returns `None`

Suggested command:

```bash
uv run pytest libs/tests/sdk/test_httpx_adapter.py -q
```

Then run broader checks:

```bash
make check
```

## Done Checklist

- Adapter returns `ToolRuntimeError | None`
- Safe agent-facing messages
- Typed exception coverage added
- Tests added/updated and passing
- TDK version bumped (if TDK code changed)
- No stdout/stderr noise added in MCP runtime paths

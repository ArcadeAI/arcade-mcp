---
name: build-error-adapter
description: Build new Arcade error adapters from scratch using public Arcade TDK patterns. Use when adding provider integrations, mapping SDK exceptions, or extending HTTP/GraphQL/auth adapter behavior.
---

# Build Error Adapter

Use this workflow to create new error adapters that fit Arcade TDK conventions without relying on private monorepo paths.

## Official Reference

Start here and align behavior with this doc:

- [Arcade docs: Providing useful tool errors (Error adapters)](https://docs.arcade.dev/en/guides/create-tools/error-handling/useful-tool-errors#error-adapters)

## Quick Context

- Adapter protocol: `arcade_tdk.error_adapters.base.ErrorAdapter`
- Common error classes:
  - `arcade_tdk.errors.UpstreamError` — upstream responded with an HTTP status code
  - `arcade_tdk.errors.UpstreamRateLimitError` — 429 / quota-exhausted with `retry_after_ms`
  - `arcade_tdk.errors.NetworkTransportError` — no complete response was received
    (timeouts, connection/DNS/TLS failures, decoding errors, redirect exhaustion).
    `status_code` is always `None`; use one of the `NETWORK_TRANSPORT_RUNTIME_*`
    kinds: `_TIMEOUT`, `_UNREACHABLE`, `_UNMAPPED`.
  - `arcade_tdk.errors.FatalToolError` — unrecoverable tool-authoring bug or
    environment misconfiguration (invalid URL, unsupported protocol, bad headers,
    TLS trust failures). Never retried.
  - `arcade_tdk.errors.RetryableToolError` — transient tool-body failure with a
    hint for the LLM to retry.
  - `arcade_tdk.errors.ContextRequiredToolError` — needs human input before retry.

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
7. Match your installed Arcade version's decorator API and parameter names.

## Privacy Rule When Uncertain

If you are not fully sure what `str(exc)`, vendor `reason`, or nested payload fields can contain, treat them as potentially sensitive.

- Default to a safe agent-facing message template:
  - `"Upstream <Service> request failed with status code <code>."`
  - `"Upstream <Service> error: unhandled <ExceptionType>."`
- Put raw details in `developer_message` instead of `message`.
- Prefer structured non-secret context in `message` (status code, error class, stable provider error code).
- Never put tokens, auth headers, full URLs with query params, raw response bodies, or stack traces in agent-facing `message`.

Use this decision rule:

1. **Known-safe field** (documented stable code/reason without sensitive payload): may be included in `message`.
2. **Unknown or mixed-content field**: keep out of `message`; include only in `developer_message`.
3. **High-risk content** (headers/body/credential-like strings): never include in `message`; sanitize or omit even in `developer_message` if policy requires.

When in doubt, prefer slightly less detail in `message` and richer diagnostics in `developer_message`.

## Decide: Adapter vs explicit tool error

Use an **error adapter** when:

- You need repeatable translation from vendor exceptions to Arcade errors.
- The same exception family appears across multiple tools.

Raise explicit tool errors in tool code when:

- You need user guidance for immediate retry (`RetryableToolError`).
- You need user/orchestrator input before retry (`ContextRequiredToolError`).
- You need a special business rule for one endpoint/tool path only.

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

For adapted errors:

- Include `extra["service"] = self.slug`
- Include `extra["error_type"] = type(exc).__name__` for non-status failures
- Include sanitized endpoint/method when available

### 4) Map status-like semantics consistently

**Upstream responded with an HTTP status code → `UpstreamError`:**

- 429 → `UpstreamRateLimitError` with `retry_after_ms`
- 5xx → retryable `UpstreamError` (`status_code >= 500`)
- 4xx → non-retryable `UpstreamError`

`UpstreamError` derives retryability from status code, so predictable behavior is automatic.

**No complete response from upstream → `NetworkTransportError`:**

Use this class when the exception inherently means the request never reached the
upstream, or no complete response came back. `status_code` is `None` by design.

| Exception kind | `kind=` | `can_retry=` |
|---|---|---|
| Timeouts (connect, read, pool) | `NETWORK_TRANSPORT_RUNTIME_TIMEOUT` | `True` |
| Connection refused, DNS, TLS handshake, remote-protocol errors | `NETWORK_TRANSPORT_RUNTIME_UNREACHABLE` | `True` |
| Decoding failures, generic transport fallback | `NETWORK_TRANSPORT_RUNTIME_UNMAPPED` | `True` |
| Redirect-loop exhaustion | `NETWORK_TRANSPORT_RUNTIME_UNMAPPED` | `False` |

**Tool-authoring bugs / local environment misconfiguration → `FatalToolError`:**

Use this class for exceptions that will never succeed on retry — the tool's
code or environment needs to change:

- Invalid URL, unsupported scheme, missing scheme, bad headers, malformed local
  HTTP protocol state
- TLS / certificate / trust configuration failures (`ssl.SSLError` and siblings)

Do **not** dress these up as `UpstreamError` — an UpstreamError implies the
upstream service actually said "no". Miscategorizing pollutes telemetry and
sends the wrong retry signal.

### 5) Optional dependency handling

For SDK-specific adapters, lazy-import the SDK module inside `from_exception` if that dependency may be optional.

- If import fails, log and return `None`.
- Do not raise import errors from adapter code paths.

## Registration Pattern

For `httpx` and `requests`, automatic adaptation is typically available.

For SDK-specific adapters, register explicitly on tools.

```python
from arcade_mcp_server import tool
from arcade_tdk.error_adapters import GoogleErrorAdapter

@tool(
    # Depending on Arcade version, this may be `adapters=` or `error_adapters=`.
    adapters=[GoogleErrorAdapter()],
)
def my_tool(...) -> ...:
    ...
```

If your project uses a different parameter name, follow your installed API docs/signature.

## Required Test Matrix

Create or extend tests in your project test suite:

- recognized typed exception -> expected `ToolRuntimeError` subclass
- expected `status_code`, `kind`, `can_retry`
- expected `extra` keys (`service`, `error_type`, endpoint/method when applicable)
- unknown exception returns `None`
- optional dependency missing path returns `None`
- privacy split is verified:
  - `message` stays safe for uncertain/raw exceptions
  - `developer_message` carries deep diagnostics

## Done Checklist

- Adapter returns `ToolRuntimeError | None`
- Safe agent-facing messages
- Uncertain exception content defaults to safe templates
- Typed exception coverage added
- Tests added/updated and passing
- Any required package versioning updated for your repo rules
- No noisy stdout/stderr output in MCP tool runtime paths

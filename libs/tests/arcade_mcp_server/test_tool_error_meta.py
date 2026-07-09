"""Verify ``_meta.arcade.{errorKind, canRetry, ...}`` is emitted on tool
error responses, per the contract documented in
``examples/mcp_servers/typed_errors/README.md``.

Schema (camelCase on the wire):

- ``_meta.arcade.errorKind``: ErrorKind enum value as string (always)
- ``_meta.arcade.canRetry``: bool (always)
- ``_meta.arcade.additionalPromptContent``: str (when present on the error)
- ``_meta.arcade.retryAfterMs``: int (when present on the error)
- ``_meta.arcade.statusCode``: int (when present on the error)

Vendor-local ``_meta.arcade.*`` namespace matches the existing precedent for
tool-definition metadata in ``arcade_mcp_server/convert.py``.
"""

import pytest
from arcade_mcp_server.types import CallToolRequest, CallToolResult, JSONRPCResponse


def _result(response) -> CallToolResult:
    assert isinstance(response, JSONRPCResponse), f"got {type(response).__name__}"
    assert isinstance(response.result, CallToolResult)
    return response.result


def _arcade_meta(result: CallToolResult) -> dict:
    assert result.isError is True
    assert result.meta is not None, "expected _meta on error response"
    assert "arcade" in result.meta, f"expected _meta.arcade key, got {result.meta!r}"
    return result.meta["arcade"]


@pytest.mark.asyncio
async def test_retryable_error_emits_retry_meta(mcp_server):
    """RetryableToolError -> errorKind=TOOL_RUNTIME_RETRY, canRetry=true,
    additionalPromptContent present."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=1,
        method="tools/call",
        params={"name": "TestToolkit.retryable_failing_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert meta["errorKind"] == "TOOL_RUNTIME_RETRY"
    assert meta["canRetry"] is True
    assert "additionalPromptContent" in meta
    assert meta["additionalPromptContent"].startswith("Wait 60s")


@pytest.mark.asyncio
async def test_context_required_error_emits_context_meta(mcp_server):
    """ContextRequiredToolError -> errorKind=TOOL_RUNTIME_CONTEXT_REQUIRED,
    canRetry=false, additionalPromptContent present."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=2,
        method="tools/call",
        params={"name": "TestToolkit.context_required_failing_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert meta["errorKind"] == "TOOL_RUNTIME_CONTEXT_REQUIRED"
    assert meta["canRetry"] is False
    assert "additionalPromptContent" in meta


@pytest.mark.asyncio
async def test_upstream_rate_limit_error_emits_rate_limit_meta(mcp_server):
    """UpstreamRateLimitError -> errorKind=UPSTREAM_RUNTIME_RATE_LIMIT,
    canRetry=true, statusCode=429, retryAfterMs present."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=3,
        method="tools/call",
        params={"name": "TestToolkit.upstream_rate_limit_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert meta["errorKind"] == "UPSTREAM_RUNTIME_RATE_LIMIT"
    assert meta["canRetry"] is True
    assert meta["statusCode"] == 429
    assert meta["retryAfterMs"] == 2000


@pytest.mark.asyncio
async def test_upstream_auth_error_emits_auth_meta(mcp_server):
    """UpstreamError(status=403) -> errorKind=UPSTREAM_RUNTIME_AUTH_ERROR,
    canRetry=false, statusCode=403."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=4,
        method="tools/call",
        params={"name": "TestToolkit.upstream_auth_error_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert meta["errorKind"] == "UPSTREAM_RUNTIME_AUTH_ERROR"
    assert meta["canRetry"] is False
    assert meta["statusCode"] == 403


@pytest.mark.asyncio
async def test_unhandled_exception_emits_fatal_meta(mcp_server):
    """Bare RuntimeError wrapped by the adapter chain -> errorKind=TOOL_RUNTIME_FATAL,
    canRetry=false."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=5,
        method="tools/call",
        params={"name": "TestToolkit.failing_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert meta["errorKind"] == "TOOL_RUNTIME_FATAL"
    assert meta["canRetry"] is False


@pytest.mark.asyncio
async def test_optional_fields_omitted_when_absent(mcp_server):
    """When the error carries no additionalPromptContent / retryAfterMs, those
    keys must NOT appear in _meta.arcade (rather than being set to None)."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=6,
        method="tools/call",
        params={"name": "TestToolkit.failing_tool", "arguments": {}},
    )
    response = await mcp_server._handle_call_tool(message)
    meta = _arcade_meta(_result(response))
    assert "retryAfterMs" not in meta
    assert "additionalPromptContent" not in meta


@pytest.mark.asyncio
async def test_successful_call_has_no_arcade_error_meta(mcp_server):
    """Regression guard: success path must not grow an arcade error _meta entry."""
    message = CallToolRequest(
        jsonrpc="2.0",
        id=7,
        method="tools/call",
        params={"name": "TestToolkit.test_tool", "arguments": {"text": "Hi"}},
    )
    response = await mcp_server._handle_call_tool(message)
    result = _result(response)
    assert result.isError is False
    # The success path must not populate _meta.arcade.errorKind. Other
    # _meta.arcade keys (e.g. tool-definition metadata) are out of scope
    # here -- the contract is "no error-kind keys on success".
    if result.meta is not None and "arcade" in result.meta:
        assert "errorKind" not in result.meta["arcade"]

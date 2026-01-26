"""
MCP Server Tool Loaders.

Public API (async-only):
- `load_from_stdio_async`
- `load_mcp_remote_async`
- `load_arcade_mcp_gateway_async`
- `load_stdio_arcade_async`

Requires the MCP SDK: pip install mcp
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)


class MCPSessionFilter(logging.Filter):
    """Filter to suppress/rewrite misleading MCP SDK session termination messages.

    The MCP SDK logs "Session termination failed: 202" when sessions close gracefully.
    HTTP 202 (Accepted) is the correct response for MCP notifications per spec,
    not an error. This filter suppresses the misleading error message.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress log record, True to allow it."""
        message = record.getMessage()

        # Suppress the misleading "Session termination failed: 202" message
        # HTTP 202 is the correct response for MCP session close notifications
        is_termination_message = "Session termination failed" in message
        has_202_code = "202" in message

        return not (is_termination_message and has_202_code)


# Apply filter to MCP SDK loggers to suppress misleading session messages
def _configure_mcp_logging() -> None:
    """Configure MCP SDK logging to suppress misleading messages."""
    mcp_loggers = [
        "mcp",
        "mcp.client",
        "mcp.client.session",
        "mcp.client.sse",
        "mcp.client.stdio",
        "mcp.client.streamable_http",
    ]

    session_filter = MCPSessionFilter()
    for logger_name in mcp_loggers:
        mcp_logger = logging.getLogger(logger_name)
        mcp_logger.addFilter(session_filter)


# Configure MCP logging on module import
_configure_mcp_logging()

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Default Arcade API base URL (production)
ARCADE_API_BASE_URL = "https://api.arcade.dev"

# =============================================================================
# TOOL CACHE - Prevents redundant connections to the same MCP source
# Uses asyncio locks to prevent concurrent loads to the same MCP source
# =============================================================================

# Cache for loaded tools: key is (url, headers_hash), value is list of tools
_tools_cache: dict[str, list[dict[str, Any]]] = {}

# Per-key asyncio locks to prevent concurrent loads to same source
_cache_locks: dict[str, asyncio.Lock] = {}


def _make_cache_key(url: str, headers: dict[str, str] | None) -> str:
    """Create a cache key from URL and headers."""
    headers_str = str(sorted((headers or {}).items()))
    return f"{url}|{headers_str}"


# Lock acquisition timeout (seconds) - prevents indefinite hangs
LOCK_TIMEOUT_SECONDS = 60


async def _get_cache_lock(cache_key: str) -> asyncio.Lock:
    """Get or create an asyncio lock for the given cache key."""
    if cache_key not in _cache_locks:
        _cache_locks[cache_key] = asyncio.Lock()
    return _cache_locks[cache_key]


async def _acquire_lock_with_timeout(lock: asyncio.Lock, timeout: float | None = None) -> bool:
    """Acquire a lock with timeout. Returns True if acquired, False on timeout."""
    if timeout is None:
        timeout = LOCK_TIMEOUT_SECONDS
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        return False
    else:
        return True


def clear_tools_cache() -> None:
    """Clear the tools cache. Useful for testing or forcing fresh connections."""
    _tools_cache.clear()
    _cache_locks.clear()


def _get_arcade_base_url() -> str:
    """Get the Arcade API base URL, checking env var at runtime."""
    return os.environ.get("ARCADE_API_BASE_URL", ARCADE_API_BASE_URL)


# =============================================================================
# MCP SDK IMPORT
# =============================================================================


def _require_mcp() -> tuple[Any, Any, Any, Any, Any]:
    """
    Import MCP SDK with a helpful error message.

    Returns:
        (ClientSession, StdioServerParameters, stdio_client, sse_client, streamablehttp_client)
    """
    try:
        import mcp
        import mcp.client.sse as mcp_client_sse
        import mcp.client.stdio as mcp_client_stdio
        import mcp.client.streamable_http as mcp_client_http

        ClientSession = mcp.ClientSession
        StdioServerParameters = mcp.StdioServerParameters
        stdio_client = mcp_client_stdio.stdio_client
        sse_client = mcp_client_sse.sse_client
        streamablehttp_client = mcp_client_http.streamablehttp_client

    except ImportError as e:
        raise ImportError(
            "MCP SDK is required for arcade-evals. "
            "Install with: pip install 'arcade-mcp[evals]' or pip install mcp"
        ) from e

    return ClientSession, StdioServerParameters, stdio_client, sse_client, streamablehttp_client


# =============================================================================
# UTILITIES
# =============================================================================


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    """Convert an MCP Tool object to the MCP-style dict format used by EvalSuite."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "inputSchema": tool.inputSchema,
    }


def _ensure_mcp_path(url: str) -> str:
    """Ensure the URL path ends with '/mcp' (without duplicating).

    Preserves query strings and fragments.
    """
    parts = urlsplit(url)
    path = (parts.path or "").rstrip("/")

    # If any path segment is already "mcp" (e.g. "/mcp" or "/mcp/{slug}" or "/foo/mcp"),
    # treat it as already pointing at an MCP endpoint.
    segments = [seg for seg in path.split("/") if seg]
    if "mcp" in segments:
        normalized_path = "/" + "/".join(segments) if segments else ""
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            normalized_path,
            parts.query,
            parts.fragment,
        ))

    new_path = (f"{path}/mcp" if path else "/mcp") if path != "" else "/mcp"
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


def _build_arcade_mcp_url(gateway_slug: str | None, base_url: str) -> str:
    """Build the Arcade MCP gateway URL."""
    base = base_url.rstrip("/")
    if gateway_slug:
        return f"{base}/mcp/{gateway_slug}"
    return f"{base}/mcp"


# =============================================================================
# PUBLIC API (async-only)
# =============================================================================


async def load_from_stdio_async(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via stdio.

    Results are cached by command to avoid starting multiple subprocesses
    for the same server. Concurrent requests for the same command will wait
    for the first request to complete and share the result.

    Args:
        command: Command to run the MCP server (e.g., ["python", "server.py"]).
        env: Additional environment variables to pass to the server.
        timeout: Timeout in seconds (not used by MCP SDK, kept for API compatibility).

    Returns:
        List of tool definitions in MCP format.
    """
    if not command:
        return []

    del timeout  # MCP SDK manages timeouts internally

    cache_key = f"stdio|{' '.join(command)}|{sorted((env or {}).items())!s}"

    # Fast path: check cache without lock (no locking overhead for cache hits)
    if cache_key in _tools_cache:
        logger.debug(f"Using cached tools for stdio: {command[0]}")
        return _tools_cache[cache_key].copy()

    # Cache miss - acquire lock and check again (double-checked locking)
    lock = await _get_cache_lock(cache_key)
    if not await _acquire_lock_with_timeout(lock):
        raise TimeoutError(f"Timeout waiting for lock on stdio: {command[0]}")

    try:
        # Re-check cache (another request may have populated it while we waited)
        if cache_key in _tools_cache:
            logger.debug(f"Using cached tools for stdio: {command[0]}")
            return _tools_cache[cache_key].copy()

        ClientSession, StdioServerParameters, stdio_client, _, _ = _require_mcp()

        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:] if len(command) > 1 else [],
            env=process_env,
        )
        async with (
            stdio_client(server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.list_tools()
            tools = [_tool_to_dict(tool) for tool in result.tools]

        # Cache the result
        _tools_cache[cache_key] = tools.copy()
        return tools
    finally:
        lock.release()


async def load_mcp_remote_async(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
    use_sse: bool = False,
) -> list[dict[str, Any]]:
    """
    Load tools from a remote MCP server via URL (HTTP or SSE transport).

    Results are cached to avoid redundant connections when multiple models
    load the same MCP source. Concurrent requests for the same URL will wait
    for the first request to complete and share the result.

    Args:
        url: URL of the MCP server.
        headers: Additional headers to send with the request.
        timeout: Timeout in seconds (not used by MCP SDK, kept for API compatibility).
        use_sse: Whether to use SSE transport. If False, uses streamable-http.

    Returns:
        List of tool definitions in MCP format.
    """
    del timeout  # MCP SDK manages timeout internally

    url = _ensure_mcp_path(url)
    cache_key = _make_cache_key(url, headers)

    # Fast path: check cache without lock (no locking overhead for cache hits)
    if cache_key in _tools_cache:
        logger.debug(f"Using cached tools for {url}")
        return _tools_cache[cache_key].copy()

    # Cache miss - acquire lock and check again (double-checked locking)
    lock = await _get_cache_lock(cache_key)
    if not await _acquire_lock_with_timeout(lock):
        raise TimeoutError(f"Timeout waiting for lock on HTTP: {url}")

    try:
        # Re-check cache (another request may have populated it while we waited)
        if cache_key in _tools_cache:
            logger.debug(f"Using cached tools for {url}")
            return _tools_cache[cache_key].copy()

        # Load MCP SDK (deferred import)
        ClientSession, _, _, sse_client, streamablehttp_client = _require_mcp()

        # Load from MCP server
        tools: list[dict[str, Any]] = []

        if use_sse:
            async with (
                sse_client(url, headers=headers) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.list_tools()
                tools = [_tool_to_dict(tool) for tool in result.tools]
        else:
            async with (
                streamablehttp_client(url, headers=headers) as (read, write, _),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.list_tools()
                tools = [_tool_to_dict(tool) for tool in result.tools]

        # Cache the result
        _tools_cache[cache_key] = tools.copy()
        return tools
    finally:
        lock.release()


async def load_arcade_mcp_gateway_async(
    gateway_slug: str | None = None,
    *,
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    base_url: str | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from an Arcade MCP gateway.

    Args:
        gateway_slug: Optional gateway slug (if None, connects to base MCP endpoint).
        arcade_api_key: Arcade API key (defaults to ARCADE_API_KEY env var).
        arcade_user_id: Arcade user ID (defaults to ARCADE_USER_ID env var).
        base_url: Arcade API base URL (defaults to ARCADE_API_BASE_URL env var or production).
        timeout: Timeout in seconds (not used by MCP SDK, kept for API compatibility).

    Returns:
        List of tool definitions in MCP format (deduplicated by name).
    """
    api_key = arcade_api_key or os.environ.get("ARCADE_API_KEY")
    user_id = arcade_user_id or os.environ.get("ARCADE_USER_ID")

    headers: dict[str, str] = {}
    if api_key:
        # Arcade Gateway expects "Bearer <token>" format
        if api_key.startswith("Bearer "):
            headers["Authorization"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
    if user_id:
        # Note: Header is "Arcade-User-Id" (not "Arcade-User-ID")
        headers["Arcade-User-Id"] = user_id

    # Use provided base_url or check env var at runtime
    effective_base_url = base_url or _get_arcade_base_url()
    url = _build_arcade_mcp_url(gateway_slug, effective_base_url)
    tools = await load_mcp_remote_async(url, headers=headers, timeout=timeout)

    # Deduplicate tools by name (gateway may return duplicates)
    seen: dict[str, dict[str, Any]] = {}
    for tool in tools:
        name = tool.get("name")
        if name and name not in seen:
            seen[name] = tool
    return list(seen.values())


async def load_stdio_arcade_async(
    command: list[str],
    *,
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    tool_secrets: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from an Arcade MCP server via stdio.

    Convenience wrapper that sets Arcade env vars and delegates to `load_from_stdio_async`.

    Args:
        command: Command to run the MCP server (e.g., ["python", "server.py"]).
        arcade_api_key: Arcade API key (defaults to ARCADE_API_KEY env var).
        arcade_user_id: Arcade user ID (defaults to ARCADE_USER_ID env var).
        tool_secrets: Additional secrets to pass as environment variables.
        timeout: Timeout in seconds.

    Returns:
        List of tool definitions in MCP format.
    """
    env: dict[str, str] = {}

    if arcade_api_key:
        env["ARCADE_API_KEY"] = arcade_api_key
    elif "ARCADE_API_KEY" in os.environ:
        env["ARCADE_API_KEY"] = os.environ["ARCADE_API_KEY"]

    if arcade_user_id:
        env["ARCADE_USER_ID"] = arcade_user_id
    elif "ARCADE_USER_ID" in os.environ:
        env["ARCADE_USER_ID"] = os.environ["ARCADE_USER_ID"]

    if tool_secrets:
        env.update(tool_secrets)

    return await load_from_stdio_async(command, timeout=timeout, env=env if env else None)

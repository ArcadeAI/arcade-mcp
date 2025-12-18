"""
MCP Server Tool Loaders (pluggable backends).

Public API (async-only):
- `load_from_stdio_async`
- `load_from_http_async`
- `load_arcade_mcp_gateway_async`
- `load_stdio_arcade_async`

Backends:
- **official** (default): official `mcp` Python SDK
- **internal**: custom subprocess/httpx implementation (alternative)
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import queue
import subprocess
import threading
import uuid
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# MCP protocol version for handshakes
MCP_PROTOCOL_VERSION = "2024-11-05"

# Client info sent during MCP initialization
MCP_CLIENT_NAME = "arcade-evals"
MCP_CLIENT_VERSION = "1.0.0"

# Default Arcade API base URL (production)
ARCADE_API_BASE_URL = "https://api.arcade.dev"

# Backend type
LoaderBackendName = Literal["official", "internal"]


# =============================================================================
# UTILITIES
# =============================================================================


def _require_mcp() -> tuple[Any, Any, Any, Any]:
    """
    Lazy import MCP SDK with a helpful error message.

    Returns:
        (ClientSession, StdioServerParameters, stdio_client, sse_client)
    """
    try:
        mcp = importlib.import_module("mcp")
        mcp_client_stdio = importlib.import_module("mcp.client.stdio")
        mcp_client_sse = importlib.import_module("mcp.client.sse")

        ClientSession = mcp.ClientSession
        StdioServerParameters = mcp.StdioServerParameters
        stdio_client = mcp_client_stdio.stdio_client
        sse_client = mcp_client_sse.sse_client

    except ImportError as e:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install arcade-mcp[mcp] "
            "(or, if using arcade-evals standalone: pip install arcade-evals[mcp])."
        ) from e

    return ClientSession, StdioServerParameters, stdio_client, sse_client


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
# BASE CLASS
# =============================================================================


class MCPToolLoaderBase(ABC):
    """Base class for loading MCP tools (async-only)."""

    @abstractmethod
    async def load_from_stdio(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        """Load tools from an MCP server via stdio."""
        ...

    @abstractmethod
    async def load_from_http(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 10,
        use_sse: bool = False,
    ) -> list[dict[str, Any]]:
        """Load tools from an MCP server via HTTP/SSE."""
        ...

    @abstractmethod
    async def load_arcade_mcp_gateway(
        self,
        gateway_slug: str | None = None,
        *,
        arcade_api_key: str | None = None,
        arcade_user_id: str | None = None,
        base_url: str = ARCADE_API_BASE_URL,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        """Load tools from an Arcade MCP gateway."""
        ...


# =============================================================================
# OFFICIAL BACKEND (uses mcp SDK)
# =============================================================================


class OfficialMCPToolLoader(MCPToolLoaderBase):
    """Loader backend using the official MCP Python SDK."""

    async def load_from_stdio(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        if not command:
            return []

        ClientSession, StdioServerParameters, stdio_client, _ = _require_mcp()

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
            return [_tool_to_dict(tool) for tool in result.tools]

    async def load_from_http(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 10,
        use_sse: bool = False,
    ) -> list[dict[str, Any]]:
        # Note: The official MCP SDK manages timeouts internally, so the timeout
        # parameter is not used here. Consider using the internal backend
        # (set_mcp_loader_backend("internal")) if you need custom timeout control.
        del timeout, use_sse  # SDK manages these internally

        ClientSession, _, _, sse_client = _require_mcp()
        url = _ensure_mcp_path(url)

        async with (
            sse_client(url, headers=headers) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.list_tools()
            return [_tool_to_dict(tool) for tool in result.tools]

    async def load_arcade_mcp_gateway(
        self,
        gateway_slug: str | None = None,
        *,
        arcade_api_key: str | None = None,
        arcade_user_id: str | None = None,
        base_url: str = ARCADE_API_BASE_URL,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        api_key = arcade_api_key or os.environ.get("ARCADE_API_KEY")
        user_id = arcade_user_id or os.environ.get("ARCADE_USER_ID")

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = api_key
        if user_id:
            headers["arcade-user-id"] = user_id

        url = _build_arcade_mcp_url(gateway_slug, base_url)
        return await self.load_from_http(url, headers=headers, timeout=timeout)


# =============================================================================
# INTERNAL BACKEND (custom subprocess/httpx implementation)
# =============================================================================


def _readline_with_timeout(stream: Any, timeout: float) -> str | None:
    """Read a line from stream with timeout using threading.

    Args:
        stream: File-like object with readline() method.
        timeout: Maximum seconds to wait for a line.

    Returns:
        The line read, or None if timeout occurred.
    """
    result_queue: queue.Queue[str | None] = queue.Queue()

    def reader() -> None:
        try:
            line = stream.readline()
            result_queue.put(line)
        except Exception:
            result_queue.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    try:
        return result_queue.get(timeout=timeout)
    except queue.Empty:
        return None


def _internal_load_from_stdio_sync(
    command: list[str],
    *,
    timeout: int = 10,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Internal: subprocess JSON-RPC handshake over stdio.

    Note: Uses threading-based timeout for readline operations to prevent
    hanging indefinitely on non-responsive MCP servers.
    """
    if not command:
        return []

    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=process_env,
    )

    try:
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": MCP_CLIENT_NAME, "version": MCP_CLIENT_VERSION},
            },
        }

        if process.stdin and process.stdout:
            process.stdin.write(json.dumps(init_req) + "\n")
            process.stdin.flush()

            # Read init response with timeout
            init_response = _readline_with_timeout(process.stdout, timeout)
            if init_response is None:
                logger.warning(
                    "MCP stdio process for command %s timed out waiting for init response.",
                    " ".join(command),
                )
                return []

            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            )
            process.stdin.flush()

            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
            )
            process.stdin.flush()

            # Read tools/list response with timeout
            tools_response = _readline_with_timeout(process.stdout, timeout)
            if tools_response is None:
                logger.warning(
                    "MCP stdio process for command %s timed out waiting for tools/list response.",
                    " ".join(command),
                )
                return []

            try:
                response = json.loads(tools_response)
                if "result" in response and "tools" in response["result"]:
                    return cast(list[dict[str, Any]], response["result"]["tools"])
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse MCP server response as JSON: %s. "
                    "The server may have returned invalid output or closed unexpectedly.",
                    e,
                )
                return []

        # stdin/stdout not available
        logger.warning(
            "MCP stdio process for command %s did not provide stdin/stdout handles.",
            " ".join(command),
        )
        return []
    finally:
        with suppress(OSError, subprocess.TimeoutExpired):
            process.terminate()
            process.wait(timeout=timeout)


def _internal_load_from_http_sync(
    url: str,
    *,
    timeout: int = 10,
    headers: dict[str, str] | None = None,
    use_sse: bool = False,
) -> list[dict[str, Any]]:
    """Internal: HTTP JSON-RPC over POST, optional SSE streaming fallback."""
    try:
        import httpx
    except ImportError as e:
        raise ImportError(
            "Internal MCP HTTP loader requires httpx. Install with: pip install httpx"
        ) from e

    url = _ensure_mcp_path(url)
    request_headers = headers.copy() if headers else {}

    if use_sse:
        if "Accept" not in request_headers:
            request_headers["Accept"] = "text/event-stream"
        with httpx.stream(
            "POST",
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers=request_headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "result" in data and "tools" in data["result"]:
                            return cast(list[dict[str, Any]], data["result"]["tools"])
                    except json.JSONDecodeError:
                        continue
        # SSE stream completed without finding tools
        logger.warning(
            "MCP SSE stream from %s completed but no 'result.tools' found in events.",
            url,
        )
        return []

    if "Accept" not in request_headers:
        request_headers["Accept"] = "application/json, text/event-stream"

    try:
        response = httpx.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers=request_headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if "result" in data and "tools" in data["result"]:
            return cast(list[dict[str, Any]], data["result"]["tools"])
        # Response was valid JSON but missing expected fields
        logger.warning(
            "MCP server at %s returned unexpected response format: missing 'result.tools'. "
            "Response keys: %s",
            url,
            list(data.keys()),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 406 and "text/event-stream" in e.response.text:
            return _internal_load_from_http_sync(
                url, timeout=timeout, headers=headers, use_sse=True
            )
        # Some servers require session handshake first.
        if e.response.status_code in (400, 401, 403) and "Mcp-Session-Id" not in request_headers:
            return _internal_load_with_session_sync(
                url=url, headers=request_headers, timeout=timeout
            )
        logger.warning(
            "HTTP error loading tools from MCP server at %s: %s %s",
            url,
            e.response.status_code,
            e.response.reason_phrase,
        )
        raise
    except httpx.ConnectError as e:
        logger.warning(
            "Failed to connect to MCP server at %s: %s. "
            "Ensure the server is running and accessible.",
            url,
            e,
        )
    except httpx.TimeoutException:
        logger.warning(
            "Timeout loading tools from MCP server at %s after %ds. "
            "Try increasing the timeout parameter.",
            url,
            timeout,
        )

    return []


def _internal_load_with_session_sync(
    *,
    url: str,
    headers: dict[str, str],
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """Internal: initialize handshake to obtain/establish session id, then tools/list."""
    import httpx

    session_id = str(uuid.uuid4())
    req_headers = headers.copy()
    req_headers["Mcp-Session-Id"] = session_id

    init_response = httpx.post(
        url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": MCP_CLIENT_NAME, "version": MCP_CLIENT_VERSION},
            },
        },
        headers=req_headers,
        timeout=timeout,
    )
    init_response.raise_for_status()

    if "mcp-session-id" in init_response.headers:
        session_id = init_response.headers["mcp-session-id"]
    req_headers["Mcp-Session-Id"] = session_id

    return _internal_load_from_http_sync(url, timeout=timeout, headers=req_headers)


def _internal_load_arcade_mcp_gateway_sync(
    gateway_slug: str | None = None,
    *,
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    base_url: str = ARCADE_API_BASE_URL,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """Internal: Arcade MCP gateway load with session handshake."""
    api_key = arcade_api_key or os.environ.get("ARCADE_API_KEY")
    user_id = arcade_user_id or os.environ.get("ARCADE_USER_ID")

    headers: dict[str, str] = {"Accept": "application/json, text/event-stream"}
    if api_key:
        headers["Authorization"] = api_key
    if user_id:
        headers["arcade-user-id"] = user_id

    url = _build_arcade_mcp_url(gateway_slug, base_url)
    return _internal_load_with_session_sync(url=url, headers=headers, timeout=timeout)


class InternalMCPToolLoader(MCPToolLoaderBase):
    """Loader backend using custom subprocess/httpx implementation."""

    async def load_from_stdio(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            _internal_load_from_stdio_sync, command, timeout=timeout, env=env
        )

    async def load_from_http(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 10,
        use_sse: bool = False,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            _internal_load_from_http_sync,
            url,
            timeout=timeout,
            headers=headers,
            use_sse=use_sse,
        )

    async def load_arcade_mcp_gateway(
        self,
        gateway_slug: str | None = None,
        *,
        arcade_api_key: str | None = None,
        arcade_user_id: str | None = None,
        base_url: str = ARCADE_API_BASE_URL,
        timeout: int = 10,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            _internal_load_arcade_mcp_gateway_sync,
            gateway_slug,
            arcade_api_key=arcade_api_key,
            arcade_user_id=arcade_user_id,
            base_url=base_url,
            timeout=timeout,
        )


# =============================================================================
# BACKEND MANAGEMENT
# =============================================================================

_ACTIVE_LOADER_BACKEND: LoaderBackendName = "official"
_MCP_TOOL_LOADER: MCPToolLoaderBase = OfficialMCPToolLoader()


def set_mcp_loader_backend(name: LoaderBackendName) -> None:
    """Select which MCP loader backend is wired."""
    global _ACTIVE_LOADER_BACKEND, _MCP_TOOL_LOADER
    if name == "official":
        _ACTIVE_LOADER_BACKEND = name
        _MCP_TOOL_LOADER = OfficialMCPToolLoader()
    elif name == "internal":
        _ACTIVE_LOADER_BACKEND = name
        _MCP_TOOL_LOADER = InternalMCPToolLoader()
    else:
        raise ValueError(f"Unknown MCP loader backend: {name}")


def get_mcp_loader_backend() -> LoaderBackendName:
    """Return the active loader backend name."""
    return _ACTIVE_LOADER_BACKEND


def set_mcp_tool_loader(loader: MCPToolLoaderBase, *, name: str = "custom") -> None:
    """Inject a custom loader implementation (for experiments/testing)."""
    global _ACTIVE_LOADER_BACKEND, _MCP_TOOL_LOADER
    _ACTIVE_LOADER_BACKEND = name  # type: ignore[assignment]
    _MCP_TOOL_LOADER = loader


# =============================================================================
# PUBLIC API (async-only, delegates to wired backend)
# =============================================================================


async def load_from_stdio_async(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via stdio.

    Args:
        command: Command to run the MCP server (e.g., ["python", "server.py"]).
        env: Additional environment variables to pass to the server.
        timeout: Timeout in seconds.

    Returns:
        List of tool definitions in MCP format.
    """
    return await _MCP_TOOL_LOADER.load_from_stdio(command, env=env, timeout=timeout)


async def load_from_http_async(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
    use_sse: bool = False,
) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via HTTP/SSE.

    Args:
        url: URL of the MCP server.
        headers: Additional headers to send with the request.
        timeout: Timeout in seconds.
        use_sse: Whether to use SSE transport (internal backend only).

    Returns:
        List of tool definitions in MCP format.
    """
    return await _MCP_TOOL_LOADER.load_from_http(
        url, headers=headers, timeout=timeout, use_sse=use_sse
    )


async def load_arcade_mcp_gateway_async(
    gateway_slug: str | None = None,
    *,
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    base_url: str = ARCADE_API_BASE_URL,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from an Arcade MCP gateway.

    Args:
        gateway_slug: Optional gateway slug (if None, connects to base MCP endpoint).
        arcade_api_key: Arcade API key (defaults to ARCADE_API_KEY env var).
        arcade_user_id: Arcade user ID (defaults to ARCADE_USER_ID env var).
        base_url: Arcade API base URL (defaults to production).
        timeout: Timeout in seconds.

    Returns:
        List of tool definitions in MCP format.
    """
    return await _MCP_TOOL_LOADER.load_arcade_mcp_gateway(
        gateway_slug,
        arcade_api_key=arcade_api_key,
        arcade_user_id=arcade_user_id,
        base_url=base_url,
        timeout=timeout,
    )


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

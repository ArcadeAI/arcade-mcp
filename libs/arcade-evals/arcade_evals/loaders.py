"""
MCP Server Tool Loaders.

Load tools from MCP servers via stdio or HTTP transport.

Functions:
    - load_from_stdio: Generic stdio loader
    - load_stdio_arcade: Arcade MCP server via stdio
    - load_from_http: Generic HTTP loader with headers
    - load_arcade_cloud: Arcade Cloud MCP gateway via HTTP
"""

import json
import os
import subprocess
from typing import Any

# Protocol version for MCP handshake
_MCP_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "arcade-evals", "version": "1.7.0"}


# =============================================================================
# STDIO LOADERS
# =============================================================================


def load_from_stdio(
    command: list[str],
    timeout: int = 10,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via stdio transport.

    Args:
        command: Command to start server (e.g., ["python", "server.py", "stdio"])
        timeout: Timeout in seconds.
        env: Environment variables for the server. Merged with current env.

    Returns:
        List of tool descriptors. Empty list on error.

    Example:
        >>> tools = load_from_stdio(
        ...     ["python", "my_server.py", "stdio"],
        ...     env={"API_KEY": "..."}
        ... )
    """
    if not command:
        return []

    # Merge with current environment
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=process_env,
        )
    except (FileNotFoundError, OSError, ValueError):
        return []

    try:
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": _MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": _CLIENT_INFO,
            },
        }

        if process.stdin and process.stdout:
            process.stdin.write(json.dumps(init_req) + "\n")
            process.stdin.flush()
            process.stdout.readline()  # Read init response

            # Send initialized notification
            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            )
            process.stdin.flush()

            # Request tools
            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n"
            )
            process.stdin.flush()

            response = json.loads(process.stdout.readline())
            if "result" in response and "tools" in response["result"]:
                tools_list: list[dict[str, Any]] = response["result"]["tools"]
                return tools_list
    finally:
        try:
            process.terminate()
            process.wait(timeout=timeout)
        except Exception:
            pass

    return []


def load_stdio_arcade(
    command: list[str],
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    tool_secrets: dict[str, str] | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from Arcade MCP server via stdio.

    Args:
        command: Command to start server (e.g., ["python", "server.py", "stdio"])
        arcade_api_key: API key (or set ARCADE_API_KEY env var).
        arcade_user_id: User ID (or set ARCADE_USER_ID env var).
        tool_secrets: Additional secrets (e.g., {"GITHUB_TOKEN": "..."}).
        timeout: Timeout in seconds.

    Returns:
        List of tool descriptors. Empty list on error.

    Example:
        >>> tools = load_stdio_arcade(
        ...     ["python", "server.py", "stdio"],
        ...     arcade_api_key="arc_...",
        ...     arcade_user_id="user@example.com"
        ... )
    """
    env: dict[str, str] = {}

    # Arcade credentials
    if arcade_api_key:
        env["ARCADE_API_KEY"] = arcade_api_key
    elif "ARCADE_API_KEY" in os.environ:
        env["ARCADE_API_KEY"] = os.environ["ARCADE_API_KEY"]

    if arcade_user_id:
        env["ARCADE_USER_ID"] = arcade_user_id
    elif "ARCADE_USER_ID" in os.environ:
        env["ARCADE_USER_ID"] = os.environ["ARCADE_USER_ID"]

    # Tool secrets
    if tool_secrets:
        env.update(tool_secrets)

    return load_from_stdio(command, timeout=timeout, env=env if env else None)


# =============================================================================
# HTTP LOADERS
# =============================================================================


def load_from_http(
    url: str,
    timeout: int = 10,
    headers: dict[str, str] | None = None,
    use_sse: bool = False,
) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via HTTP.

    Args:
        url: Server URL. /mcp is appended if needed.
        timeout: Request timeout in seconds.
        headers: HTTP headers for auth and metadata.
        use_sse: Use Server-Sent Events (experimental).

    Returns:
        List of tool descriptors. Empty list on error.

    Example:
        >>> tools = load_from_http(
        ...     "http://localhost:8000",
        ...     headers={"Authorization": "Bearer token"}
        ... )
    """
    try:
        import httpx
    except ImportError as e:
        raise ImportError("httpx required. Install: pip install httpx") from e

    # Append /mcp if not present
    if "/mcp" not in url:
        url = f"{url}mcp" if url.endswith("/") else f"{url}/mcp"

    request_headers = headers.copy() if headers else {}

    if use_sse:
        # SSE streaming mode
        if "Accept" not in request_headers:
            request_headers["Accept"] = "text/event-stream"

        try:
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
                                tools: list[dict[str, Any]] = data["result"]["tools"]
                                return tools
                        except json.JSONDecodeError:
                            continue
                return []
        except Exception:
            return []
    else:
        # Regular HTTP mode
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
                result_tools: list[dict[str, Any]] = data["result"]["tools"]
                return result_tools
        except httpx.HTTPStatusError as e:
            # Fallback to SSE if server requires it
            if e.response.status_code == 406 and "text/event-stream" in e.response.text:
                return load_from_http(url=url, timeout=timeout, headers=headers, use_sse=True)
        except Exception:
            pass

    return []


def load_arcade_cloud(
    gateway_slug: str,
    arcade_api_key: str | None = None,
    arcade_user_id: str | None = None,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    Load tools from Arcade Cloud MCP gateway via HTTP.

    Connects to https://api.arcade.dev/mcp/<gateway_slug>

    Args:
        gateway_slug: Your gateway slug (e.g., "my-gateway").
        arcade_api_key: API key (or set ARCADE_API_KEY env var).
        arcade_user_id: User ID (or set ARCADE_USER_ID env var).
        timeout: Request timeout in seconds.

    Returns:
        List of tool descriptors. Empty list on error.

    Example:
        >>> tools = load_arcade_cloud(
        ...     gateway_slug="my-gateway",
        ...     arcade_api_key="arc_...",
        ...     arcade_user_id="user@example.com"
        ... )
    """
    api_key = arcade_api_key or os.environ.get("ARCADE_API_KEY")
    user_id = arcade_user_id or os.environ.get("ARCADE_USER_ID")

    headers: dict[str, str] = {"Accept": "application/json, text/event-stream"}
    if api_key:
        headers["Authorization"] = api_key
    if user_id:
        headers["arcade-user-id"] = user_id

    url = f"https://api.arcade.dev/mcp/{gateway_slug}"
    return _load_with_session(url=url, headers=headers, timeout=timeout)


def _load_with_session(
    url: str,
    headers: dict[str, str],
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """Internal: Load tools with MCP session handshake."""
    try:
        import uuid

        import httpx

        session_id = str(uuid.uuid4())
        req_headers = headers.copy()
        req_headers["Mcp-Session-Id"] = session_id

        # Initialize
        init_response = httpx.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": _MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": _CLIENT_INFO,
                },
            },
            headers=req_headers,
            timeout=timeout,
        )
        init_response.raise_for_status()

        # Use session from response
        if "mcp-session-id" in init_response.headers:
            session_id = init_response.headers["mcp-session-id"]
        req_headers["Mcp-Session-Id"] = session_id

        return load_from_http(url=url, headers=req_headers, timeout=timeout)

    except Exception:
        return []


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# Old names -> new names
load_from_arcade_server = load_stdio_arcade
load_from_arcade_http = load_arcade_cloud

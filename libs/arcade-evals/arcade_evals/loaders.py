"""Automatic tool loading from MCP servers.

Simple implementations for loading tool descriptors from MCP servers.
Inspired by the MCP protocol but implemented as lightweight clients.
"""

import json
import subprocess
from typing import Any


def load_from_stdio(command: list[str], timeout: int = 10) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via stdio transport.

    Implements a simple MCP client that:
    1. Starts the server process
    2. Sends initialize request
    3. Sends initialized notification
    4. Sends tools/list request
    5. Returns the tool descriptors

    Args:
        command: Command to start server (e.g., ["npx", "-y", "@modelcontextprotocol/server-github"])
        timeout: Timeout in seconds.

    Returns:
        List of tool descriptors from the server. Returns empty list on error.
    """
    if not command:
        return []

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, OSError, ValueError):
        return []

    try:
        # Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "arcade-evals", "version": "1.7.0"},
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

            # Read tools response
            response = json.loads(process.stdout.readline())

            if "result" in response and "tools" in response["result"]:
                tools_list: list[dict[str, Any]] = response["result"]["tools"]
                return tools_list
    finally:
        try:
            process.terminate()
            process.wait(timeout=timeout)
        except Exception as e:
            # Ignore termination errors
            del e

    return []


def load_from_http(url: str, timeout: int = 10) -> list[dict[str, Any]]:
    """
    Load tools from an MCP server via HTTP.

    Args:
        url: Base URL of server (e.g., "http://localhost:8000")
        timeout: Request timeout in seconds.

    Returns:
        List of tool descriptors.
    """
    try:
        import httpx
    except ImportError as e:
        raise ImportError(
            "httpx is required for HTTP loading. Install with: pip install httpx"
        ) from e

    try:
        response = httpx.post(
            f"{url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            timeout=timeout,
        )
        response.raise_for_status()

        data = response.json()
        if "result" in data and "tools" in data["result"]:
            tools_list: list[dict[str, Any]] = data["result"]["tools"]
            return tools_list
    except Exception as e:
        del e
        return []

    return []

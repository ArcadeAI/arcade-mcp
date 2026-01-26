"""End-to-end integration tests for arcade_mcp_server.

Tests the full MCP protocol flow for both stdio and HTTP transports,
including initialize, ping, list tools, and tool execution with all key features.
"""

import asyncio
import json
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

# Helper Functions


def get_entrypoint_path() -> str:
    """Get the path to the test server entrypoint."""
    return str(Path(__file__).parent / "server" / "src" / "server" / "entrypoint.py")


def start_mcp_server(
    transport: str, port: int | None = None
) -> tuple[subprocess.Popen, int | None]:
    """
    Start the MCP server as a subprocess.

    Args:
        transport: Transport type ("stdio" or "http")
        port: Port for HTTP transport (optional, will be random if not provided)

    Returns:
        Tuple of (process, port). Port is None for stdio transport.
    """
    entrypoint_path = get_entrypoint_path()
    # Get the server package directory (where pyproject.toml is)
    package_path = Path(__file__).parent / "server"

    if transport == "stdio":
        cmd = ["uv", "run", entrypoint_path, "stdio"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            cwd=str(package_path),
        )
        return process, None

    elif transport == "http":
        if port is None:
            port = random.randint(8000, 9000)  # noqa: S311

        env = {
            **os.environ,
            "ARCADE_SERVER_HOST": "127.0.0.1",
            "ARCADE_SERVER_PORT": str(port),
            "ARCADE_SERVER_TRANSPORT": "http",
            "ARCADE_AUTH_DISABLED": "true",
            "ARCADE_WORKER_SECRET": "test-secret-e2e",
        }

        cmd = ["uv", "run", entrypoint_path, "http"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(package_path),
        )
        return process, port

    else:
        raise ValueError(f"Invalid transport: {transport}")


def start_mcp_server_direct_python(
    transport: str, port: int | None = None
) -> tuple[subprocess.Popen, int | None]:
    """
    Start MCP server with direct Python invocation (simulates what happens in the Engine during deployment).

    Args:
        transport: Transport type ("stdio" or "http")
        port: Port for HTTP transport (optional, will be random if not provided)

    Returns:
        Tuple of (process, port). Port is None for stdio transport.
    """
    entrypoint_path = get_entrypoint_path()
    package_path = Path(__file__).parent / "server"

    # Find Python in the server's venv
    venv_python = package_path / ".venv" / "bin" / "python"
    if not venv_python.exists():
        pytest.skip("Server venv not found - run 'uv sync' in integration/server first")

    if port is None:
        port = random.randint(8000, 9000)  # noqa: S311

    env = {
        **os.environ,
        "ARCADE_SERVER_HOST": "127.0.0.1",
        "ARCADE_SERVER_PORT": str(port),
        "ARCADE_SERVER_TRANSPORT": transport,
        "ARCADE_AUTH_DISABLED": "true",
        "ARCADE_WORKER_SECRET": "test-secret-direct",
    }

    cmd = [str(venv_python), entrypoint_path, transport]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(package_path),
    )
    return process, port if transport == "http" else None


def wait_for_http_server_ready(port: int, timeout: int = 30) -> None:
    """
    Wait for HTTP server to become healthy.

    Args:
        port: Server port
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If server doesn't become healthy within timeout
    """
    health_url = f"http://127.0.0.1:{port}/worker/health"
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200:
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(0.5)

    raise TimeoutError(f"Server failed to become healthy within {timeout} seconds")


def build_jsonrpc_request(
    method: str, params: dict | None = None, request_id: int | None = None
) -> dict:
    """
    Build a JSON-RPC 2.0 request.

    Args:
        method: Method name
        params: Method parameters
        request_id: Request ID (omit for notifications)

    Returns:
        JSON-RPC request dict
    """
    request: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }

    if params is not None:
        request["params"] = params

    if request_id is not None:
        request["id"] = request_id

    return request


def parse_jsonrpc_message(line: str) -> dict | None:
    """
    Parse a JSON-RPC message from a line of text.

    Args:
        line: Line of text containing JSON

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not line or not line.strip():
        return None

    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def mock_sampling_response(request_id: str | int) -> dict:
    """
    Create a mock response for sampling/createMessage request.

    Args:
        request_id: Request ID from the server's request

    Returns:
        JSON-RPC response with mock sampling result
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "model": "mock-model",
            "role": "assistant",
            "content": {
                "type": "text",
                "text": "This is a mock summary of the text.",
            },
            "stopReason": "endTurn",
        },
    }


def mock_elicitation_response(request_id: str | int) -> dict:
    """
    Create a mock response for user elicitation request.

    Args:
        request_id: Request ID from the server's request

    Returns:
        JSON-RPC response with mock elicitation acceptance
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "action": "accept",
            "content": {"nickname": "TestUser"},
        },
    }


class StdioClient:
    """Helper class to communicate with stdio MCP server."""

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self._next_id = 1

    def send_request(self, method: str, params: dict | None = None) -> int:
        """Send a request and return the request ID."""
        request_id = self._next_id
        self._next_id += 1

        request = build_jsonrpc_request(method, params, request_id)
        message = json.dumps(request) + "\n"

        if self.process.stdin:
            self.process.stdin.write(message)
            self.process.stdin.flush()

        return request_id

    def send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a notification (no response expected)."""
        notification = build_jsonrpc_request(method, params, request_id=None)
        message = json.dumps(notification) + "\n"

        if self.process.stdin:
            self.process.stdin.write(message)
            self.process.stdin.flush()

    def send_response(self, request_id: str | int, result: dict) -> None:
        """Send a response to a server-initiated request."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }
        message = json.dumps(response) + "\n"

        if self.process.stdin:
            self.process.stdin.write(message)
            self.process.stdin.flush()

    def read_response(self, timeout: float = 10.0) -> dict:
        """Read a response from the server."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.process.stdout:
                line = self.process.stdout.readline()
                if line:
                    message = parse_jsonrpc_message(line)
                    if message:
                        return message
            time.sleep(0.01)

        raise TimeoutError("Timeout waiting for response")

    def handle_bidirectional_request(self, message: dict) -> None:
        """Handle a server-initiated request by sending appropriate mock response."""
        if "method" not in message or "id" not in message:
            return

        method = message["method"]
        request_id = message["id"]

        if method == "sampling/createMessage":
            response = mock_sampling_response(request_id)
            self.send_response(request_id, response["result"])
        elif method == "elicitation/create":
            response = mock_elicitation_response(request_id)
            self.send_response(request_id, response["result"])


# Tests


@pytest.mark.asyncio
async def test_stdio_e2e():
    """End-to-end test for stdio transport."""
    process, _ = start_mcp_server("stdio")
    client = StdioClient(process)

    try:
        # Give server a moment to start
        await asyncio.sleep(0.5)

        # 1. Send initialize request
        init_id = client.send_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}, "elicitation": {}},
                "clientInfo": {"name": "test-client", "title": "Test Client", "version": "1.0.0"},
            },
        )

        init_response = client.read_response()
        assert init_response["jsonrpc"] == "2.0"
        assert init_response["id"] == init_id
        assert "result" in init_response
        assert "error" not in init_response
        assert init_response["result"]["serverInfo"]["name"] == "server"
        assert init_response["result"]["serverInfo"]["version"] == "1.0.0"

        # 2. Send initialized notification
        client.send_notification("notifications/initialized")

        # 3. Send ping request
        ping_id = client.send_request("ping")
        ping_response = client.read_response()
        assert ping_response["jsonrpc"] == "2.0"
        assert ping_response["id"] == ping_id
        assert "error" not in ping_response

        # 4. List tools
        list_tools_id = client.send_request("tools/list")
        list_tools_response = client.read_response()
        assert list_tools_response["jsonrpc"] == "2.0"
        assert list_tools_response["id"] == list_tools_id
        assert "result" in list_tools_response
        assert "tools" in list_tools_response["result"]
        tools = list_tools_response["result"]["tools"]
        assert len(tools) == 9

        # 5. Call logging_tool
        logging_id = client.send_request(
            "tools/call",
            {
                "name": "Server_LoggingTool",
                "arguments": {"message": "test message"},
            },
        )

        # Read response (may have logs interspersed)
        logging_tool_response = None
        expected_log_levels = ["debug", "debug", "info", "warning", "error"]
        actual_log_levels = []
        for _ in range(20):  # Allow for extra logs from before/after tool execution, just in case
            msg = client.read_response(timeout=2.0)
            if msg.get("method") == "notifications/message":
                actual_log_levels.append(msg.get("params").get("level"))
            if msg.get("id") == logging_id:  # call tool response (no more tool logs after this)
                logging_tool_response = msg
                break

        assert logging_tool_response is not None
        assert logging_tool_response["jsonrpc"] == "2.0"
        assert actual_log_levels == expected_log_levels
        assert "result" in logging_tool_response

        # 6. Call reporting_progress
        progress_id = client.send_request(
            "tools/call",
            {
                "name": "Server_ReportingProgress",
                "arguments": {},
                "_meta": {
                    "progressToken": "test-progress-token",
                },
            },
        )

        # Read response (may have progress notifications interspersed)
        progress_response = None
        actual_progress_messages = []
        expected_progress_messages = [
            "Step 1 of 5",
            "Step 2 of 5",
            "Step 3 of 5",
            "Step 4 of 5",
            "Step 5 of 5",
        ]
        for _ in range(20):  # Allow for multiple progress messages
            msg = client.read_response(timeout=2.0)
            if msg.get("method") == "notifications/progress":
                actual_progress_messages.append(msg.get("params").get("message"))
            if msg.get("id") == progress_id:
                progress_response = msg
                break

        assert progress_response is not None
        assert progress_response["jsonrpc"] == "2.0"
        assert "error" not in progress_response
        assert "result" in progress_response

        assert actual_progress_messages == expected_progress_messages

        # 7. Call call_other_tool (tests tool chaining)
        chaining_id = client.send_request(
            "tools/call",
            {
                "name": "Server_CallOtherTool",
                "arguments": {},
            },
        )

        chaining_response = client.read_response(timeout=5.0)
        assert chaining_response["jsonrpc"] == "2.0"
        assert chaining_response["id"] == chaining_id
        assert "SUCCESS" in chaining_response["result"]["content"][0]["text"]

        # 8. Call sampling (tests client model sampling with mock response)
        sampling_id = client.send_request(
            "tools/call",
            {
                "name": "Server_Sampling",
                "arguments": {"text": "This is some text to summarize."},
            },
        )

        # Server will send a sampling/createMessage request back to the client
        sampling_request = None
        actual_sampling_message = None
        expected_sampling_message = "This is some text to summarize."
        tool_response = None
        for _ in range(10):  # Allow for messages from before/after tool execution, just in case
            msg = client.read_response(timeout=5.0)
            if msg.get("method") == "sampling/createMessage":
                actual_sampling_message = (
                    msg.get("params", {})
                    .get("messages", [{}])[0]
                    .get("content", {})
                    .get("text", "")
                )
                # Sampling request was received by the client, we now send a response back to the server
                sampling_request = msg
                client.handle_bidirectional_request(msg)

            elif msg.get("id") == sampling_id:
                # Tool finished executing and returned a response back to the client
                tool_response = msg
                break

        assert sampling_request is not None, "Should have received sampling/createMessage request"
        assert actual_sampling_message == expected_sampling_message
        assert tool_response is not None, "Should have received tool call response"
        assert tool_response["jsonrpc"] == "2.0"
        assert tool_response["id"] == sampling_id
        assert "error" not in tool_response
        assert "result" in tool_response

        # 9. Call elicit_nickname (tests user elicitation with mock response)
        elicit_id = client.send_request(
            "tools/call",
            {
                "name": "Server_ElicitNickname",
                "arguments": {},
            },
        )

        # Server will send an elicitation request back the client
        elicit_request = None
        actual_elicitation_message = None
        expected_elicitation_message = "What is your nickname?"
        tool_response = None
        for _ in range(10):
            msg = client.read_response(timeout=5.0)
            if "method" in msg and msg["method"] == "elicitation/create":
                actual_elicitation_message = msg.get("params", {}).get("message", "")
                # Elicitation request was received by the client, we now send a response back to the server
                elicit_request = msg
                client.handle_bidirectional_request(msg)
            elif msg.get("id") == elicit_id:
                # Tool finished executing and returned a response back to the client
                tool_response = msg
                break

        assert elicit_request is not None, "Should have received elicitation request"
        assert actual_elicitation_message == expected_elicitation_message
        assert tool_response is not None, "Should have received tool call response"
        assert tool_response["jsonrpc"] == "2.0"
        assert tool_response["id"] == elicit_id
        assert "error" not in tool_response
        assert "result" in tool_response

        # Verify process is still running
        assert process.poll() is None

    finally:
        # Clean shutdown
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_http_e2e():
    """End-to-end test for HTTP transport."""
    process, port = start_mcp_server("http")
    assert port is not None

    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_http_server_ready(port, timeout=10)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        client = httpx.Client(base_url=base_url, timeout=30.0, headers=headers)

        # 1. Send initialize request
        init_request = build_jsonrpc_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}, "elicitation": {}},
                "clientInfo": {"name": "test-client", "title": "Test Client", "version": "1.0.0"},
            },
            request_id=1,
        )

        init_response = client.post("/mcp", json=init_request)
        assert init_response.status_code == 200
        init_data = init_response.json()
        assert init_data["jsonrpc"] == "2.0"
        assert init_data["id"] == 1
        assert "result" in init_data
        assert "error" not in init_data
        assert init_data["result"]["serverInfo"]["name"] == "server"
        assert init_data["result"]["serverInfo"]["version"] == "1.0.0"

        session_id = init_response.headers.get("mcp-session-id")
        assert session_id is not None, "Session ID not found in initialize response headers"

        # All subsequent requests from the client must include the session ID
        client.headers.update({"Mcp-Session-Id": session_id})

        # 2. Send initialized notification
        init_notif = build_jsonrpc_request(
            "notifications/initialized", params=None, request_id=None
        )
        notif_response = client.post("/mcp", json=init_notif)
        assert notif_response.status_code == 202

        # 3. Send ping request
        ping_request = build_jsonrpc_request("ping", request_id=2)
        ping_response = client.post("/mcp", json=ping_request)
        assert ping_response.status_code == 200
        ping_data = ping_response.json()
        assert ping_data["jsonrpc"] == "2.0"
        assert ping_data["id"] == 2
        assert "error" not in ping_data

        # 4. List tools
        list_tools_request = build_jsonrpc_request("tools/list", request_id=3)
        list_tools_response = client.post("/mcp", json=list_tools_request)
        assert list_tools_response.status_code == 200
        list_tools_data = list_tools_response.json()
        assert list_tools_data["jsonrpc"] == "2.0"
        assert list_tools_data["id"] == 3
        assert "result" in list_tools_data
        assert "tools" in list_tools_data["result"]
        tools = list_tools_data["result"]["tools"]
        assert len(tools) == 9

        # 5. Call logging_tool
        logging_request = build_jsonrpc_request(
            "tools/call",
            {
                "name": "Server_LoggingTool",
                "arguments": {"message": "test message"},
            },
            request_id=4,
        )

        logging_response = client.post("/mcp", json=logging_request)

        assert logging_response.status_code == 200
        logging_data = logging_response.json()
        assert logging_data["jsonrpc"] == "2.0"
        assert logging_data["id"] == 4
        assert "error" not in logging_data
        assert "result" in logging_data

        # 6. Call reporting_progress
        progress_request = build_jsonrpc_request(
            "tools/call",
            {
                "name": "Server_ReportingProgress",
                "arguments": {},
            },
            request_id=5,
        )

        progress_response = client.post("/mcp", json=progress_request)
        assert progress_response.status_code == 200
        progress_data = progress_response.json()
        assert progress_data["jsonrpc"] == "2.0"
        assert progress_data["id"] == 5
        assert "error" not in progress_data
        assert "result" in progress_data

        # 7. Call call_other_tool (tests tool chaining)
        chaining_request = build_jsonrpc_request(
            "tools/call",
            {
                "name": "Server_CallOtherTool",
                "arguments": {},
            },
            request_id=6,
        )

        chaining_response = client.post("/mcp", json=chaining_request)
        assert chaining_response.status_code == 200
        chaining_data = chaining_response.json()
        assert chaining_data["jsonrpc"] == "2.0"
        assert chaining_data["id"] == 6
        assert "error" not in chaining_data
        assert "SUCCESS" in chaining_data["result"]["content"][0]["text"]

        # TODO: Implement an HTTP client that can handle bidirectional communication (sampling/elicitation)

        assert process.poll() is None

        client.close()

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_http_mcp_concurrent_tool_execution():
    """Test that multiple tools can execute concurrently via the /mcp route."""
    process, port = start_mcp_server("http")
    assert port is not None

    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_http_server_ready(port, timeout=10)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(base_url=base_url, timeout=30.0, headers=headers) as client:
            # Initialize the connection with the server
            init_request = build_jsonrpc_request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
                request_id=1,
            )

            init_response = await client.post("/mcp", json=init_request)
            assert init_response.status_code == 200
            session_id = init_response.headers.get("mcp-session-id")
            assert session_id is not None

            client.headers.update({"Mcp-Session-Id": session_id})

            init_notif = build_jsonrpc_request(
                "notifications/initialized", params=None, request_id=None
            )
            await client.post("/mcp", json=init_notif)

            # Call the tool three times concurrently. Each tool call takes 1 second to execute.
            # Since the server should be able to execute the tools in parallel, the total time should be around 1 second
            delay_seconds = 1.0

            tool_requests = [
                build_jsonrpc_request(
                    "tools/call",
                    {
                        "name": "Server_SlowAsyncTool",
                        "arguments": {"delay_seconds": delay_seconds},
                    },
                    request_id=10,
                ),
                build_jsonrpc_request(
                    "tools/call",
                    {
                        "name": "Server_SlowSyncTool",
                        "arguments": {"delay_seconds": delay_seconds},
                    },
                    request_id=11,
                ),
                build_jsonrpc_request(
                    "tools/call",
                    {
                        "name": "Server_SlowSyncTool",
                        "arguments": {"delay_seconds": delay_seconds},
                    },
                    request_id=12,
                ),
            ]

            start_time = time.time()
            responses = await asyncio.gather(*[
                client.post("/mcp", json=req) for req in tool_requests
            ])
            total_time = time.time() - start_time

            assert all(r.status_code == 200 for r in responses), "All requests should succeed"

            for idx, response in enumerate(responses):
                data = response.json()
                assert data["jsonrpc"] == "2.0"
                assert data["id"] == idx + 10
                assert "result" in data
                assert "error" not in data
                assert f"after {delay_seconds}s" in data["result"]["content"][0]["text"]

            # If parallel, should take ~1s, not ~3s
            max_expected_time = delay_seconds + 0.5  # Allow 0.5s overhead
            assert total_time < max_expected_time

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_http_worker_concurrent_tool_execution():
    """Test that multiple tools can execute concurrently via the /worker/tools/invoke route."""
    process, port = start_mcp_server("http")
    assert port is not None

    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_http_server_ready(port, timeout=10)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(base_url=base_url, timeout=30.0, headers=headers) as client:
            # Call the tool three times concurrently. Each tool call takes 1 second to execute.
            # Since the server should be able to execute the tools in parallel, the total time should be around 1 second
            delay_seconds = 1.0

            tool_requests = [
                {
                    "execution_id": "worker_exec_0",
                    "tool": {
                        "toolkit": "Server",
                        "name": "SlowAsyncTool",
                    },
                    "inputs": {"delay_seconds": delay_seconds},
                },
                {
                    "execution_id": "worker_exec_1",
                    "tool": {
                        "toolkit": "Server",
                        "name": "SlowSyncTool",
                    },
                    "inputs": {"delay_seconds": delay_seconds},
                },
                {
                    "execution_id": "worker_exec_2",
                    "tool": {
                        "toolkit": "Server",
                        "name": "SlowSyncTool",
                    },
                    "inputs": {"delay_seconds": delay_seconds},
                },
            ]

            start_time = time.time()
            responses = await asyncio.gather(*[
                client.post("/worker/tools/invoke", json=req) for req in tool_requests
            ])
            total_time = time.time() - start_time

            assert all(r.status_code == 200 for r in responses), "All requests should succeed"

            for idx, response in enumerate(responses):
                data = response.json()
                assert data["success"] is True
                assert data["execution_id"] == f"worker_exec_{idx}"
                assert data["output"]["value"] is not None
                assert f"after {delay_seconds}s" in data["output"]["value"]

            # If parallel, should take ~1s, not ~3s
            max_expected_time = delay_seconds + 0.5  # Allow 0.5s overhead
            assert total_time < max_expected_time

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_http_mixed_route_concurrent_execution():
    """Test concurrent tool execution across both MCP and Worker routes simultaneously."""
    process, port = start_mcp_server("http")
    assert port is not None

    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_http_server_ready(port, timeout=10)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(base_url=base_url, timeout=30.0, headers=headers) as client:
            # First, set up the client-server connection for the /mcp route
            init_request = build_jsonrpc_request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
                request_id=1,
            )
            init_response = await client.post("/mcp", json=init_request)
            session_id = init_response.headers.get("mcp-session-id")

            mcp_headers = {**headers, "Mcp-Session-Id": session_id}

            delay_seconds = 1.0

            await client.post(
                "/mcp",
                json=build_jsonrpc_request("notifications/initialized", None, None),
                headers=mcp_headers,
            )

            # Prepare the tool calls for both routes
            mcp_requests = [
                build_jsonrpc_request(
                    "tools/call",
                    {
                        "name": "Server_SlowAsyncTool",
                        "arguments": {"delay_seconds": delay_seconds},
                    },
                    request_id=10,
                ),
                build_jsonrpc_request(
                    "tools/call",
                    {
                        "name": "Server_SlowSyncTool",
                        "arguments": {"delay_seconds": delay_seconds},
                    },
                    request_id=11,
                ),
            ]

            worker_requests = [
                {
                    "execution_id": "worker_exec_0",
                    "tool": {
                        "toolkit": "Server",
                        "name": "SlowAsyncTool",
                    },
                    "inputs": {"delay_seconds": delay_seconds},
                },
                {
                    "execution_id": "worker_exec_1",
                    "tool": {
                        "toolkit": "Server",
                        "name": "SlowSyncTool",
                    },
                    "inputs": {"delay_seconds": delay_seconds},
                },
            ]

            # Execute
            start_time = time.time()
            mcp_responses, worker_responses = await asyncio.gather(
                asyncio.gather(*[
                    client.post("/mcp", json=req, headers=mcp_headers) for req in mcp_requests
                ]),
                asyncio.gather(*[
                    client.post("/worker/tools/invoke", json=req) for req in worker_requests
                ]),
            )
            total_time = time.time() - start_time

            assert all(r.status_code == 200 for r in mcp_responses)
            assert all(r.status_code == 200 for r in worker_responses)

            # Called the tools four times concurrently (2 MCP + 2 Worker). Each tool call takes 1 second to execute.
            # Since the server should be able to execute the tools in parallel, the total time should be around 1 second
            max_expected_time = delay_seconds + 0.5  # Allow 0.5s overhead for mixed routes
            assert total_time < max_expected_time

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.mark.asyncio
async def test_http_direct_python_invocation():
    """Test server starts correctly with direct Python (simulates what happens in the Engine during deployment)"""
    process, port = start_mcp_server_direct_python("http")
    assert port is not None

    try:
        wait_for_http_server_ready(port, timeout=10)

        # Verify server is healthy and tools are discoverable
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10.0, headers=headers)

        # Initialize
        init_response = client.post(
            "/mcp",
            json=build_jsonrpc_request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
                request_id=1,
            ),
        )
        assert init_response.status_code == 200

        session_id = init_response.headers.get("mcp-session-id")
        client.headers.update({"Mcp-Session-Id": session_id})

        # Send initialized notification
        init_notif = build_jsonrpc_request(
            "notifications/initialized", params=None, request_id=None
        )
        client.post("/mcp", json=init_notif)

        # List tools - should have 9 tools (including hello_world from entrypoint.py)
        list_response = client.post("/mcp", json=build_jsonrpc_request("tools/list", request_id=2))
        assert list_response.status_code == 200
        tools = list_response.json()["result"]["tools"]
        assert len(tools) == 9

        client.close()

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

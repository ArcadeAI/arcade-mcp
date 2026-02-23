#!/usr/bin/env python3
"""MCP protocol smoke test for generated Arcade servers.

Why this exists alongside ``libs/tests/arcade_mcp_server/integration/test_end_to_end.py``
------------------------------------------------------------------------------------------
The existing ``test_end_to_end.py`` is a pytest suite that validates the arcade-mcp-server
*library* against a dedicated test-fixture server with rich coverage (logging, progress
notifications, tool chaining, sampling, elicitation, concurrency).

This smoke test serves a **different purpose**:

1. **Tests ``arcade new`` scaffolded output** — validates that a *generated* project's
   ``server.py`` works end-to-end, catching template regressions that library tests
   cannot detect.
2. **Windows CI entry point** — invoked by ``no_auth_cli_smoke.ps1`` on ``windows-latest``
   runners. It contains Windows-specific process management (``taskkill /T /F``, non-
   ``select()`` stderr draining) that the pytest suite does not exercise.
3. **Stdlib-only / zero external deps** — runs with nothing beyond a ``uv run python``
   invocation so it works on fresh CI images before any ``pip install``.
4. **Standalone CLI** — uses ``argparse`` so PowerShell/bash scripts can invoke it
   directly without a pytest harness.

The basic protocol flow (initialize → initialized → ping → tools/list → tools/call) is
intentionally re-implemented here rather than imported, because the stdlib-only constraint
and the need to run outside the project's virtualenv make shared helpers impractical.

Usage::

    uv run python tests/integration/windows/mcp_protocol_smoke.py \\
        --server-dir "<path-to>/src/my_server" \\
        --transport both

Tool naming convention (for reference)::

    MCPApp(name="my_server") + def greet() -> MCP tool name "MyServer_Greet"
    Toolkit name is snake_to_pascal_case(app_name), tool is snake_to_pascal_case(func_name).
    MCP exposes the fully-qualified name with "." replaced by "_".
    We find the greet tool by case-insensitive substring match on "greet".
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


def _build_request(
    method: str,
    params: dict[str, Any] | None = None,
    req_id: int | None = None,
) -> dict[str, Any]:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if req_id is not None:
        msg["id"] = req_id
    return msg


def _parse_json_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        result = json.loads(line)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def _assert_ok(msg: dict[str, Any], expected_id: int, step: str) -> None:
    assert msg.get("jsonrpc") == "2.0", f"[{step}] jsonrpc != '2.0': {msg}"
    assert msg.get("id") == expected_id, f"[{step}] id != {expected_id}: {msg}"
    assert "error" not in msg, f"[{step}] unexpected error field: {msg['error']}"
    assert "result" in msg, f"[{step}] missing 'result' field: {msg}"


def _find_greet_tool(tools: list[dict[str, Any]]) -> str:
    """Return the MCP tool name that contains 'greet' (case-insensitive)."""
    for t in tools:
        name = str(t.get("name", ""))
        if "greet" in name.lower():
            return name
    names = [t.get("name") for t in tools]
    raise AssertionError(
        "No tool containing 'greet' (case-insensitive) found.\n"
        f"Available tools: {names}\n"
        "Expected the generated server to expose a 'greet' tool "
        "(e.g. MyServer_Greet from MCPApp(name='my_server') + def greet(...))."
    )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _kill_process(proc: subprocess.Popen) -> None:
    """Terminate a subprocess, using taskkill on Windows to kill the tree."""
    if proc.poll() is not None:
        return
    try:
        if platform.system() == "Windows":
            taskkill = shutil.which("taskkill") or "taskkill"
            subprocess.run(
                [taskkill, "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
            )
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()
            proc.wait(timeout=3)


def _drain_stderr(proc: subprocess.Popen, max_chars: int = 2000) -> str:
    """Non-blocking read of available stderr bytes for diagnostics."""
    if proc.stderr is None:
        return ""
    with contextlib.suppress(Exception):
        if platform.system() != "Windows":
            import select

            ready, _, _ = select.select([proc.stderr], [], [], 0.1)
            if ready:
                return str(proc.stderr.read(max_chars))
        else:
            # On Windows select() doesn't work on pipes; try reading with timeout
            import threading

            buf: list[str] = []

            def _reader() -> None:
                with contextlib.suppress(Exception):
                    buf.append(str(proc.stderr.read(max_chars)))  # type: ignore[union-attr]

            t = threading.Thread(target=_reader, daemon=True)
            t.start()
            t.join(timeout=0.5)
            return buf[0] if buf else ""
    return ""


def _tail_text_file(path: str | None, max_chars: int = 4000) -> str:
    """Return the tail of a UTF-8 log file for diagnostics."""
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        return data[-max_chars:]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Stdio transport
# ---------------------------------------------------------------------------


class StdioClient:
    """Communicate with an MCP server over stdin/stdout."""

    def __init__(self, proc: subprocess.Popen, timeout: float = 30.0) -> None:
        self.proc = proc
        self.timeout = timeout
        self._next_id = 1
        self._stdout_queue: queue.Queue[str | None] = queue.Queue()
        self._stdout_reader = threading.Thread(target=self._read_stdout_loop, daemon=True)
        self._stdout_reader.start()

    def _read_stdout_loop(self) -> None:
        if self.proc.stdout is None:
            self._stdout_queue.put(None)
            return
        try:
            for raw in self.proc.stdout:
                self._stdout_queue.put(raw)
        finally:
            self._stdout_queue.put(None)

    def _next(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> int:
        rid = self._next()
        line = json.dumps(_build_request(method, params, rid)) + "\n"
        assert self.proc.stdin is not None
        self.proc.stdin.write(line)
        self.proc.stdin.flush()
        return rid

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        line = json.dumps(_build_request(method, params)) + "\n"
        assert self.proc.stdin is not None
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def read_response(self, expected_id: int) -> dict[str, Any]:
        """Read lines until we get a JSON-RPC message with the expected id."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                stderr_snippet = _drain_stderr(self.proc)
                raise RuntimeError(
                    f"Server exited (code={self.proc.returncode}) while waiting for id={expected_id}.\n"
                    f"STDERR snippet:\n{stderr_snippet}"
                )
            timeout = min(0.5, max(0.0, deadline - time.monotonic()))
            try:
                raw = self._stdout_queue.get(timeout=timeout)
            except queue.Empty:
                continue
            if raw is None:
                stderr_snippet = _drain_stderr(self.proc)
                raise RuntimeError(
                    f"Server stdout closed (EOF) while waiting for id={expected_id}.\n"
                    f"STDERR snippet:\n{stderr_snippet}"
                )
            msg = _parse_json_line(raw)
            if msg is None:
                # Non-JSON line (server log/debug output) — skip
                print(f"  [stdio/log] {raw.rstrip()}", flush=True)
                continue
            if msg.get("id") != expected_id:
                # Notification or out-of-order message — log and skip
                print(f"  [stdio/msg] {json.dumps(msg)}", flush=True)
                continue
            return msg
        raise TimeoutError(f"Timed out after {self.timeout}s waiting for id={expected_id}")


def run_stdio(server_dir: str, timeout: float) -> None:
    print("\n=== Stdio transport MCP protocol smoke ===", flush=True)
    proc: subprocess.Popen | None = None
    stderr_sink = None
    stderr_log_path: str | None = None
    step = "startup"
    last_response: dict[str, Any] = {}
    try:
        uv = shutil.which("uv") or "uv"
        stderr_sink = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="arcade-mcp-stdio-",
            suffix=".log",
            buffering=1,
            delete=False,
        )
        stderr_log_path = stderr_sink.name
        proc = subprocess.Popen(
            [uv, "run", "server.py"],
            cwd=server_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_sink,
            text=True,
            bufsize=1,
        )

        # Give the server a moment to initialize before we write to stdin
        time.sleep(3)
        if proc.poll() is not None:
            stdout_out = proc.stdout.read() if proc.stdout else ""
            stderr_out = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(  # noqa: TRY301
                f"Server exited early (code={proc.returncode}).\n"
                f"STDOUT:\n{stdout_out}\nSTDERR:\n{stderr_out}"
            )

        client = StdioClient(proc, timeout=timeout)

        # 1. initialize
        step = "initialize"
        print(f"Step 1: {step}", flush=True)
        init_id = client.send_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "arcade-windows-ci", "version": "0.1.0"},
            },
        )
        last_response = client.read_response(expected_id=init_id)
        _assert_ok(last_response, init_id, step)
        server_info = last_response["result"].get("serverInfo", {})
        print(f"  OK — serverInfo={server_info}", flush=True)

        # 2. notifications/initialized
        step = "notifications/initialized"
        print(f"Step 2: {step}", flush=True)
        client.send_notification("notifications/initialized")
        print("  OK — notification sent", flush=True)

        # 3. ping
        step = "ping"
        print(f"Step 3: {step}", flush=True)
        ping_id = client.send_request("ping")
        last_response = client.read_response(expected_id=ping_id)
        assert last_response.get("jsonrpc") == "2.0", f"[ping] jsonrpc != '2.0': {last_response}"
        assert last_response.get("id") == ping_id, f"[ping] id mismatch: {last_response}"
        assert "error" not in last_response, f"[ping] error in response: {last_response}"
        print("  OK", flush=True)

        # 4. tools/list
        step = "tools/list"
        print(f"Step 4: {step}", flush=True)
        list_id = client.send_request("tools/list")
        last_response = client.read_response(expected_id=list_id)
        _assert_ok(last_response, list_id, step)
        tools: list[dict[str, Any]] = last_response["result"].get("tools", [])
        assert len(tools) > 0, f"[tools/list] empty tools list: {last_response}"
        tool_names = [t.get("name") for t in tools]
        print(f"  OK — {len(tools)} tools: {tool_names}", flush=True)

        # 5. tools/call greet
        step = "tools/call(greet)"
        print(f"Step 5: {step}", flush=True)
        greet_name = _find_greet_tool(tools)
        print(f"  using tool: {greet_name!r}", flush=True)
        call_id = client.send_request(
            "tools/call",
            {"name": greet_name, "arguments": {"name": "Windows CI"}},
        )
        last_response = client.read_response(expected_id=call_id)
        _assert_ok(last_response, call_id, step)
        content = last_response["result"].get("content", [])
        assert len(content) > 0, f"[{step}] empty content array: {last_response}"
        text: str = content[0].get("text", "")
        assert "Hello" in text, (
            f"[{step}] expected 'Hello' in response text.\n"
            f"  Got: {text!r}\n"
            f"  Full response: {last_response}"
        )
        print(f"  OK — response: {text!r}", flush=True)

        print("\nStdio transport smoke PASSED.", flush=True)

    except Exception as exc:
        if stderr_sink is not None:
            with contextlib.suppress(Exception):
                stderr_sink.flush()
        stderr_snippet = _tail_text_file(stderr_log_path) if stderr_log_path else ""
        print(
            f"\nSTDIO SMOKE FAILED at step '{step}'.\n"
            f"  Error: {exc}\n"
            f"  Last response: {json.dumps(last_response) if last_response else 'n/a'}\n"
            f"  Server STDERR snippet:\n{stderr_snippet}",
            file=sys.stderr,
            flush=True,
        )
        raise
    finally:
        if stderr_sink is not None:
            with contextlib.suppress(Exception):
                stderr_sink.close()
        if proc is not None:
            _kill_process(proc)


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------


def _http_post(
    url: str,
    payload: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
    read_response_headers: bool = False,
    timeout_seconds: float = 30.0,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    """POST JSON payload, return (status, response_headers, body_dict)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")  # noqa: S310
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            status: int = resp.status
            # http.client.HTTPMessage supports case-insensitive get()
            resp_headers: dict[str, str] = {}
            if read_response_headers:
                for key in resp.headers:
                    resp_headers[key.lower()] = resp.headers[key]
            raw = resp.read().decode("utf-8")
            body_dict: dict[str, Any] = json.loads(raw) if raw.strip() else {}
            return status, resp_headers, body_dict
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8")
        try:
            return status, {}, json.loads(raw)
        except Exception:
            return status, {}, {"_raw": raw}


def _wait_for_health(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(Exception):
            req = urllib.request.Request(url)  # noqa: S310
            with urllib.request.urlopen(req, timeout=2) as resp:  # noqa: S310
                if resp.status == 200:
                    return
        time.sleep(1)
    raise TimeoutError(f"Server did not become healthy at {url} within {timeout}s")


def run_http(server_dir: str, timeout: float) -> None:
    print("\n=== HTTP transport MCP protocol smoke ===", flush=True)
    port = _find_free_port()
    proc: subprocess.Popen | None = None
    stdout_sink = None
    stderr_sink = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    step = "startup"
    last_response: dict[str, Any] = {}
    try:
        env = {
            **os.environ,
            "ARCADE_SERVER_HOST": "127.0.0.1",
            "ARCADE_SERVER_PORT": str(port),
            "ARCADE_WORKER_SECRET": "arcade-smoke-worker-secret",
        }
        uv = shutil.which("uv") or "uv"
        stdout_sink = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="arcade-mcp-http-out-",
            suffix=".log",
            buffering=1,
            delete=False,
        )
        stdout_log_path = stdout_sink.name
        stderr_sink = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="arcade-mcp-http-err-",
            suffix=".log",
            buffering=1,
            delete=False,
        )
        stderr_log_path = stderr_sink.name
        proc = subprocess.Popen(
            [uv, "run", "server.py", "http"],
            cwd=server_dir,
            stdout=stdout_sink,
            stderr=stderr_sink,
            text=True,
            env=env,
        )

        base_url = f"http://127.0.0.1:{port}"
        health_url = f"{base_url}/worker/health"
        mcp_url = f"{base_url}/mcp"

        print(f"  waiting for health at {health_url} (up to 30s)", flush=True)
        _wait_for_health(health_url, timeout=30)
        if proc.poll() is not None:
            stderr_out = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(  # noqa: TRY301
                f"Server exited (code={proc.returncode}) before health check passed.\n"
                f"STDERR:\n{stderr_out}"
            )
        print("  health OK", flush=True)

        session_headers: dict[str, str] = {}

        # 1. initialize — capture mcp-session-id from response headers
        step = "initialize"
        print(f"Step 1: {step}", flush=True)
        init_req = _build_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "arcade-windows-ci", "version": "0.1.0"},
            },
            req_id=1,
        )
        init_status, init_hdrs, last_response = _http_post(
            mcp_url, init_req, read_response_headers=True, timeout_seconds=timeout
        )
        assert (
            init_status == 200
        ), f"[{step}] expected status 200, got {init_status}: {last_response}"
        assert last_response.get("jsonrpc") == "2.0", f"[{step}] jsonrpc != '2.0': {last_response}"
        assert last_response.get("id") == 1, f"[{step}] id != 1: {last_response}"
        assert "error" not in last_response, f"[{step}] error in response: {last_response}"
        session_id = init_hdrs.get("mcp-session-id")
        assert session_id is not None, (
            f"[{step}] mcp-session-id header missing from initialize response.\n"
            f"  Headers received: {init_hdrs}"
        )
        session_headers["Mcp-Session-Id"] = session_id
        server_info = last_response["result"].get("serverInfo", {})
        print(f"  OK — serverInfo={server_info}, session_id={session_id}", flush=True)

        # 2. notifications/initialized
        step = "notifications/initialized"
        print(f"Step 2: {step}", flush=True)
        notif_req = _build_request("notifications/initialized")
        notif_status, _, _ = _http_post(mcp_url, notif_req, extra_headers=session_headers)
        assert notif_status == 202, f"[{step}] expected status 202, got {notif_status}"
        print("  OK (202)", flush=True)

        # 3. ping
        step = "ping"
        print(f"Step 3: {step}", flush=True)
        ping_status, _, last_response = _http_post(
            mcp_url,
            _build_request("ping", req_id=2),
            extra_headers=session_headers,
            timeout_seconds=timeout,
        )
        assert ping_status == 200, f"[{step}] expected 200, got {ping_status}: {last_response}"
        assert last_response.get("jsonrpc") == "2.0", f"[{step}] jsonrpc: {last_response}"
        assert last_response.get("id") == 2, f"[{step}] id: {last_response}"
        assert "error" not in last_response, f"[{step}] error: {last_response}"
        print("  OK", flush=True)

        # 4. tools/list
        step = "tools/list"
        print(f"Step 4: {step}", flush=True)
        list_status, _, last_response = _http_post(
            mcp_url,
            _build_request("tools/list", req_id=3),
            extra_headers=session_headers,
            timeout_seconds=timeout,
        )
        assert list_status == 200, f"[{step}] expected 200, got {list_status}: {last_response}"
        _assert_ok(last_response, 3, step)
        tools = last_response["result"].get("tools", [])
        assert len(tools) > 0, f"[{step}] empty tools list: {last_response}"
        tool_names = [t.get("name") for t in tools]
        print(f"  OK — {len(tools)} tools: {tool_names}", flush=True)

        # 5. tools/call greet
        step = "tools/call(greet)"
        print(f"Step 5: {step}", flush=True)
        greet_name = _find_greet_tool(tools)
        print(f"  using tool: {greet_name!r}", flush=True)
        call_status, _, last_response = _http_post(
            mcp_url,
            _build_request(
                "tools/call",
                {"name": greet_name, "arguments": {"name": "Windows CI"}},
                req_id=4,
            ),
            extra_headers=session_headers,
            timeout_seconds=timeout,
        )
        assert call_status == 200, f"[{step}] expected 200, got {call_status}: {last_response}"
        _assert_ok(last_response, 4, step)
        content = last_response["result"].get("content", [])
        assert len(content) > 0, f"[{step}] empty content: {last_response}"
        text: str = content[0].get("text", "")
        assert "Hello" in text, (
            f"[{step}] expected 'Hello' in response text.\n"
            f"  Got: {text!r}\n"
            f"  Full response: {last_response}"
        )
        print(f"  OK — response: {text!r}", flush=True)

        print("\nHTTP transport smoke PASSED.", flush=True)

    except Exception as exc:
        if stdout_sink is not None:
            with contextlib.suppress(Exception):
                stdout_sink.flush()
        if stderr_sink is not None:
            with contextlib.suppress(Exception):
                stderr_sink.flush()
        stdout_tail = _tail_text_file(stdout_log_path) if stdout_log_path else ""
        stderr_tail = _tail_text_file(stderr_log_path) if stderr_log_path else ""
        print(
            f"\nHTTP SMOKE FAILED at step '{step}'.\n"
            f"  Error: {exc}\n"
            f"  Last response: {json.dumps(last_response) if last_response else 'n/a'}\n"
            f"  Server STDOUT snippet:\n{stdout_tail}\n"
            f"  Server STDERR snippet:\n{stderr_tail}",
            file=sys.stderr,
            flush=True,
        )
        raise
    finally:
        if stdout_sink is not None:
            with contextlib.suppress(Exception):
                stdout_sink.close()
        if stderr_sink is not None:
            with contextlib.suppress(Exception):
                stderr_sink.close()
        if proc is not None:
            _kill_process(proc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP protocol smoke test for a generated Arcade server."
    )
    parser.add_argument(
        "--server-dir",
        required=True,
        help="Directory containing server.py (the generated server src dir).",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "both"],
        default="both",
        help="Transport(s) to validate (default: both).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Per-step read timeout in seconds (default: 30).",
    )
    args = parser.parse_args()

    server_dir = os.path.abspath(args.server_dir)
    if not os.path.isdir(server_dir):
        print(f"ERROR: --server-dir does not exist: {server_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(os.path.join(server_dir, "server.py")):
        print(
            f"ERROR: server.py not found in --server-dir: {server_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Server dir : {server_dir}")
    print(f"Transport  : {args.transport}")
    print(f"Timeout    : {args.timeout_seconds}s per step")

    failures: list[str] = []

    if args.transport in ("stdio", "both"):
        try:
            run_stdio(server_dir, timeout=args.timeout_seconds)
        except Exception as exc:
            failures.append(f"stdio: {exc}")

    if args.transport in ("http", "both"):
        try:
            run_http(server_dir, timeout=args.timeout_seconds)
        except Exception as exc:
            failures.append(f"http: {exc}")

    if failures:
        print("\n=== MCP PROTOCOL SMOKE FAILURES ===", file=sys.stderr)
        for msg in failures:
            print(f"  ✗ {msg}", file=sys.stderr)
        sys.exit(1)

    print("\nAll MCP protocol smoke checks PASSED.", flush=True)


if __name__ == "__main__":
    main()

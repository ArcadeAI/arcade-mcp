"""Start commands for the MCP servers ``arcade deploy`` hosts.

The runner starts a deployed MCP server with the command chosen here, the first that applies:

1. An explicit ``command`` from the deploy config.
2. ``fastmcp`` declared and a ``fastmcp.json``: ``fastmcp run fastmcp.json``.
3. ``fastmcp`` declared: ``fastmcp run <file>:<name>`` for the single module-level server
   object. ``fastmcp run`` also serves MCP SDK server objects.
4. The MCP SDK without ``fastmcp``: ``python <file>`` for the file that calls
   ``run("streamable-http")``. ``fastmcp`` is never added: each fastmcp major requires a
   particular SDK major, so adding it could change the SDK the author tested.
5. Otherwise the deploy is refused, asking for ``command``.

Server objects are found by parsing the project's source, never by importing it.

``fastmcp run`` gets fixed flags, so its port and path are known. Every other command's
port is detected: the loopback listener owned by the started process's tree (``uv run``,
``uvicorn --workers`` and gunicorn listen from a descendant), never any listener on the
machine. Its path is the first of ``/mcp`` and ``/`` that answers the MCP handshake, unless
the ``path`` setting names it.
"""

from __future__ import annotations

import ast
import contextlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import httpx
import psutil
from arcade_core.subprocess_utils import (
    get_windows_no_window_creationflags,
    graceful_terminate_process,
)
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from arcade_cli.configure import find_python_interpreter

Framework = Literal["fastmcp", "mcp-sdk-1", "mcp-sdk-2"]
Source = Literal["command", "fastmcp.json", "fastmcp", "mcp-sdk"]

RUNNER_HOST = "127.0.0.1"
RUNNER_PORT = 8000
FASTMCP_PATH = "/mcp"
DETECTED_PATHS = ("/mcp", "/")
MCP_PROTOCOL_VERSION = "2025-06-18"


def _fastmcp_run_flags(path: str) -> tuple[str, ...]:
    # --transport http: fastmcp 2.x ignores FASTMCP_TRANSPORT, and every run() defaults to stdio.
    # --no-banner: the banner checks PyPI for a newer version, which stalls start without egress.
    # --skip-env: the runner has installed the dependencies; without it a fastmcp.json
    #   `environment` block re-runs the server under `uv run`, which needs the network.
    return (
        "--transport",
        "http",
        "--host",
        RUNNER_HOST,
        "--port",
        str(RUNNER_PORT),
        "--path",
        path,
        "--no-banner",
        "--skip-env",
    )


FASTMCP_RUN_FLAGS = _fastmcp_run_flags(FASTMCP_PATH)

_SERVER_CLASSES: dict[str, Framework] = {
    "fastmcp.FastMCP": "fastmcp",
    "fastmcp.server.FastMCP": "fastmcp",
    "fastmcp.server.server.FastMCP": "fastmcp",
    "mcp.server.FastMCP": "mcp-sdk-1",
    "mcp.server.fastmcp.FastMCP": "mcp-sdk-1",
    "mcp.server.fastmcp.server.FastMCP": "mcp-sdk-1",
    "mcp.server.MCPServer": "mcp-sdk-2",
    "mcp.server.mcpserver.MCPServer": "mcp-sdk-2",
    "mcp.server.mcpserver.server.MCPServer": "mcp-sdk-2",
}

_SKIPPED_DIRS = {
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "site-packages",
    "test",
    "tests",
    "venv",
}

_ASK_FOR_COMMAND = (
    "Set `command` in [tool.arcade.deploy] in pyproject.toml (or [deploy] in arcade.toml) "
    "to the command that starts your server over streamable HTTP."
)


class StartCommandError(ValueError):
    """The server's start command can't be determined, or the server didn't start."""


@dataclass(frozen=True)
class StartCommand:
    """How the runner starts the server.

    ``command`` is what the deploy sends. ``port`` and ``path`` are known for
    ``fastmcp run``; ``None`` means they are detected from the running server.
    """

    command: str
    source: Source
    port: int | None = None
    path: str | None = None

    @property
    def argv(self) -> tuple[str, ...]:
        return tuple(shlex.split(self.command))

    def local_argv(self, port: int | None) -> list[str]:
        """The command to run on this machine, on ``port`` when the port is fixed."""
        argv = list(self.argv)
        if self.port is not None and port is not None:
            argv[argv.index("--port") + 1] = str(port)
        return argv


@dataclass(frozen=True)
class ServerObject:
    """A module-level ``<name> = FastMCP(...)`` or ``MCPServer(...)``."""

    file: Path
    name: str
    framework: Framework
    line: int


@dataclass(frozen=True)
class _RunCall:
    file: Path
    line: int
    transport: str | None  # None: chosen at runtime


# Choosing the command


def resolve_start_command(
    project_dir: Path, *, command: str | None = None, path: str | None = None
) -> StartCommand:
    """Choose how to start the server in ``project_dir``, or refuse with the reason."""
    if path is not None and not path.startswith("/"):
        raise StartCommandError(f"`path` must start with '/': {path!r}")
    if command is not None:
        if not command.strip():
            raise StartCommandError(
                "`command` is empty. Set it to the command that starts your server, or remove it."
            )
        return StartCommand(command=command.strip(), source="command", path=path)

    modules = _parse_project(project_dir)
    servers = [obj for file, tree in modules for obj in _server_objects(file, tree)]
    if "fastmcp" in declared_dependencies(project_dir):
        return _fastmcp_run(project_dir, servers, path)
    return _sdk_script(modules, servers, path)


def _fastmcp_run(project_dir: Path, servers: list[ServerObject], path: str | None) -> StartCommand:
    source: Source
    if (project_dir / "fastmcp.json").is_file():
        source, target = "fastmcp.json", "fastmcp.json"
    elif len(servers) == 1:
        source, target = "fastmcp", f"{servers[0].file.as_posix()}:{servers[0].name}"
    elif servers:
        found = "\n".join(f"  {obj.file.as_posix()}:{obj.name}" for obj in servers)
        raise StartCommandError(
            f"Found several MCP server objects, so which one to serve is ambiguous:\n{found}\n"
            f"{_ASK_FOR_COMMAND} For example: command = "
            f'"fastmcp run {servers[0].file.as_posix()}:{servers[0].name}"'
        )
    else:
        raise StartCommandError(
            "fastmcp is a dependency, but no module-level server object "
            f"(`mcp = FastMCP(...)`) was found. {_ASK_FOR_COMMAND}"
        )
    path = path or FASTMCP_PATH
    argv = ("fastmcp", "run", target, *_fastmcp_run_flags(path))
    return StartCommand(command=shlex.join(argv), source=source, port=RUNNER_PORT, path=path)


def _sdk_script(
    modules: list[tuple[Path, ast.Module]], servers: list[ServerObject], path: str | None
) -> StartCommand:
    sdk_servers = [obj for obj in servers if obj.framework != "fastmcp"]
    runs = _run_calls(modules, sdk_servers)
    http_files = sorted({run.file for run in runs if run.transport == "streamable-http"})
    if len(http_files) == 1:
        script = http_files[0]
        if _uses_relative_imports(dict(modules)[script]):
            raise StartCommandError(
                f"{script.as_posix()} uses relative imports, so `python {script.as_posix()}` "
                f"can't run it. {_ASK_FOR_COMMAND} For example: "
                f'command = "python -m {_module_name(script)}"'
            )
        argv = ("python", script.as_posix())
        return StartCommand(command=shlex.join(argv), source="mcp-sdk", path=path)
    if http_files:
        found = "\n".join(f"  {file.as_posix()}" for file in http_files)
        raise StartCommandError(
            f'Several files call run("streamable-http"), so which one to start is ambiguous:\n'
            f"{found}\n{_ASK_FOR_COMMAND}"
        )
    if runs:
        raise _unservable_run(runs[0])
    fastmcp_servers = [obj for obj in servers if obj.framework == "fastmcp"]
    if fastmcp_servers:
        obj = fastmcp_servers[0]
        raise StartCommandError(
            f"{obj.file.as_posix()}:{obj.line} creates a fastmcp server, but fastmcp isn't a "
            "declared dependency. Add it to your dependencies, or set `command`."
        )
    raise StartCommandError(f"Couldn't tell how to start this server. {_ASK_FOR_COMMAND}")


def _unservable_run(run: _RunCall) -> StartCommandError:
    where = f"{run.file.as_posix()}:{run.line}"
    if run.transport is None:
        return StartCommandError(
            f"{where} chooses its transport at runtime, so the start command can't be "
            f"detected. {_ASK_FOR_COMMAND}"
        )
    if run.transport == "stdio":
        problem = "serves stdio"
    else:
        problem = f"serves the {run.transport!r} transport"
    return StartCommandError(
        f'{where} {problem}, but Arcade Deploy needs streamable HTTP. Call run("streamable-http") '
        "there, or set `command`."
    )


def declared_dependencies(project_dir: Path) -> set[str]:
    """Normalized names of the dependencies the runner installs.

    Read from ``[project].dependencies`` in pyproject.toml and from requirements.txt.
    """
    specs: list[str] = []
    pyproject = project_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = load_toml(pyproject)
        except Exception as e:
            raise StartCommandError(f"pyproject.toml couldn't be read: {e}") from e
        specs.extend(data.get("project", {}).get("dependencies", []) or [])
    requirements = project_dir / "requirements.txt"
    if requirements.is_file():
        specs.extend(requirement_specs(requirements))

    names: set[str] = set()
    for spec in specs:
        with contextlib.suppress(InvalidRequirement):
            names.add(canonicalize_name(Requirement(spec).name))
    return names


def requirement_specs(path: Path, seen: set[Path] | None = None) -> Iterator[str]:
    """The requirement lines of a requirements file, following ``-r`` includes."""
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen or not path.is_file():
        return
    seen.add(path)
    # A trailing backslash continues a line, as in `uv export` and `pip-compile` output.
    text = re.sub(r"\\\r?\n", " ", path.read_text(encoding="utf-8-sig"))
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*", "", line).strip()
        include = re.match(r"(?:-r|--requirement)(?:\s*=\s*|\s+)(\S+)$", line)
        if include:
            yield from requirement_specs(path.parent / include.group(1), seen)
        elif line and not line.startswith("-"):
            # Per-requirement options such as --hash follow the requirement itself.
            yield re.split(r"\s+--", line, maxsplit=1)[0]


def load_toml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if sys.version_info >= (3, 11):
        import tomllib

        return tomllib.loads(text)
    import toml

    return cast(dict[str, Any], toml.loads(text))


# Scanning source


def find_server_objects(project_dir: Path) -> list[ServerObject]:
    """Every module-level MCP server object in the project's source."""
    return [
        obj for file, tree in _parse_project(project_dir) for obj in _server_objects(file, tree)
    ]


def _parse_project(project_dir: Path) -> list[tuple[Path, ast.Module]]:
    """Parse the project's Python files, skipping tests, environments and unparsable files."""
    modules: list[tuple[Path, ast.Module]] = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted(
            d
            for d in dirs
            if not d.startswith(".")
            and d not in _SKIPPED_DIRS
            and not (Path(root) / d / "pyvenv.cfg").exists()
        )
        for name in sorted(files):
            if not name.endswith(".py") or _is_test_file(name):
                continue
            path = Path(root) / name
            try:
                # Bytes, so Python's own rules apply: a byte-order mark or coding cookie.
                tree = ast.parse(path.read_bytes(), filename=str(path))
            except (SyntaxError, ValueError):
                continue
            modules.append((path.relative_to(project_dir), tree))
    return modules


def _is_test_file(name: str) -> bool:
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def _server_objects(file: Path, tree: ast.Module) -> list[ServerObject]:
    imports = _imported_names(tree)
    found: list[ServerObject] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            targets, value = stmt.targets, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets, value = [stmt.target], stmt.value
        else:
            continue
        framework = _framework_created_by(value, imports)
        if framework is None:
            continue
        found.extend(
            ServerObject(file=file, name=target.id, framework=framework, line=stmt.lineno)
            for target in targets
            if isinstance(target, ast.Name)
        )
    return found


def _imported_names(tree: ast.Module) -> dict[str, str]:
    """Map each name a module imports to the dotted name it refers to."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    names[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    names[top] = top
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return names


def _framework_created_by(value: ast.expr, imports: dict[str, str]) -> Framework | None:
    """The framework whose server ``value`` creates: ``FastMCP(...)`` or ``FastMCP.from_*(...)``."""
    if not isinstance(value, ast.Call):
        return None
    called = _dotted_name(value.func, imports)
    if called is None:
        return None
    if called in _SERVER_CLASSES:
        return _SERVER_CLASSES[called]
    owner, _, method = called.rpartition(".")
    if method.startswith("from_") and owner in _SERVER_CLASSES:
        return _SERVER_CLASSES[owner]
    return None


def _dotted_name(expr: ast.expr, imports: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Name):
        return imports.get(expr.id)
    if isinstance(expr, ast.Attribute):
        owner = _dotted_name(expr.value, imports)
        return f"{owner}.{expr.attr}" if owner else None
    return None


def _run_calls(
    modules: list[tuple[Path, ast.Module]], servers: list[ServerObject]
) -> list[_RunCall]:
    """Every ``<server>.run(...)`` on an SDK server object, in its own file or imported."""
    calls: list[_RunCall] = []
    for file, tree in modules:
        receivers = {obj.name for obj in servers if obj.file == file}
        receivers |= {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
            for obj in servers
            if alias.name == obj.name and _imports_from(node, file, obj.file)
        }
        calls.extend(
            _RunCall(file=file, line=node.lineno, transport=_transport(node))
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in receivers
        )
    return calls


def _imports_from(node: ast.ImportFrom, importer: Path, source: Path) -> bool:
    """Whether ``node`` in ``importer`` imports from the module in ``source``."""
    source_parts = source.with_suffix("").parts
    if source_parts[-1] == "__init__":
        source_parts = source_parts[:-1]
    module_parts = tuple(node.module.split(".")) if node.module else ()
    if node.level == 0:
        # Absolute: the module path ends the source's path (src/pkg/server.py is pkg.server).
        return bool(module_parts) and source_parts[-len(module_parts) :] == module_parts
    package = importer.parent.parts
    if node.level > 1:
        package = package[: -(node.level - 1)]
    return (*package, *module_parts) == source_parts


def _uses_relative_imports(tree: ast.Module) -> bool:
    return any(isinstance(node, ast.ImportFrom) and node.level > 0 for node in ast.walk(tree))


def _module_name(script: Path) -> str:
    """The dotted name ``python -m`` runs ``script`` as: a package for its ``__main__.py``."""
    parts = script.with_suffix("").parts
    if parts[-1] == "__main__":
        parts = parts[:-1]
    return ".".join(parts)


def _transport(call: ast.Call) -> str | None:
    """The transport a ``run(...)`` call serves: ``stdio`` when bare, ``None`` when not literal."""
    argument = call.args[0] if call.args else None
    for keyword in call.keywords:
        if keyword.arg == "transport":
            argument = keyword.value
    if argument is None:
        return "stdio"
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    return None


# Running locally


@dataclass(frozen=True)
class Handshake:
    """What a server answered to ``initialize``."""

    server_name: str
    server_version: str
    protocol_version: str
    session_id: str | None


@dataclass(frozen=True)
class LocalEndpoint:
    """The MCP endpoint of a server started on this machine."""

    pid: int
    port: int
    path: str
    handshake: Handshake

    @property
    def url(self) -> str:
        return f"http://{RUNNER_HOST}:{self.port}{self.path}"


@contextlib.contextmanager
def run_locally(
    start: StartCommand,
    project_dir: Path,
    *,
    env: Mapping[str, str] | None = None,
    debug: bool = False,
    timeout: float = 30.0,
) -> Iterator[LocalEndpoint]:
    """Start the server in its project's environment and yield its MCP endpoint.

    A fixed port is replaced with a free one, since this machine may already use 8000.
    The server and every process it started are stopped on exit.
    """
    port = _free_port() if start.port is not None else None
    process = _spawn(start.local_argv(port), project_dir, env, debug)
    try:
        yield _wait_for_endpoint(process, start, port, timeout, debug)
    finally:
        stop_process_tree(process)


def _spawn(
    argv: list[str], project_dir: Path, env: Mapping[str, str] | None, debug: bool
) -> subprocess.Popen[bytes]:
    # Commands name executables from the project's environment (python, fastmcp, uvicorn),
    # the way the runner's PATH resolves them.
    bin_dir = str(find_python_interpreter(project_dir).parent)
    child_env = {**os.environ, **(env or {})}
    child_env["PATH"] = bin_dir + os.pathsep + child_env.get("PATH", "")
    executable = shutil.which(argv[0], path=child_env["PATH"])
    if executable is None:
        raise StartCommandError(
            f"`{argv[0]}` wasn't found in the project's environment ({bin_dir}) or on PATH."
        )
    output = None if debug else subprocess.DEVNULL
    return subprocess.Popen(
        [executable, *argv[1:]],
        cwd=project_dir,
        env=child_env,
        stdout=output,
        stderr=output,
        creationflags=get_windows_no_window_creationflags(new_process_group=True),
    )


def _wait_for_endpoint(
    process: subprocess.Popen[bytes],
    start: StartCommand,
    port: int | None,
    timeout: float,
    debug: bool,
) -> LocalEndpoint:
    paths = (start.path,) if start.path else DETECTED_PATHS
    hint = (
        "Check the server output above."
        if debug
        else "Re-run with --debug to see the server's output."
    )
    listened: set[int] = set()
    ipv6_only: set[int] = set()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise StartCommandError(
                f"The server exited with code {code} before answering the MCP handshake. {hint}"
            )
        if port is not None:
            ports = [port]
        else:
            ports, ipv6_ports = _owned_loopback_ports(process.pid)
            ipv6_only.update(set(ipv6_ports) - set(ports))
        for candidate_port in ports:
            if not _is_listening(candidate_port):
                continue
            listened.add(candidate_port)
            for candidate_path in paths:
                url = f"http://{RUNNER_HOST}:{candidate_port}{candidate_path}"
                handshake = mcp_handshake(url)
                if handshake is not None:
                    return LocalEndpoint(process.pid, candidate_port, candidate_path, handshake)
        time.sleep(0.25)
    raise _no_endpoint(paths, listened, ipv6_only, timeout, hint)


def _no_endpoint(
    paths: tuple[str, ...], listened: set[int], ipv6_only: set[int], timeout: float, hint: str
) -> StartCommandError:
    if listened:
        tried = ", ".join(paths)
        ports_tried = ", ".join(str(p) for p in sorted(listened))
        return StartCommandError(
            f"The server answered the MCP handshake on no path (tried {tried} on port "
            f"{ports_tried}). If it serves MCP somewhere else, set `path`."
        )
    if ipv6_only:
        addresses = ", ".join(f"[::1]:{p}" for p in sorted(ipv6_only))
        return StartCommandError(
            f"The server listens on {addresses} only, but Arcade Deploy connects to it at "
            f"{RUNNER_HOST}. Listen on {RUNNER_HOST} instead."
        )
    return StartCommandError(
        f"The server listened on no loopback port within {timeout:g} seconds. {hint}"
    )


def _owned_loopback_ports(pid: int) -> tuple[list[int], list[int]]:
    """IPv4 and IPv6 loopback ports listened on by ``pid`` or its descendants, ascending.

    Uses each process's own connections: the system-wide ``psutil.net_connections()``
    needs root on macOS, and would also find servers this command didn't start.
    """
    ipv4: set[int] = set()
    ipv6: set[int] = set()
    other: list[str] = []
    for host, port in _owned_listeners(pid):
        if not _is_loopback(host):
            other.append(f"[{host}]:{port}" if ":" in host else f"{host}:{port}")
        elif ":" in host:
            ipv6.add(port)
        else:
            ipv4.add(port)
    if other:
        raise StartCommandError(
            f"The server listens on {', '.join(sorted(set(other)))}, which isn't a loopback "
            f"address. Arcade Deploy requires the server to listen on {RUNNER_HOST} only."
        )
    return sorted(ipv4), sorted(ipv6)


def _owned_listeners(pid: int) -> Iterable[tuple[str, int]]:
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.Error:
        return []
    listeners: list[tuple[str, int]] = []
    for process in processes:
        try:
            connections = process.net_connections(kind="tcp")
        except psutil.Error:
            continue
        listeners.extend(
            (conn.laddr.ip, conn.laddr.port)
            for conn in connections
            if conn.status == psutil.CONN_LISTEN and conn.laddr
        )
    return listeners


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_listening(port: int) -> bool:
    try:
        socket.create_connection((RUNNER_HOST, port), timeout=0.5).close()
    except OSError:
        return False
    return True


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((RUNNER_HOST, 0))
        return int(sock.getsockname()[1])


def stop_process_tree(process: subprocess.Popen[bytes], timeout: float = 5.0) -> None:
    """Stop ``process`` and every process it started."""
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.Error:
        descendants = []
    graceful_terminate_process(process)
    for child in descendants:
        with contextlib.suppress(psutil.Error):
            child.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    _, alive = psutil.wait_procs(descendants, timeout=timeout)
    for child in alive:
        with contextlib.suppress(psutil.Error):
            child.kill()


# Speaking MCP

# Every POST to a streamable HTTP endpoint advertises both, since the server may answer
# with an event stream (MCP 2025-11-25, transports).
_MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def mcp_handshake(
    url: str, *, headers: Mapping[str, str] | None = None, timeout: float = 5.0
) -> Handshake | None:
    """Send ``initialize`` to ``url``; ``None`` when it doesn't answer as an MCP endpoint."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "arcade-deploy", "version": "1.0.0"},
        },
    }
    try:
        response = httpx.post(
            url,
            json=request,
            headers={**_MCP_HEADERS, **(headers or {})},
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    message = _jsonrpc_response(response, request_id=1)
    result = message.get("result") if message else None
    if not isinstance(result, dict) or "protocolVersion" not in result:
        return None
    info = result.get("serverInfo") or {}
    return Handshake(
        server_name=str(info.get("name", "")),
        server_version=str(info.get("version", "")),
        protocol_version=str(result["protocolVersion"]),
        session_id=response.headers.get("mcp-session-id"),
    )


def list_tools(
    endpoint: LocalEndpoint, *, headers: Mapping[str, str] | None = None
) -> list[dict[str, Any]]:
    """List every tool the server offers, in the session its handshake opened."""
    session_headers = {
        **_MCP_HEADERS,
        "MCP-Protocol-Version": endpoint.handshake.protocol_version,
        **(headers or {}),
    }
    if endpoint.handshake.session_id:
        session_headers["Mcp-Session-Id"] = endpoint.handshake.session_id

    tools: list[dict[str, Any]] = []
    with httpx.Client(headers=session_headers, timeout=10.0, follow_redirects=True) as client:
        client.post(endpoint.url, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        cursor: str | None = None
        request_id = 2
        while True:
            params = {"cursor": cursor} if cursor else {}
            response = client.post(
                endpoint.url,
                json={"jsonrpc": "2.0", "id": request_id, "method": "tools/list", "params": params},
            )
            message = _jsonrpc_response(response, request_id) if response.is_success else None
            if message is None or "result" not in message:
                detail = message.get("error") if message else f"HTTP {response.status_code}"
                raise StartCommandError(f"The server's tools/list failed: {detail}")
            tools.extend(message["result"].get("tools", []))
            cursor = message["result"].get("nextCursor")
            if not cursor:
                return tools
            request_id += 1


def _jsonrpc_response(response: httpx.Response, request_id: int) -> dict[str, Any] | None:
    """The JSON-RPC response to ``request_id``, from a JSON body or an event stream."""
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for data in _event_stream_data(response.text):
            try:
                message = json.loads(data)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
        return None
    try:
        message = response.json()
    except ValueError:
        return None
    return message if isinstance(message, dict) else None


def _event_stream_data(text: str) -> Iterator[str]:
    """The ``data`` of each server-sent event in ``text``."""
    data: list[str] = []
    for line in [*text.splitlines(), ""]:
        if not line:
            if data:
                yield "\n".join(data)
            data = []
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))

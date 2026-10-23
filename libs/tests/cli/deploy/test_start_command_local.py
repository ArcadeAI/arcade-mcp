"""Running a start command locally and finding its MCP endpoint.

The servers here are stand-ins from ``start_command_servers/fakes`` so these tests need no
network; ``test_start_command_matrix.py`` runs the real frameworks.
"""

import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import psutil
import pytest
from arcade_cli.start_command import (
    StartCommandError,
    list_tools,
    resolve_start_command,
    run_locally,
)

FAKES = Path(__file__).parent / "start_command_servers" / "fakes"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def distinct_free_ports(count: int) -> set[int]:
    ports: set[int] = set()
    while len(ports) < count:
        ports.add(free_port())
    return ports


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for fake in FAKES.glob("*.py"):
        shutil.copy(fake, tmp_path / fake.name)
    return tmp_path


@pytest.fixture
def unrelated_mcp_server(project: Path) -> Iterator[int]:
    """An MCP server on this machine that the start command did not start."""
    port = free_port()
    process = subprocess.Popen(
        [sys.executable, str(project / "fake_mcp.py"), "--port", str(port)], cwd=project
    )
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
                break
            except OSError:
                time.sleep(0.05)
        yield port
    finally:
        process.kill()
        process.wait()


def test_an_sdk_style_server_on_a_non_default_port_is_found(project: Path) -> None:
    port = free_port()
    start = resolve_start_command(project, command=f"python fake_mcp.py --port {port}")

    with run_locally(start, project) as endpoint:
        assert endpoint.port == port
        assert endpoint.path == "/mcp"
        assert endpoint.url == f"http://127.0.0.1:{port}/mcp"
        assert endpoint.handshake.server_name == "fake-mcp"
        assert [tool["name"] for tool in list_tools(endpoint)] == ["echo"]


def test_a_server_on_the_root_path_is_found(project: Path) -> None:
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --port {free_port()} --path /"
    )

    with run_locally(start, project) as endpoint:
        assert endpoint.path == "/"


def test_a_server_mounted_elsewhere_needs_path(project: Path) -> None:
    command = f"python fake_mcp.py --port {free_port()} --path /api/mcp"

    with (
        pytest.raises(StartCommandError, match="answered the MCP handshake on no path"),
        run_locally(resolve_start_command(project, command=command), project, timeout=3),
    ):
        pass

    with run_locally(
        resolve_start_command(project, command=command, path="/api/mcp"), project
    ) as endpoint:
        assert endpoint.path == "/api/mcp"


def test_a_listener_in_a_descendant_process_is_found(project: Path) -> None:
    port = free_port()
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --launcher --port {port}"
    )

    with run_locally(start, project) as endpoint:
        assert endpoint.port == port
        launcher = psutil.Process(endpoint.pid)
        children = launcher.children(recursive=True)
        assert children
        assert not any(conn.status == psutil.CONN_LISTEN for conn in launcher.net_connections())

    assert not any(child.is_running() for child in children)


def test_uvicorn_workers_are_found(project: Path) -> None:
    port = free_port()
    start = resolve_start_command(
        project, command=f"uvicorn asgi_app:app --port {port} --workers 2"
    )

    with run_locally(start, project, timeout=60) as endpoint:
        assert endpoint.port == port
        assert [tool["name"] for tool in list_tools(endpoint)] == ["echo"]


def test_an_event_stream_response_is_read(project: Path) -> None:
    start = resolve_start_command(project, command=f"python fake_mcp.py --port {free_port()} --sse")

    with run_locally(start, project) as endpoint:
        assert endpoint.handshake.session_id == "fake-session"
        assert [tool["name"] for tool in list_tools(endpoint)] == ["echo"]


def test_every_page_of_tools_is_listed(project: Path) -> None:
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --port {free_port()} --tools one,two,three"
    )

    with run_locally(start, project) as endpoint:
        assert [tool["name"] for tool in list_tools(endpoint)] == ["one", "two", "three"]


def test_a_failed_tools_list_is_reported(project: Path) -> None:
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --port {free_port()} --fail-tools-list"
    )

    with (
        run_locally(start, project) as endpoint,
        pytest.raises(StartCommandError, match="tools/list failed.*tools are unavailable"),
    ):
        list_tools(endpoint)


def test_a_web_page_is_not_an_mcp_endpoint(project: Path) -> None:
    # / and /mcp answer 200 with HTML; the MCP endpoint is elsewhere.
    command = f"python fake_mcp.py --port {free_port()} --path /api/mcp --html-elsewhere"

    with (
        pytest.raises(StartCommandError, match="answered the MCP handshake on no path"),
        run_locally(resolve_start_command(project, command=command), project, timeout=3),
    ):
        pass


def test_a_command_that_isnt_installed_is_reported(project: Path) -> None:
    start = resolve_start_command(project, command="no-such-server-command --port 8000")

    with (
        pytest.raises(StartCommandError, match="`no-such-server-command` wasn't found"),
        run_locally(start, project),
    ):
        pass


def test_a_listener_that_is_not_loopback_is_refused(project: Path) -> None:
    port = free_port()
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --port {port} --host 0.0.0.0"
    )

    with pytest.raises(StartCommandError, match=rf"0\.0\.0\.0:{port}"), run_locally(start, project):
        pass


def test_the_listener_that_answers_the_handshake_wins(project: Path) -> None:
    # Owned ports are probed in ascending order, so the decoy is tried first.
    decoy, port = sorted(distinct_free_ports(2))
    start = resolve_start_command(
        project, command=f"python fake_mcp.py --port {port} --decoy-port {decoy}"
    )

    with run_locally(start, project) as endpoint:
        assert endpoint.port == port


@pytest.mark.skipif(not socket.has_ipv6, reason="needs IPv6 loopback")
def test_a_listener_on_ipv6_loopback_only_is_refused(project: Path) -> None:
    port = free_port()
    start = resolve_start_command(project, command=f"python fake_mcp.py --port {port} --host ::1")

    with (
        pytest.raises(StartCommandError, match=rf"\[::1\]:{port}.*127\.0\.0\.1"),
        run_locally(start, project, timeout=3),
    ):
        pass


def test_a_listener_outside_the_process_tree_is_ignored(
    project: Path, unrelated_mcp_server: int
) -> None:
    sleeper = "python -c \"import time; time.sleep(30)\""

    with (
        pytest.raises(StartCommandError, match="listened on no loopback port"),
        run_locally(resolve_start_command(project, command=sleeper), project, timeout=3),
    ):
        pass


def test_a_server_that_exits_is_reported(project: Path) -> None:
    start = resolve_start_command(project, command='python -c "raise SystemExit(3)"')

    with pytest.raises(StartCommandError, match="exited with code 3"), run_locally(start, project):
        pass

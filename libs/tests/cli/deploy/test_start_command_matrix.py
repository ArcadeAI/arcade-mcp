"""The supported frameworks start and list their tools locally.

One fixture per version in ``start_command_servers``. Each gets its own virtual
environment, installed with uv from the fixture's pinned dependencies, so these tests
need uv and access to a package index; deselect them with ``-m "not deploy_matrix"``.
"""

import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from arcade_cli.start_command import FASTMCP_RUN_FLAGS, list_tools, resolve_start_command, run_locally

SERVERS = Path(__file__).parent / "start_command_servers"
UV = shutil.which("uv")

pytestmark = [
    pytest.mark.deploy_matrix,
    pytest.mark.skipif(UV is None, reason="needs uv to build the fixture environments"),
]

_installed: dict[str, Path] = {}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def installed_fixture(name: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy a fixture project and install its dependencies into its own .venv, once per run."""
    assert UV is not None
    if name in _installed:
        return _installed[name]
    project = tmp_path_factory.mktemp(name) / name
    shutil.copytree(SERVERS / name, project)
    venv = project / ".venv"
    subprocess.run([UV, "venv", "--quiet", "--python", sys.executable, str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        [UV, "pip", "install", "--quiet", "--python", str(python), "-r", "pyproject.toml"],
        cwd=project,
        check=True,
        timeout=600,
    )
    _installed[name] = project
    return project


@pytest.mark.parametrize(
    ("fixture", "expected_argv"),
    [
        ("fastmcp_2_14", ("fastmcp", "run", "server.py:mcp", *FASTMCP_RUN_FLAGS)),
        ("fastmcp_3_4", ("fastmcp", "run", "server.py:mcp", *FASTMCP_RUN_FLAGS)),
        ("fastmcp_4_0", ("fastmcp", "run", "server.py:mcp", *FASTMCP_RUN_FLAGS)),
        ("fastmcp_json", ("fastmcp", "run", "fastmcp.json", *FASTMCP_RUN_FLAGS)),
        ("fastmcp_sdk_object", ("fastmcp", "run", "server.py:mcp", *FASTMCP_RUN_FLAGS)),
        ("mcp_sdk_1", ("python", "server.py")),
        ("mcp_sdk_2", ("python", "server.py")),
    ],
)
def test_each_supported_version_starts_and_lists_its_tools(
    fixture: str, expected_argv: tuple[str, ...], tmp_path_factory: pytest.TempPathFactory
) -> None:
    project = installed_fixture(fixture, tmp_path_factory)
    port = free_port()

    start = resolve_start_command(project)
    assert start.argv == expected_argv

    with run_locally(start, project, env={"FIXTURE_PORT": str(port)}, timeout=60) as endpoint:
        if start.port is None:
            assert endpoint.port == port
        assert endpoint.path == "/mcp"
        assert endpoint.handshake.server_name == "echo-server"
        assert [tool["name"] for tool in list_tools(endpoint)] == ["echo"]


def test_an_sdk_server_on_another_port_and_the_root_path_needs_no_configuration(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    project = installed_fixture("mcp_sdk_2_root", tmp_path_factory)
    port = free_port()

    start = resolve_start_command(project)

    with run_locally(start, project, env={"FIXTURE_PORT": str(port)}, timeout=60) as endpoint:
        assert endpoint.port == port
        assert endpoint.path == "/"
        assert [tool["name"] for tool in list_tools(endpoint)] == ["echo"]

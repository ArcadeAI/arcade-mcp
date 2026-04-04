import base64
import io
import socket
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from arcade_cli.deploy import (
    DEPLOY_TIMEOUT_SECONDS,
    create_package_archive,
    deploy_server_logic,
    deploy_server_to_engine,
    discover_entrypoint,
    find_project_root,
    get_required_secrets,
    get_server_info,
    start_server_process,
    update_deployment,
    verify_server_and_get_metadata,
    wait_for_health,
)

# Fixtures


@pytest.fixture
def test_dir() -> Path:
    """Return the path to the test directory."""
    return Path(__file__).parent


@pytest.fixture
def valid_server_dir(test_dir: Path) -> Path:
    """Return the path to the valid server directory (project root)."""
    return test_dir / "test_servers" / "valid_server"


@pytest.fixture
def valid_server_entrypoint() -> str:
    """Return the relative entrypoint path for the valid server."""
    return "server.py"


@pytest.fixture
def invalid_server_dir(test_dir: Path) -> Path:
    """Return the path to the invalid server directory (project root)."""
    return test_dir / "test_servers" / "invalid_server"


@pytest.fixture
def invalid_server_entrypoint() -> str:
    """Return the relative entrypoint path for the invalid server."""
    return "server.py"


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory with pyproject.toml."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create a basic pyproject.toml
    pyproject_content = """[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test_project"
version = "0.1.0"
description = "Test project"
requires-python = ">=3.10"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
    return project_dir


@pytest.fixture
def reserved_unreachable_local_url():
    """Yield a localhost URL that is guaranteed not to have an HTTP listener.

    Keeps a TCP socket bound (without listen()) so no other process can claim
    the port during the test, avoiding flaky collisions with long-lived local
    dev servers.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        yield f"http://127.0.0.1:{port}"


# Tests for create_package_archive


def test_create_package_archive_success(valid_server_dir: Path) -> None:
    """Test creating an archive from a valid directory."""
    archive_base64 = create_package_archive(valid_server_dir)

    # Verify it returns a base64-encoded string
    assert isinstance(archive_base64, str)
    assert len(archive_base64) > 0

    # Decode and verify the archive can be extracted
    archive_bytes = base64.b64decode(archive_base64)
    byte_stream = io.BytesIO(archive_bytes)

    with tarfile.open(fileobj=byte_stream, mode="r:gz") as tar:
        members = tar.getmembers()
        filenames = [m.name for m in members]

        # Verify expected files are present
        assert any("server.py" in name for name in filenames)
        assert any("pyproject.toml" in name for name in filenames)


def test_create_package_archive_nonexistent_dir(tmp_path: Path) -> None:
    """Test that archiving a non-existent directory raises ValueError."""
    nonexistent_dir = tmp_path / "does_not_exist"

    with pytest.raises(ValueError, match="Package directory not found"):
        create_package_archive(nonexistent_dir)


def test_create_package_archive_file_not_dir(tmp_path: Path) -> None:
    """Test that archiving a file instead of directory raises ValueError."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content", encoding="utf-8")

    with pytest.raises(ValueError, match="Package path must be a directory"):
        create_package_archive(test_file)


def test_create_package_archive_excludes_files(tmp_path: Path) -> None:
    """Test that certain files are excluded from the archive."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Create files that should be excluded
    (test_dir / ".hidden").write_text("hidden", encoding="utf-8")
    (test_dir / "__pycache__").mkdir()
    (test_dir / "__pycache__" / "cache.pyc").write_text("cache", encoding="utf-8")
    (test_dir / "requirements.lock").write_text("lock", encoding="utf-8")
    (test_dir / "dist").mkdir()
    (test_dir / "dist" / "package.tar.gz").write_text("dist", encoding="utf-8")
    (test_dir / "build").mkdir()
    (test_dir / "build" / "lib").write_text("build", encoding="utf-8")

    # Create files that should be included
    (test_dir / "main.py").write_text("main", encoding="utf-8")
    (test_dir / "pyproject.toml").write_text("project", encoding="utf-8")

    archive_base64 = create_package_archive(test_dir)
    archive_bytes = base64.b64decode(archive_base64)
    byte_stream = io.BytesIO(archive_bytes)

    with tarfile.open(fileobj=byte_stream, mode="r:gz") as tar:
        members = tar.getmembers()
        filenames = [m.name for m in members]

        # Verify excluded files are not present
        assert not any(".hidden" in name for name in filenames)
        assert not any("__pycache__" in name for name in filenames)
        assert not any(".lock" in name for name in filenames)
        assert not any("dist" in name for name in filenames)
        assert not any("build" in name for name in filenames)

        # Verify included files are present
        assert any("main.py" in name for name in filenames)
        assert any("pyproject.toml" in name for name in filenames)


# Tests for wait_for_health


def test_wait_for_health_success(
    valid_server_entrypoint: str, valid_server_dir: Path, capsys
) -> None:
    """Test waiting for a healthy server."""
    process, port = start_server_process(valid_server_entrypoint, valid_server_dir, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_health(base_url, process, timeout=10)
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_wait_for_health_process_dies(valid_server_entrypoint: str, valid_server_dir: Path) -> None:
    """Test handling when process dies during health check."""
    process, port = start_server_process(valid_server_entrypoint, valid_server_dir, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    # Kill the process immediately
    process.kill()
    process.wait()

    # Mock process object to pass to wait_for_health
    with pytest.raises(ValueError):
        wait_for_health(base_url, process, timeout=2)


# Tests for get_server_info


def test_get_server_info_success(
    valid_server_entrypoint: str, valid_server_dir: Path, capsys
) -> None:
    """Test extracting server info from a running server."""
    process, port = start_server_process(valid_server_entrypoint, valid_server_dir, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Wait for server to be healthy first
        wait_for_health(base_url, process, timeout=10)

        server_name, server_version = get_server_info(base_url)

        assert server_name == "simpleserver"
        assert server_version == "1.0.0"
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_get_server_info_invalid_url(reserved_unreachable_local_url: str) -> None:
    """Test that invalid URL raises ValueError."""
    invalid_url = reserved_unreachable_local_url

    with pytest.raises(ValueError):
        get_server_info(invalid_url)


# Tests for get_required_secrets


def test_get_required_secrets_with_secrets(
    valid_server_entrypoint: str, valid_server_dir: Path, capsys
) -> None:
    """Test extracting required secrets from server tools."""
    process, port = start_server_process(valid_server_entrypoint, valid_server_dir, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Wait for server to be healthy first
        wait_for_health(base_url, process, timeout=10)

        secrets = get_required_secrets(base_url, "simpleserver", "1.0.0", debug=True)
        assert "MY_SECRET_KEY" in secrets
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_get_required_secrets_no_secrets(
    valid_server_entrypoint: str, valid_server_dir: Path
) -> None:
    """Test getting secrets returns set even when checking actual tools."""
    process, port = start_server_process(valid_server_entrypoint, valid_server_dir, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Wait for server to be healthy first
        wait_for_health(base_url, process, timeout=10)

        secrets = get_required_secrets(base_url, "simpleserver", "1.0.0", debug=False)

        assert len(secrets) == 1
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def test_get_required_secrets_invalid_url(reserved_unreachable_local_url: str) -> None:
    """Test that invalid URL raises ValueError."""
    invalid_url = reserved_unreachable_local_url

    with pytest.raises(
        ValueError, match="Failed to extract tool secrets from /worker/tools endpoint"
    ):
        get_required_secrets(invalid_url, "test", "1.0.0")


# Tests for verify_server_and_get_metadata (integration tests)


def test_verify_server_and_get_metadata_success(
    valid_server_entrypoint: str, valid_server_dir: Path, capsys
) -> None:
    """Test full server verification flow."""
    server_name, server_version, required_secrets = verify_server_and_get_metadata(
        valid_server_entrypoint, valid_server_dir, debug=False
    )

    # Verify returned values
    assert server_name == "simpleserver"
    assert server_version == "1.0.0"
    assert "MY_SECRET_KEY" in required_secrets


def test_verify_server_and_get_metadata_with_debug(
    valid_server_entrypoint: str, valid_server_dir: Path, capsys
) -> None:
    """Test server verification with debug mode enabled."""
    server_name, server_version, required_secrets = verify_server_and_get_metadata(
        valid_server_entrypoint, valid_server_dir, debug=True
    )

    # Verify returned values
    assert server_name == "simpleserver"
    assert server_version == "1.0.0"
    assert "MY_SECRET_KEY" in required_secrets


# Tests for deploy_server_to_engine


@patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer test"})
@patch(
    "arcade_cli.deploy.get_org_scoped_url",
    return_value="http://engine/v1/orgs/1/projects/1/deployments",
)
def test_deploy_server_to_engine_timeout_raises_helpful_error(
    mock_url: MagicMock, mock_auth: MagicMock
) -> None:
    """Test that a timeout during deployment raises a clear, actionable error."""
    with patch("arcade_cli.deploy.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.side_effect = httpx.WriteTimeout("The write operation timed out")

        with pytest.raises(ValueError, match="Deployment request timed out"):
            deploy_server_to_engine("http://engine", {"test": "payload"})


@patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer test"})
@patch(
    "arcade_cli.deploy.get_org_scoped_url",
    return_value="http://engine/v1/orgs/1/projects/1/deployments",
)
def test_deploy_server_to_engine_timeout_mentions_package_size(
    mock_url: MagicMock, mock_auth: MagicMock
) -> None:
    """Test that the timeout error message mentions package size as a likely cause."""
    with patch("arcade_cli.deploy.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.side_effect = httpx.ReadTimeout("timed out")

        with pytest.raises(ValueError, match="large deployment package"):
            deploy_server_to_engine("http://engine", {"test": "payload"})


@patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer test"})
@patch(
    "arcade_cli.deploy.get_org_scoped_url",
    return_value="http://engine/v1/orgs/1/projects/1/deployments",
)
def test_deploy_server_to_engine_uses_deploy_timeout(
    mock_url: MagicMock, mock_auth: MagicMock
) -> None:
    """Test that deploy_server_to_engine uses the DEPLOY_TIMEOUT_SECONDS constant."""
    with patch("arcade_cli.deploy.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_client.post.return_value = mock_response

        deploy_server_to_engine("http://engine", {"test": "payload"})

        mock_client_cls.assert_called_once_with(
            headers={"Authorization": "Bearer test"},
            timeout=DEPLOY_TIMEOUT_SECONDS,
        )


# Tests for update_deployment


@patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer test"})
@patch(
    "arcade_cli.deploy.get_org_scoped_url",
    return_value="http://engine/v1/orgs/1/projects/1/deployments/myserver",
)
def test_update_deployment_timeout_raises_helpful_error(
    mock_url: MagicMock, mock_auth: MagicMock
) -> None:
    """Test that a timeout during deployment update raises a clear, actionable error."""
    with patch("arcade_cli.deploy.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.put.side_effect = httpx.WriteTimeout("The write operation timed out")

        with pytest.raises(ValueError, match="Deployment update timed out"):
            update_deployment("http://engine", "myserver", {"test": "payload"})


@patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer test"})
@patch(
    "arcade_cli.deploy.get_org_scoped_url",
    return_value="http://engine/v1/orgs/1/projects/1/deployments/myserver",
)
def test_update_deployment_uses_deploy_timeout(mock_url: MagicMock, mock_auth: MagicMock) -> None:
    """Test that update_deployment uses the DEPLOY_TIMEOUT_SECONDS constant."""
    with patch("arcade_cli.deploy.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        update_deployment("http://engine", "myserver", {"test": "payload"})

        mock_client_cls.assert_called_once_with(
            headers={"Authorization": "Bearer test"},
            timeout=DEPLOY_TIMEOUT_SECONDS,
        )


def test_deploy_timeout_constant() -> None:
    """Test that the deploy timeout constant is correctly defined."""
    assert DEPLOY_TIMEOUT_SECONDS == 360


# ---------------------------------------------------------------------------
# Debug-aware error messages
# ---------------------------------------------------------------------------


@patch("arcade_cli.deploy.find_python_interpreter")
@patch("arcade_cli.deploy.subprocess.Popen")
def test_start_server_process_non_debug_message(
    mock_popen: MagicMock, mock_python: MagicMock, tmp_path: Path
) -> None:
    """Non-debug mode error should hint at --debug flag."""
    mock_python.return_value = Path("python3")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 1  # Process exited immediately
    mock_popen.return_value = mock_proc

    with pytest.raises(ValueError, match="--debug"):
        start_server_process("server.py", tmp_path, debug=False)


@patch("arcade_cli.deploy.find_python_interpreter")
@patch("arcade_cli.deploy.subprocess.Popen")
def test_start_server_process_debug_message(
    mock_popen: MagicMock, mock_python: MagicMock, tmp_path: Path
) -> None:
    """Debug mode error should NOT tell user to run with --debug (already in debug mode)."""
    mock_python.return_value = Path("python3")
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 1  # Process exited immediately
    mock_popen.return_value = mock_proc

    with pytest.raises(ValueError) as exc_info:
        start_server_process("server.py", tmp_path, debug=True)

    msg = str(exc_info.value)
    assert "--debug" not in msg, "Debug mode error must not tell user to re-run with --debug"
    assert "above" in msg.lower() or "output" in msg.lower()


def test_wait_for_health_non_debug_message(reserved_unreachable_local_url: str) -> None:
    """Non-debug health timeout should hint at --debug flag."""
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (None, None)

    with pytest.raises(ValueError, match="--debug"):
        wait_for_health(reserved_unreachable_local_url, mock_proc, timeout=1, debug=False)


def test_wait_for_health_debug_message(reserved_unreachable_local_url: str) -> None:
    """Debug health timeout should NOT tell user to run with --debug,
    and SHOULD reference checking the output already shown above."""
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (None, None)

    with pytest.raises(ValueError) as exc_info:
        wait_for_health(reserved_unreachable_local_url, mock_proc, timeout=1, debug=True)

    msg = str(exc_info.value)
    assert "--debug" not in msg, "Debug mode error must not tell user to re-run with --debug"
    assert "above" in msg.lower() or "output" in msg.lower(), (
        f"Debug mode error should reference checking output above; got: {msg!r}"
    )


# ---------------------------------------------------------------------------
# find_project_root
# ---------------------------------------------------------------------------


def test_find_project_root_in_current_dir(tmp_path: Path) -> None:
    """Finds pyproject.toml in start_dir itself."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert find_project_root(tmp_path) == tmp_path


def test_find_project_root_walks_upward(tmp_path: Path) -> None:
    """Finds pyproject.toml in a parent directory."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    child = tmp_path / "src" / "pkg"
    child.mkdir(parents=True)
    assert find_project_root(child) == tmp_path


def test_find_project_root_respects_max_depth(tmp_path: Path) -> None:
    """Stops searching after MAX_PROJECT_ROOT_SEARCH_DEPTH levels."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    # Create a directory 4 levels deep (depth 0 is start_dir, so 4 parents = beyond limit of 3)
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match=r"pyproject\.toml not found"):
        find_project_root(deep)


def test_find_project_root_not_found(tmp_path: Path) -> None:
    """Raises FileNotFoundError when no pyproject.toml exists."""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match=r"pyproject\.toml not found"):
        find_project_root(empty)


# ---------------------------------------------------------------------------
# discover_entrypoint
# ---------------------------------------------------------------------------


def _make_pyproject(directory: Path, name: str = "my-server") -> None:
    """Helper to create a minimal pyproject.toml."""
    (directory / "pyproject.toml").write_text(
        f"[project]\nname = '{name}'\nversion = '0.1.0'\n"
    )


def test_discover_entrypoint_server_py_at_root(tmp_path: Path) -> None:
    """Finds server.py at project root (flat layout)."""
    _make_pyproject(tmp_path)
    (tmp_path / "server.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "server.py"


def test_discover_entrypoint_src_layout(tmp_path: Path) -> None:
    """Finds src/<pkg>/server.py (arcade new minimal layout)."""
    _make_pyproject(tmp_path, name="my-server")
    pkg_dir = tmp_path / "src" / "my_server"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "server.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "src/my_server/server.py"


def test_discover_entrypoint_flat_pkg_layout(tmp_path: Path) -> None:
    """Finds <pkg>/server.py (flat package layout without src/)."""
    _make_pyproject(tmp_path, name="my-server")
    pkg_dir = tmp_path / "my_server"
    pkg_dir.mkdir()
    (pkg_dir / "server.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "my_server/server.py"


def test_discover_entrypoint_dunder_main(tmp_path: Path) -> None:
    """Finds <pkg>/__main__.py (arcade new --full layout)."""
    _make_pyproject(tmp_path, name="my-server")
    pkg_dir = tmp_path / "my_server"
    pkg_dir.mkdir()
    (pkg_dir / "__main__.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "my_server/__main__.py"


def test_discover_entrypoint_app_py_fallback(tmp_path: Path) -> None:
    """Falls back to app.py when no other candidate exists."""
    _make_pyproject(tmp_path)
    (tmp_path / "app.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "app.py"


def test_discover_entrypoint_main_py_not_a_candidate(tmp_path: Path) -> None:
    """main.py is NOT treated as an entrypoint candidate (too ambiguous)."""
    _make_pyproject(tmp_path)
    (tmp_path / "main.py").write_text("# not an entrypoint")
    with pytest.raises(FileNotFoundError, match="Could not find an entrypoint"):
        discover_entrypoint(tmp_path)


def test_discover_entrypoint_prefers_server_py_over_src(tmp_path: Path) -> None:
    """server.py at root takes priority over src/<pkg>/server.py."""
    _make_pyproject(tmp_path, name="my-server")
    (tmp_path / "server.py").write_text("# root entrypoint")
    pkg_dir = tmp_path / "src" / "my_server"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "server.py").write_text("# src entrypoint")
    assert discover_entrypoint(tmp_path) == "server.py"


def test_discover_entrypoint_none_found(tmp_path: Path) -> None:
    """Raises FileNotFoundError when no candidate exists."""
    _make_pyproject(tmp_path)
    with pytest.raises(FileNotFoundError, match="Could not find an entrypoint"):
        discover_entrypoint(tmp_path)


def test_discover_entrypoint_hyphen_to_underscore(tmp_path: Path) -> None:
    """Project names with hyphens are normalized to underscores for path lookup."""
    _make_pyproject(tmp_path, name="my-cool-server")
    pkg_dir = tmp_path / "src" / "my_cool_server"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "server.py").write_text("# entrypoint")
    assert discover_entrypoint(tmp_path) == "src/my_cool_server/server.py"


def test_discover_entrypoint_warns_when_no_project_name(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Logs a warning when pyproject.toml has no [project].name."""
    # pyproject.toml without [project].name
    (tmp_path / "pyproject.toml").write_text("[build-system]\nrequires = ['hatchling']\n")
    (tmp_path / "server.py").write_text("# entrypoint")

    import logging

    with caplog.at_level(logging.WARNING, logger="arcade_cli.deploy"):
        result = discover_entrypoint(tmp_path)

    assert result == "server.py"
    assert "Could not read [project].name" in caplog.text


# ---------------------------------------------------------------------------
# deploy_server_logic — .py positional arg detection
# ---------------------------------------------------------------------------


@patch("arcade_cli.deploy.validate_and_get_config")
def test_deploy_server_logic_rejects_nonexistent_project_dir(mock_config: MagicMock) -> None:
    """Passing a non-existent directory as project_dir raises FileNotFoundError."""
    mock_config.return_value = MagicMock(user=MagicMock(email="test@test.com"))

    with pytest.raises(FileNotFoundError, match="Project directory not found"):
        deploy_server_logic(
            entrypoint=None,
            project_dir="/nonexistent_path_for_test",
            skip_validate=False,
            server_name=None,
            server_version=None,
            secrets="auto",
            host="localhost",
            port=None,
            force_tls=False,
            force_no_tls=False,
            debug=False,
        )


@patch("arcade_cli.deploy.validate_and_get_config")
def test_deploy_server_logic_rejects_py_as_project_dir(mock_config: MagicMock) -> None:
    """Passing a .py file as the positional arg raises a helpful error."""
    mock_config.return_value = MagicMock(user=MagicMock(email="test@test.com"))

    with pytest.raises(FileNotFoundError, match=r"looks like a Python file"):
        deploy_server_logic(
            entrypoint=None,
            project_dir="src/server.py",
            skip_validate=False,
            server_name=None,
            server_version=None,
            secrets="auto",
            host="localhost",
            port=None,
            force_tls=False,
            force_no_tls=False,
            debug=False,
        )


# ---------------------------------------------------------------------------
# deploy_server_logic — .env search uses project_root
# ---------------------------------------------------------------------------


@patch("arcade_cli.deploy.verify_server_and_get_metadata")
@patch("arcade_cli.deploy.find_env_file")
@patch("arcade_cli.deploy.validate_and_get_config")
def test_deploy_env_file_searched_from_project_root(
    mock_config: MagicMock,
    mock_find_env: MagicMock,
    mock_verify: MagicMock,
    tmp_path: Path,
) -> None:
    """find_env_file is called with start_dir=project_root, not CWD."""
    # Set up a project dir that is NOT the CWD
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    _make_pyproject(project_dir, name="my-project")
    (project_dir / "server.py").write_text("# entrypoint")

    mock_config.return_value = MagicMock(user=MagicMock(email="test@test.com"))
    mock_find_env.return_value = None
    mock_verify.side_effect = Exception("stop early")

    with pytest.raises(ValueError, match="Server verification failed"):
        deploy_server_logic(
            entrypoint=None,
            project_dir=str(project_dir),
            skip_validate=False,
            server_name=None,
            server_version=None,
            secrets="auto",
            host="localhost",
            port=None,
            force_tls=False,
            force_no_tls=False,
            debug=False,
        )

    # The key assertion: find_env_file was called with the project root, not CWD
    mock_find_env.assert_called_once_with(start_dir=project_dir)

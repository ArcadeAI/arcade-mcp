import base64
import io
import subprocess
import tarfile
from pathlib import Path

import pytest
from arcade_cli.deploy import (
    create_package_archive,
    get_required_secrets,
    get_server_info,
    start_server_process,
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
    """Return the path to the valid server directory."""
    return test_dir / "test_servers" / "valid_server"


@pytest.fixture
def valid_server_path(valid_server_dir: Path) -> str:
    """Return the path to the valid server entrypoint."""
    return str(valid_server_dir / "server.py")


@pytest.fixture
def invalid_server_path(test_dir: Path) -> str:
    """Return the path to the invalid server entrypoint."""
    return str(test_dir / "test_servers" / "invalid_server" / "server.py")


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
    (project_dir / "pyproject.toml").write_text(pyproject_content)
    return project_dir


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
    test_file.write_text("test content")

    with pytest.raises(ValueError, match="Package path must be a directory"):
        create_package_archive(test_file)


def test_create_package_archive_excludes_files(tmp_path: Path) -> None:
    """Test that certain files are excluded from the archive."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Create files that should be excluded
    (test_dir / ".hidden").write_text("hidden")
    (test_dir / "__pycache__").mkdir()
    (test_dir / "__pycache__" / "cache.pyc").write_text("cache")
    (test_dir / "requirements.lock").write_text("lock")
    (test_dir / "dist").mkdir()
    (test_dir / "dist" / "package.tar.gz").write_text("dist")
    (test_dir / "build").mkdir()
    (test_dir / "build" / "lib").write_text("build")

    # Create files that should be included
    (test_dir / "main.py").write_text("main")
    (test_dir / "pyproject.toml").write_text("project")

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


def test_wait_for_health_success(valid_server_path: str, capsys) -> None:
    """Test waiting for a healthy server."""
    process, port = start_server_process(valid_server_path, debug=False)
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


def test_wait_for_health_process_dies(valid_server_path: str) -> None:
    """Test handling when process dies during health check."""
    process, port = start_server_process(valid_server_path, debug=False)
    base_url = f"http://127.0.0.1:{port}"

    # Kill the process immediately
    process.kill()
    process.wait()

    # Mock process object to pass to wait_for_health
    with pytest.raises(ValueError):
        wait_for_health(base_url, process, timeout=2)


# Tests for get_server_info


def test_get_server_info_success(valid_server_path: str, capsys) -> None:
    """Test extracting server info from a running server."""
    process, port = start_server_process(valid_server_path, debug=False)
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


def test_get_server_info_invalid_url() -> None:
    """Test that invalid URL raises ValueError."""
    invalid_url = "http://127.0.0.1:9999"

    with pytest.raises(ValueError):
        get_server_info(invalid_url)


# Tests for get_required_secrets


def test_get_required_secrets_with_secrets(valid_server_path: str, capsys) -> None:
    """Test extracting required secrets from server tools."""
    process, port = start_server_process(valid_server_path, debug=False)
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


def test_get_required_secrets_no_secrets(valid_server_path: str) -> None:
    """Test getting secrets returns set even when checking actual tools."""
    process, port = start_server_process(valid_server_path, debug=False)
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


def test_get_required_secrets_invalid_url() -> None:
    """Test that invalid URL raises ValueError."""
    invalid_url = "http://127.0.0.1:9999"

    with pytest.raises(
        ValueError, match="Failed to extract tool secrets from /worker/tools endpoint"
    ):
        get_required_secrets(invalid_url, "test", "1.0.0")


# Tests for verify_server_and_get_metadata (integration tests)


def test_verify_server_and_get_metadata_success(valid_server_path: str, capsys) -> None:
    """Test full server verification flow."""
    server_name, server_version, required_secrets = verify_server_and_get_metadata(
        valid_server_path, debug=False
    )

    # Verify returned values
    assert server_name == "simpleserver"
    assert server_version == "1.0.0"
    assert "MY_SECRET_KEY" in required_secrets


def test_verify_server_and_get_metadata_with_debug(valid_server_path: str, capsys) -> None:
    """Test server verification with debug mode enabled."""
    server_name, server_version, required_secrets = verify_server_and_get_metadata(
        valid_server_path, debug=True
    )

    # Verify returned values
    assert server_name == "simpleserver"
    assert server_version == "1.0.0"
    assert "MY_SECRET_KEY" in required_secrets

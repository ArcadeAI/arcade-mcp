"""Tests for find_env_file() upward directory traversal."""

from pathlib import Path

import pytest
from arcade_mcp_server.settings import find_env_file


class TestFindEnvFile:
    """Test the find_env_file() utility function."""

    def test_finds_env_in_current_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should find .env file in cwd."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=value")
        monkeypatch.chdir(tmp_path)

        assert find_env_file() == env_file

    def test_finds_env_in_parent_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should traverse upward to find .env in parent."""
        subdir = tmp_path / "a" / "b" / "c"
        subdir.mkdir(parents=True)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=value")
        monkeypatch.chdir(subdir)

        assert find_env_file() == env_file

    def test_prefers_closest_env_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should find closest .env when multiple exist."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / ".env").write_text("ROOT=1")
        closer_env = subdir / ".env"
        closer_env.write_text("CLOSER=1")
        monkeypatch.chdir(subdir)

        assert find_env_file() == closer_env

    def test_returns_none_when_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return None when no .env exists."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        assert find_env_file() is None

    def test_stop_at_limits_traversal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stop_at should prevent traversing past specified directory."""
        project = tmp_path / "project" / "src"
        project.mkdir(parents=True)
        (tmp_path / ".env").write_text("OUTSIDE=1")
        monkeypatch.chdir(project)

        assert find_env_file(stop_at=tmp_path / "project") is None

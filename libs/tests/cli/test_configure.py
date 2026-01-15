"""Tests for get_tool_secrets() in arcade configure."""

from pathlib import Path

import pytest
from arcade_cli.configure import get_tool_secrets


def test_get_tool_secrets_loads_from_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should load secrets from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_ONE=value1\nSECRET_TWO=value2")
    monkeypatch.chdir(tmp_path)

    secrets = get_tool_secrets()
    assert secrets.get("SECRET_ONE") == "value1"
    assert secrets.get("SECRET_TWO") == "value2"


def test_get_tool_secrets_returns_empty_when_no_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should return empty dict when no .env exists."""
    monkeypatch.chdir(tmp_path)

    assert get_tool_secrets() == {}

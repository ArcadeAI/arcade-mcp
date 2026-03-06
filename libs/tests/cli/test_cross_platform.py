"""Focused cross-platform regression tests with minimal duplication.

This module keeps only scenarios that are not already covered by dedicated
test files under ``libs/tests/cli``.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest


class TestUtf8FileIO:
    """Verify UTF-8 behavior across file I/O paths that have regressed before."""

    def test_config_model_save_uses_utf8(self, tmp_path: Path) -> None:
        from arcade_core.config_model import Config

        config_dir = tmp_path / ".arcade"
        config_dir.mkdir()

        with (
            patch.object(
                Config,
                "get_config_file_path",
                return_value=config_dir / "credentials.yaml",
            ),
            patch.object(Config, "ensure_config_dir_exists"),
        ):
            cfg = Config(coordinator_url="https://café-coordinator.example.com")
            cfg.save_to_file()

        raw = (config_dir / "credentials.yaml").read_bytes()
        text = raw.decode("utf-8")
        assert "caf" in text
        assert "é" in text or "\\xe9" not in text

    def test_config_model_load_reads_utf8(self, tmp_path: Path) -> None:
        import yaml
        from arcade_core.config_model import Config

        config_dir = tmp_path / ".arcade"
        config_dir.mkdir()
        config_file = config_dir / "credentials.yaml"

        data = {"cloud": {"coordinator_url": "https://café.example.com"}}
        config_file.write_text(yaml.dump(data), encoding="utf-8")

        with (
            patch.object(Config, "get_config_file_path", return_value=config_file),
            patch.object(Config, "ensure_config_dir_exists"),
        ):
            loaded = Config.load_from_file()

        assert loaded.coordinator_url == "https://café.example.com"

    def test_config_model_permissions_no_crash_on_windows(self, tmp_path: Path) -> None:
        from arcade_core.config_model import Config

        config_dir = tmp_path / ".arcade"
        config_dir.mkdir()
        config_file = config_dir / "credentials.yaml"

        with (
            patch.object(Config, "get_config_file_path", return_value=config_file),
            patch.object(Config, "ensure_config_dir_exists"),
            patch("arcade_core.config_model.os.name", "nt"),
            patch("arcade_core.config_model.subprocess.run", side_effect=OSError("icacls failed")),
        ):
            cfg = Config(coordinator_url="https://test.example.com")
            cfg.save_to_file()

        assert config_file.exists()

    def test_configure_client_writes_utf8(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from arcade_cli.configure import configure_client

        monkeypatch.chdir(tmp_path)
        entrypoint = tmp_path / "server.py"
        entrypoint.write_text("print('ok')\n", encoding="utf-8")

        config_path = tmp_path / "test_config.json"
        configure_client(
            client="cursor",
            entrypoint_file="server.py",
            server_name="café-server",
            transport="stdio",
            host="local",
            port=8000,
            config_path=config_path,
        )

        raw = config_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8")
        data = json.loads(text)
        assert "café-server" in data["mcpServers"]

    def test_load_env_file_reads_utf8(self, tmp_path: Path) -> None:
        from arcade_cli.secret import load_env_file

        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=café\nKEY2=naïve\n", encoding="utf-8")

        secrets = load_env_file(str(env_file))
        assert secrets["KEY1"] == "café"
        assert secrets["KEY2"] == "naïve"

    def test_identity_write_atomic_uses_utf8(self, tmp_path: Path) -> None:
        from arcade_core.usage.identity import UsageIdentity

        config_path = tmp_path / ".arcade"
        config_path.mkdir()

        with patch("arcade_core.usage.identity.ARCADE_CONFIG_PATH", str(config_path)):
            identity = UsageIdentity()
            identity.usage_file_path = str(config_path / "usage.json")
            identity._write_atomic({"anon_id": "test-ñ-123", "linked_principal_id": None})

        raw = (config_path / "usage.json").read_bytes()
        text = raw.decode("utf-8")
        data = json.loads(text)
        assert data["anon_id"] == "test-ñ-123"

    def test_utils_load_dotenv_reads_utf8(self, tmp_path: Path) -> None:
        from arcade_cli.utils import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("DB_PASSWORD=pässwörd\n", encoding="utf-8")

        result = load_dotenv(env_file, override=False)
        assert result.get("DB_PASSWORD") == "pässwörd"

    def test_new_toolkit_files_are_utf8(self, tmp_path: Path) -> None:
        from arcade_cli.new import create_new_toolkit_minimal

        output_dir = tmp_path / "scaffolded"
        output_dir.mkdir()
        create_new_toolkit_minimal(str(output_dir), "my_server")

        server_py = output_dir / "my_server" / "src" / "my_server" / "server.py"
        assert server_py.exists()
        content = server_py.read_bytes().decode("utf-8")
        assert len(content) > 0


class TestFileLockingErrorHandling:
    """Verify graceful handling for Windows-style file-locking scenarios."""

    def test_logout_handles_permission_error(self) -> None:
        with (
            patch("arcade_cli.main.os.path.exists", return_value=True),
            patch("arcade_cli.main.os.remove", side_effect=PermissionError("Locked")),
            patch("arcade_cli.main.handle_cli_error") as mock_error,
        ):
            from arcade_cli.main import logout

            try:
                logout(debug=False)
            except SystemExit:
                pass

            mock_error.assert_called_once()
            message = mock_error.call_args[0][0].lower()
            assert "in use" in message or "lock" in message

    def test_logout_permission_error_does_not_double_report(self) -> None:
        from arcade_cli.utils import CLIError

        with (
            patch("arcade_cli.main.os.path.exists", return_value=True),
            patch("arcade_cli.main.os.remove", side_effect=PermissionError("Locked")),
            patch("arcade_cli.main.handle_cli_error", side_effect=CLIError("locked")) as mock_error,
        ):
            from arcade_cli.main import logout

            with pytest.raises(CLIError):
                logout(debug=False)

        mock_error.assert_called_once()

    def test_remove_toolkit_handles_permission_error(self, tmp_path: Path) -> None:
        from arcade_cli.new import remove_toolkit
        from rich.console import Console

        toolkit_path = tmp_path / "locked_toolkit"
        toolkit_path.mkdir()
        (toolkit_path / "file.py").write_text("x", encoding="utf-8")

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False)

        import arcade_cli.new as new_mod

        original_console = new_mod.console
        new_mod.console = test_console

        try:
            with patch("arcade_cli.new.shutil.rmtree", side_effect=PermissionError("Locked")):
                remove_toolkit(tmp_path, "locked_toolkit")
        finally:
            new_mod.console = original_console

        output = buf.getvalue()
        assert "Warning" in output or "Could not" in output

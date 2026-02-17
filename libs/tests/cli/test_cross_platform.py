"""Comprehensive cross-platform tests for Windows/Unix compatibility.

This file systematically tests every fix applied for Windows compatibility:
  1. UTF-8 encoding on all file I/O (read_text, write_text, open)
  2. Subprocess CREATE_NO_WINDOW flags
  3. Console encoding safety (UnicodeEncodeError prevention)
  4. Browser opening without CMD flash
  5. File locking error handling (os.remove, shutil.rmtree)
  6. Config model UTF-8 + chmod safety
  7. Path formatting for display
  8. OAuth callback loopback binding
  9. Signal handling logging level

All tests run on BOTH Unix and Windows — platform-specific behaviour is
tested by mocking ``sys.platform``.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# 1. UTF-8 ENCODING — file I/O
# =========================================================================


class TestUtf8FileIO:
    """Verify all config and credential I/O uses explicit UTF-8 encoding."""

    # --- config_model.py ---

    def test_config_model_save_uses_utf8(self, tmp_path: Path) -> None:
        """Config.save_to_file must write UTF-8, not the system default."""
        from arcade_core.config_model import Config

        config_dir = tmp_path / ".arcade"
        config_dir.mkdir()

        with patch.object(Config, "get_config_file_path", return_value=config_dir / "credentials.yaml"):
            with patch.object(Config, "ensure_config_dir_exists"):
                cfg = Config(coordinator_url="https://café-coordinator.example.com")
                cfg.save_to_file()

        raw = (config_dir / "credentials.yaml").read_bytes()
        text = raw.decode("utf-8")
        assert "caf" in text
        assert "é" in text or "\\xe9" not in text  # Must be valid UTF-8

    def test_config_model_load_reads_utf8(self, tmp_path: Path) -> None:
        """Config.load_from_file must read UTF-8 even on cp1252-default systems."""
        import yaml
        from arcade_core.config_model import Config

        config_dir = tmp_path / ".arcade"
        config_dir.mkdir()
        config_file = config_dir / "credentials.yaml"

        data = {"cloud": {"coordinator_url": "https://café.example.com"}}
        config_file.write_text(yaml.dump(data), encoding="utf-8")

        with patch.object(Config, "get_config_file_path", return_value=config_file):
            with patch.object(Config, "ensure_config_dir_exists"):
                loaded = Config.load_from_file()

        assert loaded.coordinator_url == "https://café.example.com"

    def test_config_model_permissions_no_crash_on_windows(self, tmp_path: Path) -> None:
        """Windows ACL hardening should be best-effort and not crash saves."""
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
            # Should NOT raise
            cfg.save_to_file()

        assert config_file.exists()

    # --- configure.py ---

    def test_configure_client_writes_utf8(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """configure_client must produce valid UTF-8 JSON config files."""
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
        assert not raw.startswith(b"\xef\xbb\xbf"), "No UTF-8 BOM"
        text = raw.decode("utf-8")
        data = json.loads(text)
        assert "café-server" in data["mcpServers"]

    # --- secret.py ---

    def test_load_env_file_reads_utf8(self, tmp_path: Path) -> None:
        """load_env_file must handle UTF-8 content in .env files."""
        from arcade_cli.secret import load_env_file

        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=café\nKEY2=naïve\n", encoding="utf-8")

        secrets = load_env_file(str(env_file))
        assert secrets["KEY1"] == "café"
        assert secrets["KEY2"] == "naïve"

    # --- identity.py ---

    def test_identity_write_atomic_uses_utf8(self, tmp_path: Path) -> None:
        """UsageIdentity._write_atomic must write UTF-8 JSON."""
        from arcade_core.usage.identity import UsageIdentity

        config_path = tmp_path / ".arcade"
        config_path.mkdir()

        with patch("arcade_core.usage.identity.ARCADE_CONFIG_PATH", str(config_path)):
            identity = UsageIdentity()
            identity.usage_file_path = str(config_path / "usage.json")
            data = {"anon_id": "test-ñ-123", "linked_principal_id": None}
            identity._write_atomic(data)

        raw = (config_path / "usage.json").read_bytes()
        text = raw.decode("utf-8")  # Must not raise — file is valid UTF-8
        data = json.loads(text)
        assert data["anon_id"] == "test-ñ-123"

    # --- utils.py ---

    def test_utils_load_dotenv_reads_utf8(self, tmp_path: Path) -> None:
        """utils.load_dotenv must use encoding='utf-8'."""
        from arcade_cli.utils import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("DB_PASSWORD=pässwörd\n", encoding="utf-8")

        result = load_dotenv(env_file, override=False)
        assert result.get("DB_PASSWORD") == "pässwörd"

    # --- new.py write_template ---

    def test_new_toolkit_files_are_utf8(self, tmp_path: Path) -> None:
        """Scaffolded toolkit files must be valid UTF-8."""
        from arcade_cli.new import create_new_toolkit_minimal

        output_dir = tmp_path / "scaffolded"
        output_dir.mkdir()
        create_new_toolkit_minimal(str(output_dir), "my_server")

        server_py = output_dir / "my_server" / "src" / "my_server" / "server.py"
        assert server_py.exists()
        content = server_py.read_bytes().decode("utf-8")
        assert len(content) > 0


# =========================================================================
# 2. SUBPROCESS CREATE_NO_WINDOW FLAGS
# =========================================================================


class TestSubprocessFlags:
    """Verify that background subprocess calls use CREATE_NO_WINDOW on Windows."""

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_deploy_start_server_sets_flag_on_win32(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        mock_python.return_value = Path("python.exe")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        # On non-Windows, these constants don't exist; patch subprocess
        create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        create_new_pg = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

        with patch.object(sys, "platform", "win32"):
            with patch.object(
                subprocess, "CREATE_NO_WINDOW", create_no_window, create=True
            ), patch.object(
                subprocess, "CREATE_NEW_PROCESS_GROUP", create_new_pg, create=True
            ):
                from arcade_cli.deploy import start_server_process
                start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        flags = kwargs.get("creationflags", 0)
        assert flags & create_no_window
        assert flags & create_new_pg

    @patch("arcade_cli.deploy.find_python_interpreter")
    @patch("arcade_cli.deploy.subprocess.Popen")
    def test_deploy_start_server_no_flag_on_linux(
        self, mock_popen: MagicMock, mock_python: MagicMock
    ) -> None:
        mock_python.return_value = Path("python3")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        with patch.object(sys, "platform", "linux"):
            from arcade_cli.deploy import start_server_process
            start_server_process("server.py")

        _, kwargs = mock_popen.call_args
        assert kwargs.get("creationflags") == 0

    def test_mcp_app_source_has_create_no_window(self) -> None:
        """mcp_app.py source must contain CREATE_NO_WINDOW guard."""
        import inspect
        import arcade_mcp_server.mcp_app as mcp_mod

        source = inspect.getsource(mcp_mod)
        assert "CREATE_NO_WINDOW" in source
        assert 'sys.platform == "win32"' in source or "sys.platform == 'win32'" in source

    def test_usage_service_uses_hidden_background_flags_on_windows(self) -> None:
        """usage_service.py must hide windows for background tracking on Windows."""
        import inspect
        import arcade_core.usage.usage_service as us_mod

        source = inspect.getsource(us_mod)
        assert "CREATE_NEW_PROCESS_GROUP" in source
        assert "CREATE_NO_WINDOW" in source
        assert "SW_HIDE" in source
        assert 'sys.platform == "win32"' in source or "sys.platform == 'win32'" in source

    def test_config_model_uses_icacls_on_windows(self) -> None:
        """config_model should use icacls for Windows ACL hardening."""
        import inspect
        import arcade_core.config_model as config_model_mod

        source = inspect.getsource(config_model_mod)
        assert "icacls" in source
        assert "os.name == \"nt\"" in source or "os.name == 'nt'" in source


# =========================================================================
# 3. CONSOLE ENCODING SAFETY
# =========================================================================


class TestConsoleEncoding:
    """Verify console encoding reconfiguration logic works cross-platform."""

    from arcade_cli.console import _configure_windows_utf8, _needs_utf8

    @pytest.mark.parametrize(
        "encoding, expected",
        [
            ("utf-8", False),
            ("UTF-8", False),
            ("utf8", False),
            ("cp1252", True),
            ("ascii", True),
            ("latin-1", True),
            ("", True),
            (None, True),
        ],
    )
    def test_needs_utf8(self, encoding: str | None, expected: bool) -> None:
        from arcade_cli.console import _needs_utf8
        assert _needs_utf8(encoding) is expected

    def test_noop_on_non_windows(self) -> None:
        from arcade_cli.console import _configure_windows_utf8
        with patch.object(sys, "platform", "linux"):
            _configure_windows_utf8()  # Should not raise

    def test_reconfigures_cp1252_on_win32(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
        ):
            _configure_windows_utf8()
            assert fake_stdout.encoding.lower().replace("-", "") == "utf8"
            assert fake_stderr.encoding.lower().replace("-", "") == "utf8"

    def test_sets_pythonioencoding(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        env_copy = os.environ.copy()
        env_copy.pop("PYTHONIOENCODING", None)

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
            patch.dict(os.environ, env_copy, clear=True),
        ):
            _configure_windows_utf8()
            assert os.environ.get("PYTHONIOENCODING") == "utf-8"

    def test_does_not_overwrite_existing_pythonioencoding(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
            patch.dict(os.environ, {"PYTHONIOENCODING": "ascii"}, clear=False),
        ):
            _configure_windows_utf8()
            assert os.environ["PYTHONIOENCODING"] == "ascii"

    def test_no_crash_without_reconfigure(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        class FakeStream:
            encoding = "cp1252"

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", FakeStream()),
            patch.object(sys, "stderr", FakeStream()),
        ):
            _configure_windows_utf8()  # Should not raise

    def test_noop_when_already_utf8(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        reconfigure_called = False
        original_reconfigure = fake_stdout.reconfigure

        def tracking_reconfigure(**kwargs):
            nonlocal reconfigure_called
            reconfigure_called = True
            return original_reconfigure(**kwargs)

        fake_stdout.reconfigure = tracking_reconfigure  # type: ignore[assignment]

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
        ):
            _configure_windows_utf8()
            assert not reconfigure_called

    def test_emoji_output_after_reconfigure(self) -> None:
        from arcade_cli.console import _configure_windows_utf8

        buf = io.BytesIO()
        fake_stdout = io.TextIOWrapper(buf, encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stdout),
        ):
            _configure_windows_utf8()
            fake_stdout.write("Hello! ✅ 🚀 Done.\n")
            fake_stdout.flush()

        output = buf.getvalue().decode("utf-8")
        assert "✅" in output
        assert "🚀" in output


# =========================================================================
# 4. BROWSER OPENING — _open_browser
# =========================================================================


class TestOpenBrowser:
    """Tests for _open_browser on both platforms.

    On Windows, the priority order is:
      1. ctypes ShellExecuteW
      2. rundll32 url.dll
      3. os.startfile
      4. webbrowser.open
    """

    def test_uses_webbrowser_on_linux(self) -> None:
        from arcade_cli.authn import _open_browser

        with (
            patch.object(sys, "platform", "linux"),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.return_value = True
            result = _open_browser("https://example.com")
            assert result is True
            mock_wb.open.assert_called_once_with("https://example.com")

    def test_uses_webbrowser_on_darwin(self) -> None:
        from arcade_cli.authn import _open_browser

        with (
            patch.object(sys, "platform", "darwin"),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.return_value = True
            assert _open_browser("https://example.com") is True

    def test_tries_ctypes_shellexecute_first_on_win32(self) -> None:
        """On Windows, attempt 1 is ctypes ShellExecuteW."""
        from arcade_cli.authn import _open_browser

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW.return_value = 42  # >32 = success

        with (
            patch.object(sys, "platform", "win32"),
            patch.dict("sys.modules", {"ctypes": MagicMock()}),
            patch("ctypes.windll.shell32", mock_shell32, create=True),
        ):
            # Need to re-import ctypes in the function scope
            import ctypes
            ctypes.windll = MagicMock()
            ctypes.windll.shell32.ShellExecuteW.return_value = 42

            assert _open_browser("https://example.com") is True

    def test_falls_back_to_rundll32_on_win32(self) -> None:
        """If ctypes fails, attempt 2 is rundll32 url.dll."""
        from arcade_cli.authn import _open_browser

        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen") as mock_popen,
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True) as mock_si_cls,
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", subprocess.DEVNULL),
        ):
            mock_si = MagicMock()
            mock_si.dwFlags = 0
            mock_si_cls.return_value = mock_si
            mock_popen.return_value = MagicMock()

            assert _open_browser("https://example.com") is True
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            assert cmd[0] == "rundll32"
            assert "url.dll,FileProtocolHandler" in cmd[1]

    def test_falls_back_to_startfile_on_win32(self) -> None:
        """If both ctypes and rundll32 fail, attempt 3 is os.startfile."""
        from arcade_cli.authn import _open_browser

        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen", side_effect=Exception("popen failed")),
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True, return_value=MagicMock()),
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", -1),
            patch("arcade_cli.authn.os.startfile", create=True) as mock_sf,
        ):
            assert _open_browser("https://example.com") is True
            mock_sf.assert_called_once_with("https://example.com")

    def test_falls_back_to_webbrowser_on_win32_when_all_else_fails(self) -> None:
        """If ctypes, rundll32, and startfile all fail, use webbrowser.open."""
        from arcade_cli.authn import _open_browser

        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen", side_effect=Exception("fail")),
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True, return_value=MagicMock()),
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", -1),
            patch("arcade_cli.authn.os.startfile", side_effect=OSError, create=True),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.return_value = True
            assert _open_browser("https://example.com") is True
            mock_wb.open.assert_called_once()

    def test_returns_false_when_everything_fails(self) -> None:
        from arcade_cli.authn import _open_browser

        with (
            patch.object(sys, "platform", "linux"),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.side_effect = Exception("no browser")
            assert _open_browser("https://example.com") is False


# =========================================================================
# 5. FILE LOCKING ERROR HANDLING
# =========================================================================


class TestFileLockingErrorHandling:
    """Verify graceful handling of Windows file-locking errors."""

    def test_logout_handles_permission_error(self) -> None:
        """arcade logout should not crash if credentials file is locked."""
        with (
            patch("arcade_cli.main.os.path.exists", return_value=True),
            patch("arcade_cli.main.os.remove", side_effect=PermissionError("Locked")),
            patch("arcade_cli.main.handle_cli_error") as mock_error,
        ):
            from arcade_cli.main import logout
            # Call the underlying function (not the Typer command).
            # logout is wrapped by Typer, but the core logic is testable.
            try:
                logout(debug=False)
            except SystemExit:
                pass  # Typer may exit
            # Verify the error handler was called instead of crashing.
            mock_error.assert_called_once()
            assert "in use" in mock_error.call_args[0][0].lower() or "lock" in mock_error.call_args[0][0].lower()

    def test_remove_toolkit_handles_permission_error(self, tmp_path: Path) -> None:
        """remove_toolkit should warn (not crash) if directory is locked."""
        from arcade_cli.new import remove_toolkit

        toolkit_path = tmp_path / "locked_toolkit"
        toolkit_path.mkdir()
        (toolkit_path / "file.py").write_text("x", encoding="utf-8")

        buf = StringIO()
        from rich.console import Console
        test_console = Console(file=buf, force_terminal=False)

        import arcade_cli.new as new_mod
        orig = new_mod.console
        new_mod.console = test_console

        try:
            with patch("arcade_cli.new.shutil.rmtree", side_effect=PermissionError("Locked")):
                remove_toolkit(tmp_path, "locked_toolkit")
        finally:
            new_mod.console = orig

        output = buf.getvalue()
        assert "Warning" in output or "Could not" in output


# =========================================================================
# 6. PATH FORMATTING FOR DISPLAY
# =========================================================================


class TestPathFormatting:
    """Verify _format_path_for_display handles spaces correctly on all platforms."""

    def test_windows_quotes_spaces(self) -> None:
        from arcade_cli.configure import _format_path_for_display
        path = Path(r"C:\Users\A User\My Folder\mcp.json")
        result = _format_path_for_display(path, platform_system="Windows")
        assert result.startswith('"')
        assert result.endswith('"')
        assert "A User" in result

    def test_windows_no_quotes_no_spaces(self) -> None:
        from arcade_cli.configure import _format_path_for_display
        path = Path(r"C:\Users\Alice\config.json")
        result = _format_path_for_display(path, platform_system="Windows")
        assert '"' not in result

    def test_linux_escapes_spaces(self) -> None:
        from arcade_cli.configure import _format_path_for_display
        if sys.platform == "win32":
            # On Windows, Path normalizes to backslashes, but the function should
            # still escape spaces.
            path = Path("/tmp/with space/mcp.json")
            result = _format_path_for_display(path, platform_system="Linux")
            assert "\\ " in result
        else:
            path = Path("/tmp/with space/mcp.json")
            result = _format_path_for_display(path, platform_system="Linux")
            assert result == "/tmp/with\\ space/mcp.json"

    def test_linux_no_escapes_no_spaces(self) -> None:
        from arcade_cli.configure import _format_path_for_display
        path = Path("/tmp/simple/mcp.json")
        result = _format_path_for_display(path, platform_system="Linux")
        assert "\\" not in result or sys.platform == "win32"  # Backslash is separator on Win


# =========================================================================
# 7. APPDATA RESOLUTION
# =========================================================================


class TestAppDataResolution:
    """Verify _resolve_windows_appdata delegates to platformdirs."""

    def test_delegates_to_platformdirs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_resolve_windows_appdata returns whatever platformdirs resolves."""
        from arcade_cli.configure import _resolve_windows_appdata

        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.delenv("USERPROFILE", raising=False)

        fake_platformdirs = types.ModuleType("platformdirs")
        fake_platformdirs.user_data_dir = (
            lambda *args, **kwargs: r"C:\Users\Alice\AppData\Roaming"
        )
        monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

        assert _resolve_windows_appdata() == Path(r"C:\Users\Alice\AppData\Roaming")

    def test_handles_older_platformdirs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to positional args when platformdirs raises TypeError."""
        from arcade_cli.configure import _resolve_windows_appdata

        def strict_user_data_dir(*args: object, **kwargs: object) -> str:
            if kwargs:
                raise TypeError("keyword args not supported")
            return r"C:\Users\Bob\AppData\Roaming"

        fake_platformdirs = types.ModuleType("platformdirs")
        fake_platformdirs.user_data_dir = strict_user_data_dir
        monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

        assert _resolve_windows_appdata() == Path(r"C:\Users\Bob\AppData\Roaming")


# =========================================================================
# 8. OAUTH CALLBACK — LOOPBACK BINDING
# =========================================================================


class TestOAuthCallbackServer:
    """Verify the OAuth callback server binds correctly."""

    def test_binds_to_loopback(self) -> None:
        """Server must bind to 127.0.0.1 to avoid Windows Firewall prompts."""
        from arcade_cli.authn import oauth_callback_server

        with oauth_callback_server("test-state", port=0) as server:
            assert server.httpd is not None
            host, _ = server.httpd.server_address
            assert host == "127.0.0.1"
            redirect = server.get_redirect_uri()
            assert redirect.startswith("http://localhost:")
            server.shutdown_server()

    def test_success_callback(self) -> None:
        """Successful OAuth callback returns the code."""
        from urllib.request import urlopen
        from arcade_cli.authn import oauth_callback_server

        state = "success-test"
        with oauth_callback_server(state, port=0) as server:
            url = f"{server.get_redirect_uri()}?code=abc123&state={state}"
            with urlopen(url) as response:
                assert response.status == 200
                response.read()
            assert server.wait_for_result(timeout=2.0) is True
        assert server.result["code"] == "abc123"

    def test_timeout(self) -> None:
        """Server reports timeout when no callback arrives."""
        from arcade_cli.authn import oauth_callback_server

        with oauth_callback_server("timeout-test", port=0) as server:
            assert server.wait_for_result(timeout=0.05) is False
        assert "Timed out" in server.result.get("error", "")

    def test_state_mismatch_returns_error(self) -> None:
        """Mismatched state should produce an error."""
        from urllib.error import HTTPError
        from urllib.request import urlopen
        from arcade_cli.authn import oauth_callback_server

        with oauth_callback_server("correct-state", port=0) as server:
            url = f"{server.get_redirect_uri()}?code=abc&state=wrong-state"
            try:
                with urlopen(url) as resp:
                    resp.read()
            except HTTPError:
                pass
            server.wait_for_result(timeout=1.0)
        assert "error" in server.result

    def test_missing_code_returns_error(self) -> None:
        """Missing code parameter should produce an error."""
        from urllib.error import HTTPError
        from urllib.request import urlopen
        from arcade_cli.authn import oauth_callback_server

        with oauth_callback_server("no-code", port=0) as server:
            url = f"{server.get_redirect_uri()}?state=no-code"
            try:
                with urlopen(url) as resp:
                    resp.read()
            except HTTPError:
                pass
            server.wait_for_result(timeout=1.0)
        assert "error" in server.result

    def test_wait_until_ready(self) -> None:
        """wait_until_ready should return True once listening."""
        import threading
        from arcade_cli.authn import OAuthCallbackServer

        server = OAuthCallbackServer("ready-test", port=0)
        t = threading.Thread(target=server.run_server, daemon=True)
        t.start()

        assert server.wait_until_ready(timeout=5.0) is True
        assert server.httpd is not None
        assert server.port != 0

        server.shutdown_server()
        t.join(timeout=2)


# =========================================================================
# 9. SIGNAL HANDLING — STDIO TRANSPORT
# =========================================================================


class TestSignalHandling:
    """Verify quiet Windows signal-handler fallback behavior."""

    @pytest.mark.asyncio
    async def test_signal_support_message_is_suppressed_on_windows(self) -> None:
        """On Windows, suppress noisy signal-support log messages."""
        import asyncio
        import logging
        from arcade_mcp_server.transports.stdio import StdioTransport

        transport = StdioTransport(name="test-stdio")
        log_records: list[logging.LogRecord] = []

        class RecordHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                log_records.append(record)

        logger = logging.getLogger("arcade.mcp.transports.stdio")
        handler = RecordHandler()
        logger.addHandler(handler)
        original_level = logger.level
        logger.setLevel(logging.DEBUG)

        try:
            with patch.object(sys, "platform", "win32"):
                loop = asyncio.get_running_loop()
                original_add = loop.add_signal_handler

                def raise_not_impl(*args, **kwargs):
                    raise NotImplementedError

                loop.add_signal_handler = raise_not_impl  # type: ignore[assignment]
                try:
                    await transport.start()
                finally:
                    loop.add_signal_handler = original_add  # type: ignore[assignment]
                    await transport.stop()

            messages = [r.getMessage() for r in log_records]
            assert not any(
                "Windows does not support asyncio signal handlers" in m for m in messages
            )
            assert not any("Failed to set up signal handler" in m for m in messages)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)


# =========================================================================
# 10. NEW TOOLKIT SCAFFOLDING
# =========================================================================


class TestNewToolkitScaffolding:
    """Tests for arcade new scaffold on both platforms."""

    def test_scaffold_in_path_with_spaces(self, tmp_path: Path) -> None:
        from arcade_cli.new import create_new_toolkit_minimal

        output_dir = tmp_path / "dir with spaces"
        output_dir.mkdir()
        create_new_toolkit_minimal(str(output_dir), "my_server")

        root = output_dir / "my_server"
        assert (root / "pyproject.toml").is_file()
        assert (root / "src" / "my_server" / "server.py").is_file()
        assert (root / "src" / "my_server" / ".env.example").is_file()

    def test_scaffold_prints_next_steps(self, tmp_path: Path) -> None:
        from arcade_cli.new import create_new_toolkit_minimal

        buf = StringIO()
        from rich.console import Console
        test_console = Console(file=buf, force_terminal=False)

        import arcade_cli.new as new_mod
        orig = new_mod.console
        new_mod.console = test_console
        try:
            output_dir = tmp_path / "test_steps"
            output_dir.mkdir()
            create_new_toolkit_minimal(str(output_dir), "demo")
        finally:
            new_mod.console = orig

        output = buf.getvalue()
        assert "Next steps:" in output
        assert "uv run server.py" in output

    def test_rejects_duplicate_name(self, tmp_path: Path) -> None:
        from arcade_cli.new import create_new_toolkit_minimal

        output_dir = tmp_path / "dup"
        output_dir.mkdir()
        create_new_toolkit_minimal(str(output_dir), "srv")

        with pytest.raises(FileExistsError, match="already exists"):
            create_new_toolkit_minimal(str(output_dir), "srv")

    def test_rejects_invalid_name(self, tmp_path: Path) -> None:
        from arcade_cli.new import create_new_toolkit_minimal

        output_dir = tmp_path / "invalid"
        output_dir.mkdir()
        with pytest.raises(ValueError, match="illegal characters"):
            create_new_toolkit_minimal(str(output_dir), "My-Server!")


# =========================================================================
# 11. WARN OVERWRITE HELPER
# =========================================================================


class TestWarnOverwrite:
    """Tests for _warn_overwrite in configure.py."""

    def test_prints_warning_when_entry_exists(self) -> None:
        from arcade_cli.configure import _warn_overwrite
        from rich.console import Console

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False)

        import arcade_cli.configure as mod
        orig = mod.console
        mod.console = test_console
        try:
            config = {"mcpServers": {"demo": {"command": "old"}}}
            _warn_overwrite(config, "mcpServers", "demo", Path("/fake/config.json"))
        finally:
            mod.console = orig

        output = buf.getvalue()
        assert "demo" in output
        assert "already exists" in output

    def test_silent_when_no_entry(self) -> None:
        from arcade_cli.configure import _warn_overwrite
        from rich.console import Console

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False)

        import arcade_cli.configure as mod
        orig = mod.console
        mod.console = test_console
        try:
            config: dict = {"mcpServers": {}}
            _warn_overwrite(config, "mcpServers", "new_server", Path("/fake/config.json"))
        finally:
            mod.console = orig

        assert buf.getvalue() == ""


# =========================================================================
# 12. EVAL FILE DISCOVERY
# =========================================================================


class TestEvalFilePaths:
    """Tests for get_eval_files with platform-agnostic path handling."""

    def test_finds_eval_files(self, tmp_path: Path) -> None:
        from arcade_cli.utils import get_eval_files

        eval_dir = tmp_path / "evals"
        eval_dir.mkdir()
        (eval_dir / "eval_one.py").write_text("print('one')\n", encoding="utf-8")
        (eval_dir / "not_eval.py").write_text("print('no')\n", encoding="utf-8")
        (eval_dir / "eval_two.py").write_text("print('two')\n", encoding="utf-8")

        files = get_eval_files(str(eval_dir))
        names = [Path(f).name for f in files]
        assert "eval_one.py" in names
        assert "eval_two.py" in names
        assert "not_eval.py" not in names

    def test_returns_single_file(self, tmp_path: Path) -> None:
        from arcade_cli.utils import get_eval_files

        eval_file = tmp_path / "eval_single.py"
        eval_file.write_text("print('single')\n", encoding="utf-8")

        files = get_eval_files(str(eval_file))
        assert len(files) == 1
        assert Path(files[0]).name == "eval_single.py"


# =========================================================================
# 13. PERFORM OAUTH LOGIN — URL ALWAYS SHOWN
# =========================================================================


class TestPerformOAuthLogin:
    """Verify perform_oauth_login always surfaces the auth URL."""

    def _run_login(self, browser_return: bool) -> list[str]:
        status_messages: list[str] = []

        def capture(msg: str) -> None:
            status_messages.append(msg)

        with (
            patch("arcade_cli.authn.fetch_cli_config") as mock_config,
            patch("arcade_cli.authn.create_oauth_client"),
            patch("arcade_cli.authn.generate_authorization_url") as mock_gen_url,
            patch("arcade_cli.authn._open_browser") as mock_browser,
            patch("arcade_cli.authn.oauth_callback_server") as mock_server_ctx,
        ):
            mock_config.return_value = MagicMock()
            mock_gen_url.return_value = ("https://example.com/auth?state=abc", "verifier123")
            mock_browser.return_value = browser_return

            mock_server = MagicMock()
            mock_server.get_redirect_uri.return_value = "http://localhost:9999/callback"
            mock_server.result = {"error": "timeout for test"}
            mock_server.wait_for_result.return_value = False
            mock_server_ctx.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_server_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from arcade_cli.authn import OAuthLoginError, perform_oauth_login

            try:
                perform_oauth_login(
                    "https://fake.example.com",
                    on_status=capture,
                    callback_timeout_seconds=1,
                )
            except OAuthLoginError:
                pass

        return status_messages

    def test_shows_url_when_browser_succeeds(self) -> None:
        msgs = self._run_login(browser_return=True)
        url_msgs = [m for m in msgs if "https://example.com/auth" in m]
        assert len(url_msgs) >= 1

    def test_shows_url_when_browser_fails(self) -> None:
        msgs = self._run_login(browser_return=False)
        url_msgs = [m for m in msgs if "https://example.com/auth" in m]
        assert len(url_msgs) >= 1
        browser_fail_msgs = [m for m in msgs if "Could not open a browser" in m]
        assert len(browser_fail_msgs) >= 1

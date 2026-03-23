"""Tests for the `arcade update` CLI command."""

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.main import cli
from arcade_cli.update import (
    InstallMethod,
    UpdateCache,
    _background_check,
    check_and_notify,
    detect_install_method,
    fetch_latest_pypi_version,
    fork_background_check,
    read_update_cache,
    should_check_for_update,
    write_update_cache,
)
from typer.testing import CliRunner

runner = CliRunner()

PACKAGE_NAME = "arcade-mcp"


# ---------------------------------------------------------------------------
# Unit tests for fetch_latest_pypi_version
# ---------------------------------------------------------------------------


class TestFetchLatestPypiVersion:
    def test_returns_version_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"info": {"version": "2.0.0"}}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arcade_cli.update.urlopen", return_value=mock_response):
            assert fetch_latest_pypi_version() == "2.0.0"

    def test_falls_back_to_stable_release_when_latest_is_prerelease(self) -> None:
        """When info.version is a pre-release, return the highest stable from releases."""
        mock_response = MagicMock()
        mock_response.status = 200
        payload = json.dumps({
            "info": {"version": "2.0.0rc1"},
            "releases": {"1.9.0": [], "2.0.0rc1": [], "1.10.0": []},
        }).encode()
        mock_response.read.return_value = payload
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arcade_cli.update.urlopen", return_value=mock_response):
            assert fetch_latest_pypi_version() == "1.10.0"

    def test_returns_none_when_only_prereleases_exist(self) -> None:
        """When all releases are pre-releases, return None."""
        mock_response = MagicMock()
        mock_response.status = 200
        payload = json.dumps({
            "info": {"version": "2.0.0rc1"},
            "releases": {"2.0.0a1": [], "2.0.0rc1": []},
        }).encode()
        mock_response.read.return_value = payload
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("arcade_cli.update.urlopen", return_value=mock_response):
            assert fetch_latest_pypi_version() is None

    def test_returns_none_on_http_error(self) -> None:
        with patch("arcade_cli.update.urlopen", side_effect=Exception("network error")):
            assert fetch_latest_pypi_version() is None


# ---------------------------------------------------------------------------
# Unit tests for detect_install_method
# ---------------------------------------------------------------------------


class TestDetectInstallMethod:
    def test_detects_uv_tool(self) -> None:
        """If `uv tool list` output contains the package name, method is UV_TOOL."""
        uv_tool_output = "arcade-mcp v1.12.1\n- arcade\n- arcade-mcp\nother-package v0.1.0\n"
        with patch("arcade_cli.update.shutil") as mock_shutil:
            mock_shutil.which.return_value = "/usr/local/bin/uv"
            with patch("arcade_cli.update.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=uv_tool_output)
                assert detect_install_method() == InstallMethod.UV_TOOL

    def test_detects_pipx(self) -> None:
        """If uv tool doesn't have it but pipx does, method is PIPX."""

        def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
            if cmd[0] == "uv":
                return MagicMock(returncode=0, stdout="other-package v1.0.0\n")
            if cmd[0] == "pipx":
                return MagicMock(returncode=0, stdout=f"   package {PACKAGE_NAME} 1.12.1")
            return MagicMock(returncode=1, stdout="")

        with patch("arcade_cli.update.shutil") as mock_shutil:
            mock_shutil.which.side_effect = lambda name: f"/usr/local/bin/{name}"
            with patch("arcade_cli.update.subprocess.run", side_effect=run_side_effect):
                assert detect_install_method() == InstallMethod.PIPX

    def test_falls_back_to_uv_pip_when_uv_available(self) -> None:
        """If uv is available but package not in uv tool or pipx, use UV_PIP."""

        def run_side_effect(cmd: list[str], **kwargs: object) -> MagicMock:
            # Neither uv tool nor pipx has it
            return MagicMock(returncode=0, stdout="other-package v1.0.0\n")

        def which_side_effect(name: str) -> str | None:
            if name == "uv":
                return "/usr/local/bin/uv"
            return None  # pipx not available

        with patch("arcade_cli.update.shutil") as mock_shutil:
            mock_shutil.which.side_effect = which_side_effect
            with patch("arcade_cli.update.subprocess.run", side_effect=run_side_effect):
                assert detect_install_method() == InstallMethod.UV_PIP

    def test_does_not_false_positive_on_prefix_match(self) -> None:
        """arcade-mcp-server should NOT be detected as arcade-mcp."""
        uv_tool_output = "arcade-mcp-server v1.0.0\n- arcade-mcp-server\n"
        with patch("arcade_cli.update.shutil") as mock_shutil:
            mock_shutil.which.return_value = "/usr/local/bin/uv"
            with patch("arcade_cli.update.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=uv_tool_output)
                # Should NOT detect UV_TOOL since only arcade-mcp-server is installed
                assert detect_install_method() == InstallMethod.UV_PIP

    def test_falls_back_to_pip(self) -> None:
        """If neither uv nor pipx is available, fall back to PIP."""
        with patch("arcade_cli.update.shutil") as mock_shutil:
            mock_shutil.which.return_value = None  # nothing on PATH
            assert detect_install_method() == InstallMethod.PIP


# ---------------------------------------------------------------------------
# Integration tests for the `arcade update` CLI command
# ---------------------------------------------------------------------------


class TestUpdateCommand:
    def test_already_up_to_date(self) -> None:
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="1.12.1"),
            patch("arcade_cli.update.metadata") as mock_meta,
        ):
            mock_meta.version.return_value = "1.12.1"
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "up to date" in result.output.lower()

    def test_update_available_uv_tool(self) -> None:
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.detect_install_method", return_value=InstallMethod.UV_TOOL),
            patch("arcade_cli.update.subprocess.run") as mock_run,
        ):
            mock_meta.version.return_value = "1.12.1"
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["uv", "tool", "upgrade", PACKAGE_NAME]

    def test_update_available_pipx_shows_warning(self) -> None:
        """Non-uv-tool methods should show a warning recommending uv tool install."""
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.detect_install_method", return_value=InstallMethod.PIPX),
            patch("arcade_cli.update.subprocess.run") as mock_run,
        ):
            mock_meta.version.return_value = "1.12.1"
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "recommend" in result.output.lower()
            assert "uv tool" in result.output.lower()

    def test_update_available_uv_pip_shows_warning(self) -> None:
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.detect_install_method", return_value=InstallMethod.UV_PIP),
            patch("arcade_cli.update.subprocess.run") as mock_run,
        ):
            mock_meta.version.return_value = "1.12.1"
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "recommend" in result.output.lower()
            assert "uv tool" in result.output.lower()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["uv", "pip", "install", "--upgrade", PACKAGE_NAME]

    def test_update_available_pip_shows_warning(self) -> None:
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.detect_install_method", return_value=InstallMethod.PIP),
            patch("arcade_cli.update.subprocess.run") as mock_run,
        ):
            mock_meta.version.return_value = "1.12.1"
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "recommend" in result.output.lower()
            assert "uv tool" in result.output.lower()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["pip", "install", "--upgrade", PACKAGE_NAME]

    def test_upgrade_alias_works(self) -> None:
        """The `arcade upgrade` alias should behave identically."""
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="1.12.1"),
            patch("arcade_cli.update.metadata") as mock_meta,
        ):
            mock_meta.version.return_value = "1.12.1"
            result = runner.invoke(cli, ["upgrade"])
            assert result.exit_code == 0
            assert "up to date" in result.output.lower()

    def test_pypi_fetch_failure(self) -> None:
        with patch("arcade_cli.update.fetch_latest_pypi_version", return_value=None):
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "could not check" in result.output.lower()

    def test_upgrade_command_failure_shows_manual_instructions(self) -> None:
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.detect_install_method", return_value=InstallMethod.UV_TOOL),
            patch("arcade_cli.update.subprocess.run") as mock_run,
        ):
            mock_meta.version.return_value = "1.12.1"
            mock_run.return_value = MagicMock(returncode=1)
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            output = result.output.lower()
            # Should show preferred method and alternatives
            assert "uv tool upgrade" in output
            assert "alternatives" in output


# ---------------------------------------------------------------------------
# Unit tests for UpdateCache and cache I/O
# ---------------------------------------------------------------------------


class TestUpdateCache:
    def test_read_cache_returns_none_when_file_missing(self, tmp_path: pytest.TempPathFactory) -> None:
        assert read_update_cache(str(tmp_path / "nonexistent.json")) is None

    def test_read_cache_returns_none_on_corrupt_json(self, tmp_path: pytest.TempPathFactory) -> None:
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text("not valid json{{{")
        assert read_update_cache(str(cache_file)) is None

    def test_write_and_read_cache_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        cache_file = str(tmp_path / "update_cache.json")
        cache = UpdateCache(latest_version="2.0.0", checked_at=1000.0)
        write_update_cache(cache_file, cache)
        result = read_update_cache(cache_file)
        assert result is not None
        assert result.latest_version == "2.0.0"
        assert result.checked_at == 1000.0

    def test_read_cache_ignores_unknown_fields(self, tmp_path: pytest.TempPathFactory) -> None:
        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text(json.dumps({
            "latest_version": "2.0.0",
            "checked_at": 1000.0,
            "unknown_field": "should be ignored",
        }))
        result = read_update_cache(str(cache_file))
        assert result is not None
        assert result.latest_version == "2.0.0"


# ---------------------------------------------------------------------------
# Unit tests for should_check_for_update
# ---------------------------------------------------------------------------


class TestShouldCheckForUpdate:
    def test_returns_true_when_no_cache(self) -> None:
        assert should_check_for_update(None) is True

    def test_returns_true_when_cache_expired(self) -> None:
        old_cache = UpdateCache(latest_version="1.0.0", checked_at=time.time() - 5 * 3600)
        assert should_check_for_update(old_cache) is True

    def test_returns_false_when_cache_fresh(self) -> None:
        fresh_cache = UpdateCache(latest_version="1.0.0", checked_at=time.time() - 60)
        assert should_check_for_update(fresh_cache) is False

    def test_returns_false_when_disabled_env_var(self) -> None:
        with patch.dict(os.environ, {"ARCADE_DISABLE_AUTOUPDATE": "1"}):
            assert should_check_for_update(None) is False


# ---------------------------------------------------------------------------
# Unit tests for fork_background_check
# ---------------------------------------------------------------------------


class TestForkBackgroundCheck:
    def test_background_check_import_string_is_valid(self) -> None:
        """The hardcoded import string in fork_background_check must resolve to the real function."""
        import importlib
        import inspect

        source = inspect.getsource(fork_background_check)
        # Extract the import string from the "-c" argument
        assert "from arcade_cli.update import _background_check; _background_check()" in source
        # Verify the function is actually importable at that path
        mod = importlib.import_module("arcade_cli.update")
        assert hasattr(mod, "_background_check") and callable(mod._background_check)

    def test_spawns_detached_subprocess_unix(self) -> None:
        """On Unix, spawns a detached subprocess with start_new_session=True."""
        with (
            patch("arcade_cli.update.read_update_cache", return_value=None),
            patch("arcade_cli.update.should_check_for_update", return_value=True),
            patch("arcade_cli.update.sys") as mock_sys,
            patch("arcade_cli.update.subprocess.Popen") as mock_popen,
        ):
            mock_sys.platform = "darwin"
            mock_sys.executable = "/usr/bin/python3"
            fork_background_check()
            mock_popen.assert_called_once()
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs.get("start_new_session") is True
            assert call_kwargs.get("close_fds") is True

    def test_spawns_detached_subprocess_windows(self) -> None:
        """On Windows, spawns a subprocess with creationflags instead of start_new_session."""
        with (
            patch("arcade_cli.update.read_update_cache", return_value=None),
            patch("arcade_cli.update.should_check_for_update", return_value=True),
            patch("arcade_cli.update.sys") as mock_sys,
            patch("arcade_cli.update.subprocess.Popen") as mock_popen,
            patch("arcade_cli.update.get_windows_no_window_creationflags", return_value=0x08000200),
            patch("arcade_cli.update.build_windows_hidden_startupinfo", return_value=None),
        ):
            mock_sys.platform = "win32"
            mock_sys.executable = "python.exe"
            fork_background_check()
            mock_popen.assert_called_once()
            call_kwargs = mock_popen.call_args[1]
            assert "start_new_session" not in call_kwargs
            assert call_kwargs.get("creationflags") == 0x08000200
            assert call_kwargs.get("close_fds") is True

    def test_does_not_spawn_when_check_not_needed(self) -> None:
        """When cache is fresh, no subprocess is spawned."""
        fresh_cache = UpdateCache(latest_version="1.0.0", checked_at=time.time())
        with (
            patch("arcade_cli.update.read_update_cache", return_value=fresh_cache),
            patch("arcade_cli.update.should_check_for_update", return_value=False),
            patch("arcade_cli.update.subprocess.Popen") as mock_popen,
        ):
            fork_background_check()
            mock_popen.assert_not_called()

    def test_swallows_exceptions(self) -> None:
        """Popen raising an exception should not crash."""
        with (
            patch("arcade_cli.update.read_update_cache", return_value=None),
            patch("arcade_cli.update.should_check_for_update", return_value=True),
            patch("arcade_cli.update.subprocess.Popen", side_effect=OSError("spawn failed")),
        ):
            # Should not raise
            fork_background_check()


# ---------------------------------------------------------------------------
# Unit tests for check_and_notify
# ---------------------------------------------------------------------------


class TestCheckAndNotify:
    def test_prints_notification_when_update_available(self) -> None:
        cache = UpdateCache(latest_version="2.0.0", checked_at=time.time())
        with (
            patch("arcade_cli.update.read_update_cache", return_value=cache),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.fork_background_check"),
            patch("arcade_cli.update.console") as mock_console,
        ):
            mock_meta.version.return_value = "1.0.0"
            check_and_notify()
            output = mock_console.print.call_args[0][0]
            assert "update available" in output.lower()
            assert "arcade update" in output.lower()
            assert mock_console.print.call_args[1]["style"] == "yellow"

    def test_no_notification_when_up_to_date(self) -> None:
        cache = UpdateCache(latest_version="1.0.0", checked_at=time.time())
        with (
            patch("arcade_cli.update.read_update_cache", return_value=cache),
            patch("arcade_cli.update.metadata") as mock_meta,
            patch("arcade_cli.update.fork_background_check"),
            patch("arcade_cli.update.console") as mock_console,
        ):
            mock_meta.version.return_value = "1.0.0"
            check_and_notify()
            mock_console.print.assert_not_called()

    def test_no_notification_when_no_cache(self) -> None:
        with (
            patch("arcade_cli.update.read_update_cache", return_value=None),
            patch("arcade_cli.update.fork_background_check"),
            patch("arcade_cli.update.console") as mock_console,
        ):
            check_and_notify()
            mock_console.print.assert_not_called()

    def test_no_notification_when_disabled(self) -> None:
        with (
            patch.dict(os.environ, {"ARCADE_DISABLE_AUTOUPDATE": "1"}),
            patch("arcade_cli.update.read_update_cache") as mock_read,
            patch("arcade_cli.update.fork_background_check") as mock_fork,
            patch("arcade_cli.update.console") as mock_console,
        ):
            check_and_notify()
            mock_read.assert_not_called()
            mock_fork.assert_not_called()
            mock_console.print.assert_not_called()

    def test_forks_background_check(self) -> None:
        with (
            patch("arcade_cli.update.read_update_cache", return_value=None),
            patch("arcade_cli.update.fork_background_check") as mock_fork,
        ):
            check_and_notify()
            mock_fork.assert_called_once()


# ---------------------------------------------------------------------------
# Unit tests for _background_check
# ---------------------------------------------------------------------------


class TestBackgroundCheck:
    def test_updates_timestamp_when_fetch_returns_none(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """When fetch returns None, the cache timestamp is still updated to throttle retries."""
        cache_path = str(tmp_path / "update_cache.json")
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value=None),
            patch("arcade_cli.update.UPDATE_CACHE_PATH", cache_path),
        ):
            _background_check()
            result = read_update_cache(cache_path)
            assert result is not None
            assert result.latest_version == ""
            assert result.checked_at > 0

    def test_preserves_cached_version_when_fetch_fails(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """When fetch fails but a previous version is cached, preserve it."""
        cache_path = str(tmp_path / "update_cache.json")
        old_cache = UpdateCache(latest_version="1.5.0", checked_at=1000.0)
        write_update_cache(cache_path, old_cache)
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value=None),
            patch("arcade_cli.update.UPDATE_CACHE_PATH", cache_path),
        ):
            _background_check()
            result = read_update_cache(cache_path)
            assert result is not None
            assert result.latest_version == "1.5.0"
            assert result.checked_at > old_cache.checked_at

    def test_caches_stable_release(self, tmp_path: pytest.TempPathFactory) -> None:
        """Stable versions from PyPI should be cached."""
        cache_path = str(tmp_path / "update_cache.json")
        with (
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="2.0.0"),
            patch("arcade_cli.update.UPDATE_CACHE_PATH", cache_path),
        ):
            _background_check()
            result = read_update_cache(cache_path)
            assert result is not None
            assert result.latest_version == "2.0.0"


# ---------------------------------------------------------------------------
# Tests for main_callback integration with check_and_notify
# ---------------------------------------------------------------------------


class TestMainCallbackUpdateNotification:
    def test_main_callback_calls_check_and_notify(self) -> None:
        """Running a non-update command triggers check_and_notify."""
        with patch("arcade_cli.main.check_and_notify") as mock_notify:
            # Use 'show' as a public command that goes through main_callback
            runner.invoke(cli, ["show", "--help"])
            mock_notify.assert_called_once()

    def test_main_callback_skips_check_for_update_command(self) -> None:
        """Running `arcade update` should NOT trigger check_and_notify."""
        with (
            patch("arcade_cli.main.check_and_notify") as mock_notify,
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="1.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
        ):
            mock_meta.version.return_value = "1.0.0"
            runner.invoke(cli, ["update"])
            mock_notify.assert_not_called()

    def test_main_callback_skips_check_for_upgrade_command(self) -> None:
        """Running `arcade upgrade` should NOT trigger check_and_notify."""
        with (
            patch("arcade_cli.main.check_and_notify") as mock_notify,
            patch("arcade_cli.update.fetch_latest_pypi_version", return_value="1.0.0"),
            patch("arcade_cli.update.metadata") as mock_meta,
        ):
            mock_meta.version.return_value = "1.0.0"
            runner.invoke(cli, ["upgrade"])
            mock_notify.assert_not_called()

    def test_main_callback_skips_check_for_mcp_command(self) -> None:
        """Running `arcade mcp` should NOT trigger check_and_notify (would corrupt stdio)."""
        with patch("arcade_cli.main.check_and_notify") as mock_notify:
            runner.invoke(cli, ["mcp", "--help"])
            mock_notify.assert_not_called()

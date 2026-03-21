"""Tests for the `arcade update` CLI command."""

from unittest.mock import MagicMock, patch

from arcade_cli.main import cli
from arcade_cli.update import InstallMethod, detect_install_method, fetch_latest_pypi_version
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
            # Should show manual fallback instructions
            assert "uv tool upgrade" in result.output.lower() or "manually" in result.output.lower()

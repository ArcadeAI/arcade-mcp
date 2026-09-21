import textwrap
from unittest.mock import patch

import pytest
from arcade_cli.main import cli
from arcade_cli.show import show_logic
from arcade_cli.utils import CLIError
from typer.testing import CliRunner


def test_show_logic_local_false():
    with patch("arcade_cli.show.get_tools_from_engine") as mock_get_tools:
        mock_get_tools.return_value = []
        show_logic(
            toolkit=None,
            tool=None,
            host="localhost",
            local=False,
            port=None,
            force_tls=False,
            force_no_tls=False,
            worker=False,
            debug=False,
        )

        # get_tools_from_engine should be called when local=False
        mock_get_tools.assert_called_once()


def test_show_logic_local_true():
    with patch("arcade_cli.show.create_cli_catalog_local") as mock_create_catalog:
        mock_create_catalog.return_value = []

        show_logic(
            toolkit=None,
            tool=None,
            host="localhost",
            local=True,
            port=None,
            force_tls=False,
            force_no_tls=False,
            worker=False,
            debug=False,
        )

        # create_cli_catalog_local should be called when local=True
        # and toolkit is not provided
        mock_create_catalog.assert_called_once()


@pytest.fixture
def broken_local_project(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "tools.py").write_text(
        textwrap.dedent(
            """
            from arcade_mcp_server import MCPApp

            app = MCPApp(name="Test")

            @app.tool
            def broken() -> str:
                return "example"
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARCADE_DISABLE_AUTOUPDATE", "1")
    return tmp_path


def test_show_logic_raises_cli_error_on_invalid_local_tool(broken_local_project):
    with pytest.raises(CLIError) as exc_info:
        show_logic(
            toolkit=None,
            tool=None,
            host="localhost",
            local=True,
            port=None,
            force_tls=False,
            force_no_tls=False,
            worker=False,
            debug=False,
        )

    message = str(exc_info.value)
    assert "broken" in message
    assert "description" in message.lower()


def test_show_local_exits_nonzero_on_invalid_tool(broken_local_project):
    result = CliRunner().invoke(cli, ["show", "--local"])
    output = f"{result.output}{getattr(result, 'stdout', '')}{getattr(result, 'stderr', '')}"

    assert result.exit_code == 1
    assert "broken" in output
    assert "description" in output.lower()

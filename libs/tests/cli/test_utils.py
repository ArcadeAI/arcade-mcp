import textwrap
from unittest.mock import patch

import pytest
from arcade_cli.utils import (
    Provider,
    compute_base_url,
    create_cli_catalog_local,
    resolve_provider_api_key,
)
from arcade_core.errors import ToolDefinitionError, ToolInputSchemaError

DEFAULT_CLOUD_HOST = "cloud.arcade.dev"
DEFAULT_ENGINE_HOST = "api.arcade.dev"
LOCALHOST = "localhost"
DEFAULT_PORT = None
DEFAULT_FORCE_TLS = False
DEFAULT_FORCE_NO_TLS = False


@pytest.mark.parametrize(
    "inputs, expected_output",
    [
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade.dev",
            id="default",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "http://localhost:9099",
            id="localhost",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade.dev:9099",
            id="custom port",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "http://localhost:9099",
            id="localhost with custom port",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade.dev",
            id="force TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://localhost:9099",
            id="localhost with force TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://api.arcade.dev:9099",
            id="custom port with force TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://localhost:9099",
            id="localhost with custom port and force TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://api.arcade.dev",
            id="force no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with force no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://api.arcade.dev:9099",
            id="custom port with force no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with custom port and force no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://api.arcade.dev",
            id="force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": DEFAULT_PORT,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": DEFAULT_ENGINE_HOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://api.arcade.dev:9099",
            id="custom port with force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": LOCALHOST,
                "port_input": 9099,
                "force_tls": True,
                "force_no_tls": True,
            },
            "http://localhost:9099",
            id="localhost with custom port, force TLS and no TLS",
        ),
        pytest.param(
            {
                "host_input": "arandomhost.com",
                "port_input": DEFAULT_PORT,
                "force_tls": DEFAULT_FORCE_TLS,
                "force_no_tls": DEFAULT_FORCE_NO_TLS,
            },
            "https://arandomhost.com",
            id="random host",
        ),
    ],
)
def test_compute_base_url(inputs: dict, expected_output: str):
    base_url = compute_base_url(
        inputs["force_tls"],
        inputs["force_no_tls"],
        inputs["host_input"],
        inputs["port_input"],
    )

    assert base_url == expected_output


def test_resolve_provider_api_key(monkeypatch):
    resolved_api_key = resolve_provider_api_key(Provider.OPENAI, "123")
    assert resolved_api_key == "123"

    resolved_api_key = resolve_provider_api_key("not-a-provider", None)
    assert resolved_api_key is None

    # Ensure OPENAI_API_KEY is not set in the environment for this test
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resolved_api_key = resolve_provider_api_key(Provider.OPENAI, None)
    assert resolved_api_key is None


def _write_local_project(tmp_path, source: str, filename: str = "tools.py") -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / filename).write_text(textwrap.dedent(source), encoding="utf-8")


def test_create_cli_catalog_local_plain_tool_missing_docstring(tmp_path, monkeypatch):
    _write_local_project(
        tmp_path,
        """
        from arcade_tdk import tool

        @tool
        def broken() -> str:
            return "example"
        """,
    )
    monkeypatch.chdir(tmp_path)

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        with pytest.raises(ToolDefinitionError, match="(?i)broken"):
            create_cli_catalog_local()
        mock_fallback.assert_not_called()


def test_create_cli_catalog_local_app_tool_missing_docstring(tmp_path, monkeypatch):
    _write_local_project(
        tmp_path,
        """
        from arcade_mcp_server import MCPApp

        app = MCPApp(name="Test")

        @app.tool
        def broken() -> str:
            return "example"
        """,
    )
    monkeypatch.chdir(tmp_path)

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        with pytest.raises(ToolDefinitionError, match="broken"):
            create_cli_catalog_local()
        mock_fallback.assert_not_called()


def test_create_cli_catalog_local_mixed_valid_and_invalid_tools(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "valid.py").write_text(
        textwrap.dedent(
            """
            from arcade_tdk import tool

            @tool
            def ok() -> str:
                \"\"\"A valid tool.\"\"\"
                return "ok"
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "broken.py").write_text(
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

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        with pytest.raises(ToolDefinitionError, match="broken"):
            create_cli_catalog_local()
        mock_fallback.assert_not_called()


def test_create_cli_catalog_local_preserves_tool_input_schema_error(tmp_path, monkeypatch):
    _write_local_project(
        tmp_path,
        """
        from arcade_tdk import tool

        @tool
        def broken(param1: str) -> str:
            \"\"\"Has a docstring.\"\"\"
            return "example"
        """,
    )
    monkeypatch.chdir(tmp_path)

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        with pytest.raises(ToolInputSchemaError, match="param1") as exc_info:
            create_cli_catalog_local()
        assert "missing a description" in str(exc_info.value)
        mock_fallback.assert_not_called()


def test_create_cli_catalog_local_preserves_reserved_argument_error(tmp_path, monkeypatch):
    _write_local_project(
        tmp_path,
        """
        from typing import Annotated
        from arcade_tdk import tool

        @tool
        def reserved(connected_account: Annotated[str, "The account to use"]) -> str:
            \"\"\"A tool that collides with the reserved name.\"\"\"
            return connected_account
        """,
    )
    monkeypatch.chdir(tmp_path)

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        with pytest.raises(ToolInputSchemaError, match="connected_account") as exc_info:
            create_cli_catalog_local()
        assert "Arcade Engine" in str(exc_info.value)
        assert "Rename" in str(exc_info.value)
        mock_fallback.assert_not_called()


def test_create_cli_catalog_local_valid_discovery(tmp_path, monkeypatch):
    _write_local_project(
        tmp_path,
        """
        from arcade_tdk import tool

        @tool
        def ok() -> str:
            \"\"\"A valid tool.\"\"\"
            return "ok"
        """,
    )
    monkeypatch.chdir(tmp_path)

    with patch("arcade_cli.utils._discover_installed_toolkits") as mock_fallback:
        catalog = create_cli_catalog_local()
        mock_fallback.assert_not_called()

    assert [tool.definition.name for tool in catalog] == ["Ok"]


def test_create_cli_catalog_local_falls_back_when_no_local_tools(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with patch(
        "arcade_cli.utils._discover_installed_toolkits", return_value="fallback"
    ) as mock_fallback:
        result = create_cli_catalog_local()

    mock_fallback.assert_called_once()
    assert result == "fallback"


def test_create_cli_catalog_local_falls_back_when_pyproject_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch(
        "arcade_cli.utils._discover_installed_toolkits", return_value="fallback"
    ) as mock_fallback:
        result = create_cli_catalog_local()

    mock_fallback.assert_called_once()
    assert result == "fallback"

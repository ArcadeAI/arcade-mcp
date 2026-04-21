"""Tests for get_tool_secrets() and gateway configuration in arcade configure."""

import json
import sys
import types
from io import StringIO
from pathlib import Path

import pytest
from arcade_cli.configure import (
    _format_path_for_display,
    _resolve_windows_appdata,
    _warn_overwrite,
    configure_amazonq_arcade,
    configure_claude_arcade,
    configure_client,
    configure_client_gateway,
    configure_client_toolkit,
    configure_cursor_arcade,
    configure_vscode_arcade,
    configure_windsurf_arcade,
    get_tool_secrets,
    get_toolkit_http_config,
    get_toolkit_stdio_config,
)


def _write_entrypoint(tmp_path: Path) -> Path:
    entrypoint = tmp_path / "server.py"
    entrypoint.write_text("print('ok')\n", encoding="utf-8")
    return entrypoint


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_stdio_entry(entry: dict) -> None:
    assert "command" in entry
    assert "args" in entry
    assert any(str(arg).endswith("server.py") for arg in entry["args"])
    assert "env" in entry


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


# ---------------------------------------------------------------------------
# _format_path_for_display()
# ---------------------------------------------------------------------------


def test_format_path_for_display_windows_quotes() -> None:
    path = Path(r"C:\Users\A User\My Server\mcp.json")
    assert (
        _format_path_for_display(path, platform_system="Windows")
        == '"C:\\Users\\A User\\My Server\\mcp.json"'
    )


def test_format_path_for_display_no_spaces_unchanged() -> None:
    """Paths without spaces should be returned as-is."""
    path = Path(r"C:\Users\Alice\mcp.json")
    result = _format_path_for_display(path, platform_system="Windows")
    assert result == str(path)
    assert '"' not in result


def test_format_path_for_display_posix_escapes() -> None:
    # Use str directly to avoid Windows Path normalization converting / to \
    import sys

    if sys.platform == "win32":
        # On Windows, Path("/tmp/with space/mcp.json") uses backslashes.
        # The function should still escape spaces.
        path = Path("/tmp/with space/mcp.json")
        result = _format_path_for_display(path, platform_system="Linux")
        assert "\\ " in result  # spaces are escaped
    else:
        path = Path("/tmp/with space/mcp.json")
        assert (
            _format_path_for_display(path, platform_system="Linux") == "/tmp/with\\ space/mcp.json"
        )


# ---------------------------------------------------------------------------
# _resolve_windows_appdata()
# ---------------------------------------------------------------------------


def test_resolve_windows_appdata_delegates_to_platformdirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_resolve_windows_appdata returns whatever platformdirs resolves."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)

    fake_platformdirs = types.ModuleType("platformdirs")
    fake_platformdirs.user_data_dir = lambda *args, **kwargs: r"C:\Users\Alice\AppData\Roaming"
    monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

    assert _resolve_windows_appdata() == Path(r"C:\Users\Alice\AppData\Roaming")


def test_resolve_windows_appdata_handles_older_platformdirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falls back to positional args when platformdirs raises TypeError.

    The positional signature is user_data_dir(appname, appauthor, version, roaming).
    The fallback call must pass roaming=True as the *fourth* positional arg, not
    the third (which would be ``version``).
    """
    received_args: list[tuple] = []

    def strict_user_data_dir(*args: object, **kwargs: object) -> str:
        if kwargs:
            raise TypeError("keyword args not supported")
        received_args.append(args)
        return r"C:\Users\Bob\AppData\Roaming"

    fake_platformdirs = types.ModuleType("platformdirs")
    fake_platformdirs.user_data_dir = strict_user_data_dir
    monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

    result = _resolve_windows_appdata()
    assert result == Path(r"C:\Users\Bob\AppData\Roaming")

    # First call raises TypeError (has kwargs), second call uses positional args.
    # Verify the fallback used the correct signature: (appname, appauthor, version, roaming)
    assert len(received_args) == 1, "Fallback must make exactly one positional call"
    fallback_args = received_args[0]
    # args: (None, False, None, True) — roaming is the 4th positional arg
    assert len(fallback_args) == 4, (
        f"Expected 4 positional args, got {len(fallback_args)}: {fallback_args}"
    )
    assert fallback_args[3] is True, f"4th arg (roaming) must be True, got {fallback_args[3]}"
    assert fallback_args[2] is None, f"3rd arg (version) must be None, got {fallback_args[2]}"


def test_get_cursor_config_path_windows_prefers_existing_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import arcade_cli.configure as configure_mod

    appdata_path = tmp_path / "AppData" / "Roaming" / "Cursor" / "mcp.json"
    home_path = tmp_path / ".cursor" / "mcp.json"
    home_path.parent.mkdir(parents=True, exist_ok=True)
    home_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(configure_mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        configure_mod,
        "_get_windows_cursor_config_paths",
        lambda: [appdata_path, home_path],
    )

    assert configure_mod.get_cursor_config_path() == home_path


# ---------------------------------------------------------------------------
# _warn_overwrite()
# ---------------------------------------------------------------------------


def test_warn_overwrite_prints_when_entry_exists() -> None:
    """Should print a yellow warning when the server entry already exists."""
    from arcade_cli.console import Console

    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    import arcade_cli.configure as configure_mod

    orig = configure_mod.console
    configure_mod.console = test_console
    try:
        config = {"mcpServers": {"demo": {"command": "old"}}}
        _warn_overwrite(config, "mcpServers", "demo", Path("/fake/cursor.json"))
    finally:
        configure_mod.console = orig

    output = buf.getvalue()
    assert "demo" in output
    assert "already exists" in output


def test_warn_overwrite_silent_when_no_entry() -> None:
    """Should NOT print anything when the server entry doesn't exist."""
    from arcade_cli.console import Console

    buf = StringIO()
    test_console = Console(file=buf, force_terminal=True)

    # Temporarily monkey-patch the module-level console used by _warn_overwrite.
    import arcade_cli.configure as configure_mod

    orig = configure_mod.console
    configure_mod.console = test_console
    try:
        config: dict = {"mcpServers": {}}
        _warn_overwrite(config, "mcpServers", "new_server", Path("/fake/mcp.json"))
    finally:
        configure_mod.console = orig

    assert buf.getvalue() == "", "No output expected when entry doesn't exist"


def test_warn_overwrite_message_content() -> None:
    """Verify the warning message mentions the server name."""
    from arcade_cli.console import Console

    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    import arcade_cli.configure as configure_mod

    orig = configure_mod.console
    configure_mod.console = test_console
    try:
        config = {"servers": {"my_srv": {"command": "old"}}}
        _warn_overwrite(config, "servers", "my_srv", Path("/fake/vscode.json"))
    finally:
        configure_mod.console = orig

    output = buf.getvalue()
    assert "my_srv" in output
    assert "already exists" in output
    assert "--name" in output


# ---------------------------------------------------------------------------
# UTF-8 config I/O
# ---------------------------------------------------------------------------


def test_config_written_as_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Config files must be written with UTF-8 encoding, including non-ASCII paths."""
    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "config.json"

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )

    # Read the file as raw bytes and verify UTF-8 BOM is absent and content
    # decodes cleanly as UTF-8.
    raw = config_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM should not be present"
    decoded = raw.decode("utf-8")  # Should not raise
    data = json.loads(decoded)
    assert "mcpServers" in data
    assert "demo" in data["mcpServers"]


def test_config_roundtrip_preserves_unicode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Write a config with Unicode, then overwrite and verify it still decodes."""
    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "config.json"

    # Seed with Unicode content
    config_path.write_text(
        json.dumps({"mcpServers": {"caf\u00e9": {"command": "old"}}}),
        encoding="utf-8",
    )

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )

    data = json.loads(config_path.read_text(encoding="utf-8"))
    # Original Unicode entry should be preserved alongside the new one.
    assert "caf\u00e9" in data["mcpServers"]
    assert "demo" in data["mcpServers"]


def test_cursor_config_stdio_and_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "cursor.json"

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )
    config = _load_json(config_path)
    entry = config["mcpServers"]["demo"]
    _assert_stdio_entry(entry)

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="http",
        host="local",
        port=8123,
        config_path=config_path,
    )
    config = _load_json(config_path)
    entry = config["mcpServers"]["demo"]
    assert entry["type"] == "stream"
    assert entry["url"] == "http://localhost:8123/mcp"


def test_cursor_config_stdio_uses_absolute_uv_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import arcade_cli.configure as configure_mod

    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "cursor.json"
    monkeypatch.setattr(
        configure_mod.shutil,
        "which",
        lambda executable: r"C:\Tools\uv.exe" if executable == "uv" else None,
    )

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )

    config = _load_json(config_path)
    assert config["mcpServers"]["demo"]["command"] == r"C:\Tools\uv.exe"


def test_cursor_windows_writes_compatibility_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import arcade_cli.configure as configure_mod

    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)

    appdata_path = tmp_path / "AppData" / "Roaming" / "Cursor" / "mcp.json"
    home_path = tmp_path / ".cursor" / "mcp.json"
    appdata_path.parent.mkdir(parents=True, exist_ok=True)
    home_path.parent.mkdir(parents=True, exist_ok=True)
    appdata_path.write_text(
        json.dumps({"mcpServers": {"appdata_only": {"command": "x"}}}),
        encoding="utf-8",
    )
    home_path.write_text(
        json.dumps({"mcpServers": {"home_only": {"command": "y"}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(configure_mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(configure_mod, "get_cursor_config_path", lambda: appdata_path)
    monkeypatch.setattr(
        configure_mod,
        "_get_windows_cursor_config_paths",
        lambda: [appdata_path, home_path],
    )

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
    )

    appdata_config = _load_json(appdata_path)
    home_config = _load_json(home_path)
    assert "demo" in appdata_config["mcpServers"]
    assert "demo" in home_config["mcpServers"]
    assert "appdata_only" in appdata_config["mcpServers"]
    assert "home_only" in home_config["mcpServers"]


def test_cursor_windows_explicit_config_does_not_write_compatibility_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import arcade_cli.configure as configure_mod

    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)

    explicit_path = tmp_path / "custom" / "cursor.json"
    appdata_path = tmp_path / "AppData" / "Roaming" / "Cursor" / "mcp.json"
    home_path = tmp_path / ".cursor" / "mcp.json"

    monkeypatch.setattr(configure_mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(configure_mod, "get_cursor_config_path", lambda: appdata_path)
    monkeypatch.setattr(
        configure_mod,
        "_get_windows_cursor_config_paths",
        lambda: [appdata_path, home_path],
    )

    configure_client(
        client="cursor",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=explicit_path,
    )

    assert explicit_path.exists()
    assert not appdata_path.exists()
    assert not home_path.exists()


def test_vscode_config_stdio_and_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "vscode.json"

    configure_client(
        client="vscode",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )
    config = _load_json(config_path)
    entry = config["servers"]["demo"]
    _assert_stdio_entry(entry)

    configure_client(
        client="vscode",
        entrypoint_file="server.py",
        server_name="demo",
        transport="http",
        host="local",
        port=8123,
        config_path=config_path,
    )
    config = _load_json(config_path)
    entry = config["servers"]["demo"]
    assert entry["type"] == "http"
    assert entry["url"] == "http://localhost:8123/mcp"


def test_claude_config_stdio_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_entrypoint(tmp_path)
    config_path = tmp_path / "claude.json"

    configure_client(
        client="claude",
        entrypoint_file="server.py",
        server_name="demo",
        transport="stdio",
        host="local",
        port=8000,
        config_path=config_path,
    )
    config = _load_json(config_path)
    entry = config["mcpServers"]["demo"]
    _assert_stdio_entry(entry)

    with pytest.raises(ValueError, match="Claude Desktop only supports stdio"):
        configure_client(
            client="claude",
            entrypoint_file="server.py",
            server_name="demo",
            transport="http",
            host="local",
            port=8000,
            config_path=config_path,
        )


# ---------------------------------------------------------------------------
# configure_*_arcade() — gateway configuration
# ---------------------------------------------------------------------------


class TestConfigureClaudeArcade:
    def test_writes_gateway_url_and_headers(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        configure_claude_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="tok_abc",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert entry["headers"]["Authorization"] == "Bearer tok_abc"

    def test_preserves_existing_entries(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        config_path.write_text(
            json.dumps({"mcpServers": {"existing": {"command": "old"}}}),
            encoding="utf-8",
        )
        configure_claude_arcade(
            server_name="new-gw",
            gateway_url="https://api.arcade.dev/mcp/new-gw",
            auth_token="tok",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert "existing" in config["mcpServers"]
        assert "new-gw" in config["mcpServers"]


class TestConfigureCursorArcade:
    def test_writes_sse_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cursor.json"
        configure_cursor_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="tok_abc",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["type"] == "sse"
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert entry["headers"]["Authorization"] == "Bearer tok_abc"


class TestConfigureVscodeArcade:
    def test_writes_http_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "vscode.json"
        configure_vscode_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="tok_abc",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["servers"]["my-gw"]
        assert entry["type"] == "http"
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert entry["headers"]["Authorization"] == "Bearer tok_abc"


# ---------------------------------------------------------------------------
# configure_client_gateway() — dispatcher
# ---------------------------------------------------------------------------


class TestConfigureClientGateway:
    @pytest.mark.parametrize(
        "client,section",
        [
            ("claude", "mcpServers"),
            ("cursor", "mcpServers"),
            ("vscode", "servers"),
            ("windsurf", "mcpServers"),
            ("amazonq", "mcpServers"),
        ],
    )
    def test_dispatches_to_correct_client(self, tmp_path: Path, client: str, section: str) -> None:
        config_path = tmp_path / f"{client}.json"
        configure_client_gateway(
            client=client,
            server_name="test-gw",
            gateway_url="https://api.arcade.dev/mcp/test-gw",
            auth_token="tok",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert "test-gw" in config[section]


# ---------------------------------------------------------------------------
# configure_client_toolkit() — toolkit stdio config
# ---------------------------------------------------------------------------


class TestConfigureClientToolkit:
    def test_claude_toolkit_stdio(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        configure_client_toolkit(
            client="claude",
            server_name="arcade-github",
            tool_packages=["github"],
            config_path=config_path,
            transport="stdio",
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["arcade-github"]
        assert "command" in entry
        assert "--tool-package" in entry["args"]
        assert "github" in entry["args"]

    def test_claude_toolkit_http(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        configure_client_toolkit(
            client="claude",
            server_name="arcade-github",
            tool_packages=["github"],
            config_path=config_path,
            transport="http",
            port=8000,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["arcade-github"]
        assert entry["url"] == "http://localhost:8000/mcp"
        assert "command" not in entry

    def test_cursor_toolkit_http(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cursor.json"
        configure_client_toolkit(
            client="cursor",
            server_name="arcade-github",
            tool_packages=["github"],
            config_path=config_path,
            transport="http",
            port=9000,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["arcade-github"]
        assert entry["type"] == "sse"
        assert entry["url"] == "http://localhost:9000/mcp"

    def test_vscode_toolkit_stdio(self, tmp_path: Path) -> None:
        config_path = tmp_path / "vscode.json"
        configure_client_toolkit(
            client="vscode",
            server_name="arcade-tools",
            tool_packages=["github", "slack"],
            config_path=config_path,
            transport="stdio",
        )
        config = _load_json(config_path)
        entry = config["servers"]["arcade-tools"]
        assert "command" in entry
        args_str = " ".join(str(a) for a in entry["args"])
        assert "github" in args_str
        assert "slack" in args_str

    def test_vscode_toolkit_http(self, tmp_path: Path) -> None:
        config_path = tmp_path / "vscode.json"
        configure_client_toolkit(
            client="vscode",
            server_name="arcade-tools",
            tool_packages=["github", "slack"],
            config_path=config_path,
            transport="http",
        )
        config = _load_json(config_path)
        entry = config["servers"]["arcade-tools"]
        assert entry["type"] == "http"
        assert entry["url"] == "http://localhost:8000/mcp"

    def test_windsurf_toolkit_stdio(self, tmp_path: Path) -> None:
        config_path = tmp_path / "windsurf.json"
        configure_client_toolkit(
            client="windsurf",
            server_name="arcade-github",
            tool_packages=["github"],
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["arcade-github"]
        assert "command" in entry
        assert "--tool-package" in entry["args"]

    def test_amazonq_toolkit_stdio(self, tmp_path: Path) -> None:
        config_path = tmp_path / "amazonq.json"
        configure_client_toolkit(
            client="amazonq",
            server_name="arcade-github",
            tool_packages=["github"],
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["arcade-github"]
        assert "command" in entry
        assert "--tool-package" in entry["args"]


# ---------------------------------------------------------------------------
# get_toolkit_stdio_config()
# ---------------------------------------------------------------------------


class TestGetToolkitStdioConfig:
    def test_uses_uv_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import arcade_cli.configure as configure_mod

        monkeypatch.setattr(
            configure_mod.shutil, "which", lambda exe: "/usr/bin/uv" if exe == "uv" else None
        )
        config = get_toolkit_stdio_config(["github"], "arcade-github")
        assert config["command"] == "/usr/bin/uv"
        assert "tool" in config["args"]
        assert "run" in config["args"]
        assert "--tool-package" in config["args"]
        assert "github" in config["args"]

    def test_falls_back_to_python(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import arcade_cli.configure as configure_mod

        monkeypatch.setattr(configure_mod.shutil, "which", lambda exe: None)
        config = get_toolkit_stdio_config(["github"], "arcade-github")
        assert "python" in config["command"].lower() or config["command"].endswith("python3")
        assert "--tool-package" in config["args"]


# ---------------------------------------------------------------------------
# get_toolkit_http_config()
# ---------------------------------------------------------------------------


class TestGetToolkitHttpConfig:
    def test_claude_config(self) -> None:
        config = get_toolkit_http_config("claude", ["github"])
        assert config["url"] == "http://localhost:8000/mcp"
        assert "type" not in config

    def test_cursor_config(self) -> None:
        config = get_toolkit_http_config("cursor", ["github"])
        assert config["type"] == "sse"
        assert config["url"] == "http://localhost:8000/mcp"

    def test_vscode_config(self) -> None:
        config = get_toolkit_http_config("vscode", ["github"])
        assert config["type"] == "http"
        assert config["url"] == "http://localhost:8000/mcp"

    def test_custom_port(self) -> None:
        config = get_toolkit_http_config("claude", ["github"], port=9000)
        assert config["url"] == "http://localhost:9000/mcp"


# ---------------------------------------------------------------------------
# New clients: Windsurf, Amazon Q, Zed
# ---------------------------------------------------------------------------


class TestConfigureWindsurfArcade:
    def test_writes_mcpservers_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "windsurf.json"
        configure_windsurf_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert "headers" not in entry

    def test_with_api_key(self, tmp_path: Path) -> None:
        config_path = tmp_path / "windsurf.json"
        configure_windsurf_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="arc_test",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert config["mcpServers"]["my-gw"]["headers"]["Authorization"] == "Bearer arc_test"


class TestConfigureAmazonqArcade:
    def test_writes_mcpservers_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "amazonq.json"
        configure_amazonq_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"

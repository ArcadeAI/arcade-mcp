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
    _upsert_codex_mcp_server,
    _warn_overwrite,
    configure_amazonq_arcade,
    configure_claude_code_arcade,
    configure_client,
    configure_client_gateway,
    configure_client_toolkit,
    configure_codex_arcade,
    configure_cursor_arcade,
    configure_gemini_arcade,
    configure_opencode_arcade,
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


class TestConfigureClaudeCodeArcade:
    def test_writes_http_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        configure_claude_code_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="tok_abc",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["type"] == "http"
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert entry["headers"]["Authorization"] == "Bearer tok_abc"

    def test_preserves_existing_entries(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        config_path.write_text(
            json.dumps({
                "projects": {"/some/path": {"mcpServers": {}}},
                "mcpServers": {"existing": {"type": "http", "url": "https://old"}},
            }),
            encoding="utf-8",
        )
        configure_claude_code_arcade(
            server_name="new-gw",
            gateway_url="https://api.arcade.dev/mcp/new-gw",
            auth_token="tok",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert "existing" in config["mcpServers"]
        assert "new-gw" in config["mcpServers"]
        assert "projects" in config


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
            ("claude-code", "mcpServers"),
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


# ---------------------------------------------------------------------------
# Codex CLI
# ---------------------------------------------------------------------------


class TestUpsertCodexMcpServer:
    def test_appends_when_missing(self) -> None:
        result = _upsert_codex_mcp_server("", "arcade", {"url": "https://example.com/mcp"})
        assert result == '[mcp_servers.arcade]\nurl = "https://example.com/mcp"\n'

    def test_preserves_other_content(self) -> None:
        existing = "# user config\nmodel = \"gpt-5\"\n\n[mcp_servers.other]\nurl = \"https://other\"\n"
        result = _upsert_codex_mcp_server(
            existing, "arcade", {"url": "https://arcade", "bearer_token": "tok"}
        )
        # Original content is preserved verbatim
        assert "# user config" in result
        assert 'model = "gpt-5"' in result
        assert "[mcp_servers.other]" in result
        assert 'url = "https://other"' in result
        # New section added at the end
        assert "[mcp_servers.arcade]" in result
        assert 'url = "https://arcade"' in result
        assert 'bearer_token = "tok"' in result

    def test_replaces_existing_section(self) -> None:
        existing = (
            "[mcp_servers.arcade]\n"
            'url = "https://old"\n'
            'bearer_token = "old_tok"\n'
            "\n"
            "[mcp_servers.other]\n"
            'url = "https://other"\n'
        )
        result = _upsert_codex_mcp_server(existing, "arcade", {"url": "https://new"})
        # Old url/bearer_token are gone; new url is present
        assert 'url = "https://old"' not in result
        assert 'bearer_token = "old_tok"' not in result
        assert 'url = "https://new"' in result
        # Other section is untouched
        assert "[mcp_servers.other]" in result
        assert 'url = "https://other"' in result

    def test_escapes_special_characters_in_values(self) -> None:
        result = _upsert_codex_mcp_server(
            "", "arcade", {"url": 'https://example.com/"weird"\\path'}
        )
        # Backslashes and quotes must be escaped per TOML basic-string rules
        assert r'url = "https://example.com/\"weird\"\\path"' in result


class TestConfigureCodexArcade:
    def test_writes_url_only(self, tmp_path: Path) -> None:
        config_path = tmp_path / "codex_config.toml"
        configure_codex_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        content = config_path.read_text(encoding="utf-8")
        assert "[mcp_servers.my-gw]" in content
        assert 'url = "https://api.arcade.dev/mcp/my-gw"' in content
        assert "bearer_token" not in content

    def test_writes_bearer_token_when_auth_token_given(self, tmp_path: Path) -> None:
        config_path = tmp_path / "codex_config.toml"
        configure_codex_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="arc_abc",
            config_path=config_path,
        )
        content = config_path.read_text(encoding="utf-8")
        assert 'bearer_token = "arc_abc"' in content

    def test_preserves_existing_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "codex_config.toml"
        config_path.write_text(
            'model = "gpt-5"\n\n[mcp_servers.keep]\nurl = "https://keep"\n',
            encoding="utf-8",
        )
        configure_codex_arcade(
            server_name="new-gw",
            gateway_url="https://new",
            config_path=config_path,
        )
        content = config_path.read_text(encoding="utf-8")
        assert 'model = "gpt-5"' in content
        assert "[mcp_servers.keep]" in content
        assert 'url = "https://keep"' in content
        assert "[mcp_servers.new-gw]" in content


# ---------------------------------------------------------------------------
# OpenCode
# ---------------------------------------------------------------------------


class TestConfigureOpencodeArcade:
    def test_writes_remote_mcp_entry(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        configure_opencode_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcp"]["my-gw"]
        assert entry["type"] == "remote"
        assert entry["url"] == "https://api.arcade.dev/mcp/my-gw"
        assert entry["enabled"] is True
        assert "headers" not in entry

    def test_with_auth_token(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        configure_opencode_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="arc_test",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert config["mcp"]["my-gw"]["headers"]["Authorization"] == "Bearer arc_test"

    def test_preserves_existing_entries(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        config_path.write_text(
            json.dumps({
                "$schema": "https://opencode.ai/config.json",
                "mcp": {"existing": {"type": "remote", "url": "https://old"}},
                "theme": "dark",
            }),
            encoding="utf-8",
        )
        configure_opencode_arcade(
            server_name="new-gw",
            gateway_url="https://new",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert "existing" in config["mcp"]
        assert "new-gw" in config["mcp"]
        assert config["$schema"] == "https://opencode.ai/config.json"
        assert config["theme"] == "dark"


# ---------------------------------------------------------------------------
# Gemini CLI
# ---------------------------------------------------------------------------


class TestConfigureGeminiArcade:
    def test_writes_httpurl_entry(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        configure_gemini_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        config = _load_json(config_path)
        entry = config["mcpServers"]["my-gw"]
        assert entry["httpUrl"] == "https://api.arcade.dev/mcp/my-gw"
        # Gemini CLI uses httpUrl (not url) for streamable HTTP
        assert "url" not in entry
        assert "headers" not in entry

    def test_with_auth_token(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        configure_gemini_arcade(
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            auth_token="arc_test",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert config["mcpServers"]["my-gw"]["headers"]["Authorization"] == "Bearer arc_test"

    def test_preserves_existing_entries(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        config_path.write_text(
            json.dumps({
                "mcpServers": {"keep": {"httpUrl": "https://keep"}},
                "theme": "Default",
            }),
            encoding="utf-8",
        )
        configure_gemini_arcade(
            server_name="new-gw",
            gateway_url="https://new",
            config_path=config_path,
        )
        config = _load_json(config_path)
        assert "keep" in config["mcpServers"]
        assert "new-gw" in config["mcpServers"]
        assert config["theme"] == "Default"


# ---------------------------------------------------------------------------
# configure_client_gateway dispatch for new clients
# ---------------------------------------------------------------------------


class TestConfigureClientGatewayNewClients:
    def test_dispatches_to_codex(self, tmp_path: Path) -> None:
        config_path = tmp_path / "codex_config.toml"
        configure_client_gateway(
            client="codex",
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        content = config_path.read_text(encoding="utf-8")
        assert "[mcp_servers.my-gw]" in content

    def test_dispatches_to_opencode(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        configure_client_gateway(
            client="opencode",
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        assert "my-gw" in _load_json(config_path)["mcp"]

    def test_dispatches_to_gemini(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        configure_client_gateway(
            client="gemini",
            server_name="my-gw",
            gateway_url="https://api.arcade.dev/mcp/my-gw",
            config_path=config_path,
        )
        assert "my-gw" in _load_json(config_path)["mcpServers"]


# ---------------------------------------------------------------------------
# Preservation contract: configure_*_arcade must never delete or mutate any
# pre-existing entry in the user's config. It may only add or replace the
# single entry keyed by server_name. These tests compare the full original
# config to the post-write config to prove no unrelated data was lost.
# ---------------------------------------------------------------------------


def _rich_claude_config() -> dict:
    """Config that mimics the real ~/.claude.json: many top-level keys,
    projects map with per-project mcpServers, and a user-scope mcpServers
    with a pre-existing entry we must not disturb."""
    return {
        "numStartups": 42,
        "userID": "abc-123",
        "hasCompletedOnboarding": True,
        "mcpServers": {
            "keep-me": {"type": "http", "url": "https://keep.example.com/mcp"},
            "also-keep": {
                "type": "http",
                "url": "https://also.example.com/mcp",
                "headers": {"Authorization": "Bearer OLD_TOKEN"},
            },
        },
        "projects": {
            "/Users/me/project-a": {
                "allowedTools": ["Read", "Write"],
                "mcpServers": {
                    "project-scoped": {"type": "http", "url": "https://proj.example"},
                },
                "hasTrustDialogAccepted": True,
            },
            "/Users/me/project-b": {
                "mcpContextUris": [],
                "lastCost": 0.12,
            },
        },
        "oauthAccount": {"email": "user@example.com"},
        "cachedDynamicConfigs": {"featureFlag": True},
    }


def _rich_opencode_config() -> dict:
    return {
        "$schema": "https://opencode.ai/config.json",
        "theme": "github-dark",
        "model": "claude-3-5-sonnet",
        "mcp": {
            "keep-me": {
                "type": "remote",
                "url": "https://keep.example.com",
                "enabled": True,
            },
            "stdio-server": {
                "type": "local",
                "command": ["node", "server.js"],
            },
        },
        "provider": {"anthropic": {"apiKey": "{env:ANTHROPIC_API_KEY}"}},
        "experimental": {"something": True},
    }


def _rich_gemini_config() -> dict:
    return {
        "theme": "Default",
        "selectedAuthType": "oauth-personal",
        "mcpServers": {
            "keep-me": {"httpUrl": "https://keep.example.com/mcp"},
            "with-auth": {
                "httpUrl": "https://auth.example.com/mcp",
                "headers": {"Authorization": "Bearer OLD"},
                "timeout": 10000,
            },
        },
        "contextFileName": "GEMINI.md",
        "fileFiltering": {"respectGitIgnore": True},
    }


def _rich_codex_toml() -> str:
    """A realistic Codex config.toml with comments, top-level keys, other
    server sections, and an unrelated table. All of this must survive."""
    return (
        "# User preferences for Codex\n"
        'model = "gpt-5"\n'
        'model_provider = "openai"\n'
        "approval_policy = \"on-request\"\n"
        "\n"
        "[model_providers.openai]\n"
        'name = "OpenAI"\n'
        'base_url = "https://api.openai.com/v1"\n'
        "\n"
        "[mcp_servers.keep-me]\n"
        'url = "https://keep.example.com/mcp"\n'
        'bearer_token = "KEEP_TOKEN"\n'
        "\n"
        "# Another server, don't touch\n"
        "[mcp_servers.also-keep]\n"
        'url = "https://also.example.com/mcp"\n'
        "\n"
        "[shell_environment_policy]\n"
        'inherit = "core"\n'
    )


def _assert_only_added(original: dict, updated: dict, parent_key: str, server_name: str) -> None:
    """Assert that ``updated`` equals ``original`` except for a single new or
    replaced entry at ``updated[parent_key][server_name]``. Every other key
    and nested value at every depth must be byte-for-byte identical."""
    # Top-level keys: same set
    assert set(updated.keys()) == set(original.keys()), (
        f"top-level keys changed: added {set(updated) - set(original)}, "
        f"removed {set(original) - set(updated)}"
    )
    # Every top-level key except parent_key is deeply equal
    for key in original:
        if key == parent_key:
            continue
        assert updated[key] == original[key], f"key '{key}' was modified"
    # Inside parent_key, every server except server_name is preserved exactly
    for name, entry in original[parent_key].items():
        if name == server_name:
            continue
        assert name in updated[parent_key], f"existing server '{name}' was deleted"
        assert updated[parent_key][name] == entry, f"existing server '{name}' was mutated"


class TestClaudeCodePreservesEverything:
    def test_preserves_full_original_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        original = _rich_claude_config()
        config_path.write_text(json.dumps(original), encoding="utf-8")

        configure_claude_code_arcade(
            server_name="new-gw",
            gateway_url="https://new.example/mcp",
            auth_token="new_tok",
            config_path=config_path,
        )

        updated = _load_json(config_path)
        _assert_only_added(original, updated, "mcpServers", "new-gw")
        # New entry has the expected shape
        assert updated["mcpServers"]["new-gw"] == {
            "type": "http",
            "url": "https://new.example/mcp",
            "headers": {"Authorization": "Bearer new_tok"},
        }

    def test_repeated_writes_accumulate(self, tmp_path: Path) -> None:
        """Running connect twice with different names keeps both entries."""
        config_path = tmp_path / "claude.json"
        configure_claude_code_arcade(
            server_name="first", gateway_url="https://first/mcp", config_path=config_path
        )
        configure_claude_code_arcade(
            server_name="second", gateway_url="https://second/mcp", config_path=config_path
        )
        servers = _load_json(config_path)["mcpServers"]
        assert set(servers) == {"first", "second"}
        assert servers["first"]["url"] == "https://first/mcp"
        assert servers["second"]["url"] == "https://second/mcp"

    def test_replacing_same_name_leaves_others_intact(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"
        original = _rich_claude_config()
        config_path.write_text(json.dumps(original), encoding="utf-8")

        # Write the same server name twice — should only replace that one entry.
        configure_claude_code_arcade(
            server_name="keep-me", gateway_url="https://replacement/mcp", config_path=config_path
        )
        updated = _load_json(config_path)
        # keep-me was replaced
        assert updated["mcpServers"]["keep-me"] == {
            "type": "http",
            "url": "https://replacement/mcp",
        }
        # Everything else survived
        assert updated["mcpServers"]["also-keep"] == original["mcpServers"]["also-keep"]
        assert updated["projects"] == original["projects"]
        assert updated["oauthAccount"] == original["oauthAccount"]


class TestOpencodePreservesEverything:
    def test_preserves_full_original_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        original = _rich_opencode_config()
        config_path.write_text(json.dumps(original), encoding="utf-8")

        configure_opencode_arcade(
            server_name="new-gw",
            gateway_url="https://new.example/mcp",
            auth_token="new_tok",
            config_path=config_path,
        )

        updated = _load_json(config_path)
        _assert_only_added(original, updated, "mcp", "new-gw")
        assert updated["mcp"]["new-gw"] == {
            "type": "remote",
            "url": "https://new.example/mcp",
            "enabled": True,
            "headers": {"Authorization": "Bearer new_tok"},
        }

    def test_repeated_writes_accumulate(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        configure_opencode_arcade(
            server_name="first", gateway_url="https://first", config_path=config_path
        )
        configure_opencode_arcade(
            server_name="second", gateway_url="https://second", config_path=config_path
        )
        entries = _load_json(config_path)["mcp"]
        assert set(entries) == {"first", "second"}


class TestGeminiPreservesEverything:
    def test_preserves_full_original_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        original = _rich_gemini_config()
        config_path.write_text(json.dumps(original), encoding="utf-8")

        configure_gemini_arcade(
            server_name="new-gw",
            gateway_url="https://new.example/mcp",
            auth_token="new_tok",
            config_path=config_path,
        )

        updated = _load_json(config_path)
        _assert_only_added(original, updated, "mcpServers", "new-gw")
        assert updated["mcpServers"]["new-gw"] == {
            "httpUrl": "https://new.example/mcp",
            "headers": {"Authorization": "Bearer new_tok"},
        }

    def test_repeated_writes_accumulate(self, tmp_path: Path) -> None:
        config_path = tmp_path / "gemini.json"
        configure_gemini_arcade(
            server_name="first", gateway_url="https://first", config_path=config_path
        )
        configure_gemini_arcade(
            server_name="second", gateway_url="https://second", config_path=config_path
        )
        entries = _load_json(config_path)["mcpServers"]
        assert set(entries) == {"first", "second"}


class TestCodexPreservesEverything:
    def test_preserves_full_original_toml(self, tmp_path: Path) -> None:
        """Every line from the original TOML (comments, other tables, other
        mcp_servers sections) must still be present after writing a new
        ``[mcp_servers.new-gw]`` section."""
        config_path = tmp_path / "codex_config.toml"
        original = _rich_codex_toml()
        config_path.write_text(original, encoding="utf-8")

        configure_codex_arcade(
            server_name="new-gw",
            gateway_url="https://new.example/mcp",
            auth_token="new_tok",
            config_path=config_path,
        )

        updated = config_path.read_text(encoding="utf-8")
        # Every non-empty line from the original must appear verbatim.
        for line in original.splitlines():
            if line == "":
                continue
            assert line in updated, f"Line lost from Codex config: {line!r}"
        # And the new section was added.
        assert "[mcp_servers.new-gw]" in updated
        assert 'url = "https://new.example/mcp"' in updated
        assert 'bearer_token = "new_tok"' in updated

    def test_replacing_existing_leaves_sibling_sections_intact(self, tmp_path: Path) -> None:
        """Replacing ``[mcp_servers.keep-me]`` must not disturb
        ``[mcp_servers.also-keep]`` or unrelated tables."""
        config_path = tmp_path / "codex_config.toml"
        original = _rich_codex_toml()
        config_path.write_text(original, encoding="utf-8")

        configure_codex_arcade(
            server_name="keep-me",
            gateway_url="https://replacement/mcp",
            config_path=config_path,
        )

        updated = config_path.read_text(encoding="utf-8")
        # The old URL and token for keep-me are gone (replaced).
        assert 'url = "https://keep.example.com/mcp"' not in updated
        assert "KEEP_TOKEN" not in updated
        # The replacement is present.
        assert 'url = "https://replacement/mcp"' in updated
        # Sibling section survives intact.
        assert "[mcp_servers.also-keep]" in updated
        assert 'url = "https://also.example.com/mcp"' in updated
        # Non-mcp tables and top-level keys survive.
        assert "[model_providers.openai]" in updated
        assert 'model = "gpt-5"' in updated
        assert "[shell_environment_policy]" in updated
        assert "# User preferences for Codex" in updated

    def test_repeated_writes_accumulate(self, tmp_path: Path) -> None:
        config_path = tmp_path / "codex_config.toml"
        configure_codex_arcade(
            server_name="first", gateway_url="https://first", config_path=config_path
        )
        configure_codex_arcade(
            server_name="second", gateway_url="https://second", config_path=config_path
        )
        content = config_path.read_text(encoding="utf-8")
        assert "[mcp_servers.first]" in content
        assert "[mcp_servers.second]" in content
        assert 'url = "https://first"' in content
        assert 'url = "https://second"' in content

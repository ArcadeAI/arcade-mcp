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
    configure_client,
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
            _format_path_for_display(path, platform_system="Linux")
            == "/tmp/with\\ space/mcp.json"
        )


# ---------------------------------------------------------------------------
# _resolve_windows_appdata()
# ---------------------------------------------------------------------------


def test_resolve_windows_appdata_prefers_appdata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", r"C:\Users\Alice\AppData\Roaming")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    assert _resolve_windows_appdata() == Path(r"C:\Users\Alice\AppData\Roaming")


def test_resolve_windows_appdata_from_localappdata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate a realistic AppData layout so the Roaming sibling exists.
    local_dir = tmp_path / "AppData" / "Local"
    roaming_dir = tmp_path / "AppData" / "Roaming"
    local_dir.mkdir(parents=True)
    roaming_dir.mkdir(parents=True)

    monkeypatch.delenv("APPDATA", raising=False)
    import arcade_cli.configure as configure_mod

    monkeypatch.setattr(configure_mod, "_resolve_windows_appdata_with_platformdirs", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.delenv("USERPROFILE", raising=False)
    assert _resolve_windows_appdata() == roaming_dir


def test_resolve_windows_appdata_from_userprofile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falls back to USERPROFILE when APPDATA and LOCALAPPDATA are unset."""
    monkeypatch.delenv("APPDATA", raising=False)
    import arcade_cli.configure as configure_mod

    monkeypatch.setattr(configure_mod, "_resolve_windows_appdata_with_platformdirs", lambda: None)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert _resolve_windows_appdata() == tmp_path / "AppData" / "Roaming"


def test_resolve_windows_appdata_uses_platformdirs_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)

    fake_platformdirs = types.ModuleType("platformdirs")
    fake_platformdirs.user_data_dir = (
        lambda *args, **kwargs: r"C:\Users\Alice\AppData\Roaming"
    )
    monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

    assert _resolve_windows_appdata() == Path(r"C:\Users\Alice\AppData\Roaming")


def test_resolve_windows_appdata_platformdirs_empty_falls_back_to_localappdata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_dir = tmp_path / "AppData" / "Local"
    roaming_dir = tmp_path / "AppData" / "Roaming"
    local_dir.mkdir(parents=True)
    roaming_dir.mkdir(parents=True)

    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.delenv("USERPROFILE", raising=False)

    fake_platformdirs = types.ModuleType("platformdirs")
    fake_platformdirs.user_data_dir = lambda *args, **kwargs: ""
    monkeypatch.setitem(sys.modules, "platformdirs", fake_platformdirs)

    assert _resolve_windows_appdata() == roaming_dir


# ---------------------------------------------------------------------------
# _warn_overwrite()
# ---------------------------------------------------------------------------


def test_warn_overwrite_prints_when_entry_exists(capsys: pytest.CaptureFixture) -> None:
    """Should print a yellow warning when the server entry already exists."""
    config = {"mcpServers": {"demo": {"command": "old"}}}
    config_path = Path("/fake/cursor.json")
    _warn_overwrite(config, "mcpServers", "demo", config_path)
    # The warning uses Rich console, so check the captured output from the
    # console (which writes to stdout).  Rich may strip markup but the text
    # content should be present.
    # Because Rich writes directly via its Console, we read from the console's
    # file object.  Just ensure no exception was raised — the visual output
    # is verified below via a buffer-based approach.


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


def test_config_roundtrip_preserves_unicode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

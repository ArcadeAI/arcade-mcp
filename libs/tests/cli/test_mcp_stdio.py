"""Exercise the CLI's subprocess handoff with real MCP pipes."""

import os
import sys
from datetime import timedelta
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_mcp_stdio_preserves_client_pipes(tmp_path: Path) -> None:
    (tmp_path / "server.py").write_text(
        "from arcade_tdk import tool\n\n"
        "@tool\n"
        "def check_stdio() -> str:\n"
        '    """Return a fixed response through the CLI transport."""\n'
        '    return "stdio-ok"\n',
        encoding="utf-8",
    )
    # Bound env-file discovery and avoid the unrelated first-run CLI notice.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "cli-stdio-test"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    config_dir = tmp_path / "arcade-config"
    config_dir.mkdir()
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP"}
    }
    environment.update({
        "ARCADE_WORK_DIR": str(config_dir),
        "ARCADE_USAGE_TRACKING": "0",
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
    })
    executable = Path(sys.executable).with_name(
        "arcade.exe" if sys.platform == "win32" else "arcade"
    )
    parameters = StdioServerParameters(
        command=str(executable),
        args=["mcp", "stdio", "--cwd", str(tmp_path), "--env-file", str(env_file)],
        env=environment,
        cwd=tmp_path,
    )

    with (
        anyio.fail_after(30),
        (tmp_path / "server-stderr.log").open("w", encoding="utf-8") as errors,
    ):
        async with stdio_client(parameters, errlog=errors) as (reader, writer):
            async with ClientSession(
                reader, writer, read_timeout_seconds=timedelta(seconds=15)
            ) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 1
                result = await session.call_tool(tools.tools[0].name, {})
                assert not result.isError
                assert result.structuredContent == {"result": "stdio-ok"}

"""Connect command for configuring MCP clients."""

import json
import logging
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

import typer
from arcade_mcp_server.settings import find_env_file
from dotenv import dotenv_values

from arcade_cli.console import console

logger = logging.getLogger(__name__)


def is_wsl() -> bool:
    """Check if running in Windows Subsystem for Linux."""
    # Check for WSL environment variable
    if os.environ.get("WSL_DISTRO_NAME"):
        return True

    # Check /proc/version for WSL indicators
    try:
        with open("/proc/version", encoding="utf-8") as f:
            version_info = f.read().lower()
            return "microsoft" in version_info or "wsl" in version_info
    except (FileNotFoundError, PermissionError):
        return False


def get_windows_username() -> str | None:
    """Get the Windows username when running in WSL."""
    try:
        # Try to get username from Windows environment via cmd.exe
        # Note: cmd.exe is safe to use here as it's a Windows system binary available in WSL
        result = subprocess.run(
            ["cmd.exe", "/c", "echo", "%USERNAME%"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            username = result.stdout.strip()
            # Remove any carriage returns
            username = username.replace("\r", "")
            if username and username != "%USERNAME%":
                return username
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def _resolve_windows_appdata() -> Path:
    """Resolve the Windows roaming AppData directory via ``platformdirs``.

    ``platformdirs`` is the de-facto standard Python library for resolving
    OS-specific user directories.  On Windows it reads the ``APPDATA``
    environment variable (and the Windows registry as a fallback), so a
    single call covers every real-world scenario.
    """
    from platformdirs import user_data_dir

    try:
        result = user_data_dir(appname=None, appauthor=False, roaming=True)
    except TypeError:
        # Older platformdirs versions require positional args only.
        # Signature: user_data_dir(appname, appauthor, version, roaming)
        logger.debug("platformdirs raised TypeError; retrying with positional args")
        result = user_data_dir(None, False, None, True)

    return Path(result)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Return paths in order, removing duplicates (case-insensitive on Windows)."""
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(str(path))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _get_windows_cursor_config_paths() -> list[Path]:
    """Return known Windows Cursor config locations (primary first)."""
    return _dedupe_paths([
        _resolve_windows_appdata() / "Cursor" / "mcp.json",
        Path.home() / ".cursor" / "mcp.json",
    ])


def _format_path_for_display(path: Path, platform_system: str | None = None) -> str:
    path_str = str(path)
    if " " in path_str:
        system = platform_system or platform.system()
        if system == "Windows":
            return f'"{path_str}"'
        return path_str.replace(" ", "\\ ")
    return path_str


def _warn_overwrite(config: dict, section: str, server_name: str, config_path: Path) -> None:
    if section in config and server_name in config[section]:
        config_display = _format_path_for_display(config_path)
        console.print(
            f"[yellow]Warning: MCP server '{server_name}' already exists in {config_display}. "
            "This will overwrite the existing entry. Use --name to keep both.[/yellow]"
        )


def get_claude_config_path() -> Path:
    """Get the Claude Desktop configuration file path."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif system == "Windows":
        return _resolve_windows_appdata() / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        # Check if we're in WSL - if so, use Windows path
        if is_wsl():
            username = get_windows_username()
            if username:
                # Use the Windows AppData path accessible via WSL mount
                return Path(
                    f"/mnt/c/Users/{username}/AppData/Roaming/Claude/claude_desktop_config.json"
                )
            else:
                console.print(
                    "[yellow]Warning: Running in WSL but couldn't determine Windows username. "
                    "Using Linux path instead. Claude Desktop may not detect this configuration.[/yellow]"
                )

        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_cursor_config_path() -> Path:
    """Get the Cursor configuration file path."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / ".cursor" / "mcp.json"
    elif system == "Windows":
        candidates = _get_windows_cursor_config_paths()
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]
    else:  # Linux
        # Check if we're in WSL - if so, use Windows path
        if is_wsl():
            username = get_windows_username()
            if username:
                # Use the Windows AppData path accessible via WSL mount
                return Path(f"/mnt/c/Users/{username}/AppData/Roaming/Cursor/mcp.json")
            else:
                console.print(
                    "[yellow]Warning: Running in WSL but couldn't determine Windows username. "
                    "Using Linux path instead. Cursor may not detect this configuration.[/yellow]"
                )

        return Path.home() / ".config" / "Cursor" / "mcp.json"


def get_vscode_config_path() -> Path:
    """Get the VS Code configuration file path."""
    # Paths to global 'Default User' MCP configuration file
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
    elif system == "Windows":
        return _resolve_windows_appdata() / "Code" / "User" / "mcp.json"
    else:  # Linux
        # Check if we're in WSL - if so, use Windows path
        if is_wsl():
            username = get_windows_username()
            if username:
                # Use the Windows AppData path accessible via WSL mount
                return Path(f"/mnt/c/Users/{username}/AppData/Roaming/Code/User/mcp.json")
            else:
                console.print(
                    "[yellow]Warning: Running in WSL but couldn't determine Windows username. "
                    "Using Linux path instead. VS Code may not detect this configuration.[/yellow]"
                )

        return Path.home() / ".config" / "Code" / "User" / "mcp.json"


def get_windsurf_config_path() -> Path:
    """Get the Windsurf (Codeium) configuration file path."""
    return Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def get_amazonq_config_path() -> Path:
    """Get the Amazon Q Developer configuration file path."""
    return Path.home() / ".aws" / "amazonq" / "mcp.json"


def is_uv_installed() -> bool:
    """Check if uv is installed and available in PATH."""
    return shutil.which("uv") is not None


def get_tool_secrets() -> dict:
    """Get tool secrets from .env file for stdio servers.

    Discovers .env file by traversing upward from the current directory
    through parent directories until a .env file is found.

    Returns:
        Dictionary of environment variables from the .env file, or empty dict if not found.
    """
    env_path = find_env_file()
    if env_path is not None:
        return dotenv_values(env_path)
    return {}


def find_python_interpreter() -> Path:
    """
    Find the Python interpreter in the virtual environment.

    NOTE: This function assumes it is called from the project root directory (where .venv lives).
    Currently, callers like `arcade deploy` enforce this by requiring pyproject.toml in cwd.
    If this requirement is relaxed in the future, this function should be updated to:
      1. Accept a project_root parameter, OR
      2. Honor VIRTUAL_ENV / UV_PROJECT_ENVIRONMENT env vars, OR
      3. Search upward from cwd to find pyproject.toml and resolve .venv relative to that
    """
    venv_python = None
    # Check for .venv first (uv default)
    if (Path.cwd() / ".venv").exists():
        system = platform.system()
        if system == "Windows":
            venv_python = Path.cwd() / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = Path.cwd() / ".venv" / "bin" / "python"

    # Fall back to system python if no venv found
    if not venv_python or not venv_python.exists():
        console.print("[yellow]Warning: No .venv found, using system python[/yellow]")
        import sys

        venv_python = Path(sys.executable)

    return venv_python


def get_stdio_config(entrypoint_file: str, server_name: str) -> dict:
    """Get the appropriate stdio configuration based on whether uv is installed."""
    server_file = Path.cwd() / entrypoint_file

    uv_executable = shutil.which("uv")
    if uv_executable:
        return {
            # Use the absolute uv path so GUI clients can launch reliably even
            # when they were started with a different PATH than the shell.
            "command": uv_executable,
            "args": [
                "run",
                "--directory",
                str(Path.cwd()),
                "python",
                entrypoint_file,
            ],
            "env": get_tool_secrets(),
        }
    else:
        console.print(
            "[yellow]Warning: uv is not installed. Install uv for the best experience with arcade configure CLI command.[/yellow]"
        )
        venv_python = find_python_interpreter()
        return {
            "command": str(venv_python),
            "args": [str(server_file)],
            "env": get_tool_secrets(),
        }


def configure_claude_local(
    entrypoint_file: str, server_name: str, port: int = 8000, config_path: Path | None = None
) -> None:
    """Configure Claude Desktop to add a local MCP server to the configuration."""
    config_path = config_path or get_claude_config_path()

    # Handle both absolute and relative config paths
    if config_path and not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new one
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    # Add or update MCP servers configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    _warn_overwrite(config, "mcpServers", server_name, config_path)

    # Claude Desktop uses stdio transport
    config["mcpServers"][server_name] = get_stdio_config(entrypoint_file, server_name)

    # Write updated config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Claude Desktop by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = _format_path_for_display(config_path)
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    console.print(
        f"   Server file: {_format_path_for_display(Path.cwd() / entrypoint_file)}",
        style="dim",
    )
    if is_uv_installed():
        console.print("   Using uv to run server", style="dim")
    else:
        console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart Claude Desktop for changes to take effect.", style="yellow")


def _configure_mcpservers_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None,
    config_path: Path,
    display_name: str,
) -> None:
    """Shared helper for clients that use the ``mcpServers`` JSON key.

    Used by Claude Desktop, Windsurf, and Amazon Q which all share
    the same config format — only the file path and display name differ.
    """
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    _warn_overwrite(config, "mcpServers", server_name, config_path)

    entry: dict = {"url": gateway_url}
    if auth_token:
        entry["headers"] = {"Authorization": f"Bearer {auth_token}"}
    config["mcpServers"][server_name] = entry

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]Configured {display_name} with Arcade gateway '{server_name}'[/green]")
    console.print(f"   Gateway URL: {gateway_url}", style="dim")
    console.print(f"   Config file: {_format_path_for_display(config_path)}", style="dim")
    console.print(f"   Restart {display_name} for changes to take effect.", style="yellow")


def configure_claude_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure Claude Desktop to connect to an Arcade Cloud MCP gateway."""
    _configure_mcpservers_arcade(
        server_name,
        gateway_url,
        auth_token,
        config_path or get_claude_config_path(),
        "Claude Desktop",
    )


def configure_cursor_local(
    entrypoint_file: str,
    server_name: str,
    transport: str,
    port: int = 8000,
    config_path: Path | None = None,
) -> None:
    """Configure Cursor to add a local MCP server to the configuration."""

    def http_config(server_name: str, port: int = 8000) -> dict:
        return {
            "name": server_name,
            "type": "stream",  # Cursor prefers stream
            "url": f"http://localhost:{port}/mcp",
        }

    if config_path is not None:
        target_paths = [config_path]
    elif platform.system() == "Windows":
        primary_path = get_cursor_config_path()
        target_paths = _dedupe_paths([primary_path, *_get_windows_cursor_config_paths()])
    else:
        target_paths = [get_cursor_config_path()]

    # Handle both absolute and relative config paths.
    resolved_target_paths: list[Path] = []
    for path in target_paths:
        resolved_target_paths.append(path if path.is_absolute() else Path.cwd() / path)

    server_config = (
        get_stdio_config(entrypoint_file, server_name)
        if transport == "stdio"
        else http_config(server_name, port)
    )

    for idx, config_path in enumerate(resolved_target_paths):
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new one
        config = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

        # Add or update MCP servers configuration
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        if idx == 0:
            _warn_overwrite(config, "mcpServers", server_name, config_path)

        config["mcpServers"][server_name] = server_config

        # Write updated config
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    primary_config_path = resolved_target_paths[0]

    console.print(
        f"✅ Configured Cursor by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = _format_path_for_display(primary_config_path)
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    compatibility_paths = resolved_target_paths[1:]
    if compatibility_paths:
        compatibility_display = ", ".join(
            _format_path_for_display(path) for path in compatibility_paths
        )
        console.print(
            f"   Also updated compatibility config file(s): {compatibility_display}",
            style="dim",
        )
    if transport == "http":
        console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    elif transport == "stdio":
        if is_uv_installed():
            console.print("   Using uv to run server", style="dim")
        else:
            console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart Cursor for changes to take effect.", style="yellow")


def configure_cursor_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure Cursor to connect to an Arcade Cloud MCP gateway."""
    if config_path is not None:
        target_paths = [config_path]
    elif platform.system() == "Windows":
        primary_path = get_cursor_config_path()
        target_paths = _dedupe_paths([primary_path, *_get_windows_cursor_config_paths()])
    else:
        target_paths = [get_cursor_config_path()]

    resolved_target_paths: list[Path] = []
    for path in target_paths:
        resolved_target_paths.append(path if path.is_absolute() else Path.cwd() / path)

    server_config: dict = {"type": "sse", "url": gateway_url}
    if auth_token:
        server_config["headers"] = {"Authorization": f"Bearer {auth_token}"}

    for idx, target in enumerate(resolved_target_paths):
        target.parent.mkdir(parents=True, exist_ok=True)

        config: dict = {}
        if target.exists():
            with open(target, encoding="utf-8") as f:
                config = json.load(f)

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        if idx == 0:
            _warn_overwrite(config, "mcpServers", server_name, target)

        config["mcpServers"][server_name] = server_config

        with open(target, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    primary_config_path = resolved_target_paths[0]
    console.print(f"[green]Configured Cursor with Arcade gateway '{server_name}'[/green]")
    console.print(f"   Gateway URL: {gateway_url}", style="dim")
    console.print(
        f"   Config file: {_format_path_for_display(primary_config_path)}",
        style="dim",
    )
    console.print("   Restart Cursor for changes to take effect.", style="yellow")


def configure_vscode_local(
    entrypoint_file: str,
    server_name: str,
    transport: str,
    port: int = 8000,
    config_path: Path | None = None,
) -> None:
    """Configure VS Code to add a local MCP server to the configuration."""

    def http_config(port: int = 8000) -> dict:
        return {
            "type": "http",
            "url": f"http://localhost:{port}/mcp",
        }

    config_path = config_path or get_vscode_config_path()

    # Handle both absolute and relative config paths
    if config_path and not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Load existing config or create new one
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"\n\tFailed to load MCP configuration file at {_format_path_for_display(config_path)} "
                    f"\n\tThe file contains invalid JSON: {e}. "
                    "\n\tPlease check the file format or delete it to create a new configuration."
                )

    # Add or update MCP servers configuration
    if "servers" not in config:
        config["servers"] = {}

    _warn_overwrite(config, "servers", server_name, config_path)

    config["servers"][server_name] = (
        get_stdio_config(entrypoint_file, server_name)
        if transport == "stdio"
        else http_config(port)
    )

    # Write updated config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured VS Code by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = _format_path_for_display(config_path)
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    if transport == "http":
        console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    elif transport == "stdio":
        if is_uv_installed():
            console.print("   Using uv to run server", style="dim")
        else:
            console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart VS Code for changes to take effect.", style="yellow")


def configure_vscode_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure VS Code to connect to an Arcade Cloud MCP gateway."""
    config_path = config_path or get_vscode_config_path()
    if config_path and not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"\n\tFailed to load MCP configuration file at {_format_path_for_display(config_path)} "
                    f"\n\tThe file contains invalid JSON: {e}. "
                    "\n\tPlease check the file format or delete it to create a new configuration."
                )

    if "servers" not in config:
        config["servers"] = {}

    _warn_overwrite(config, "servers", server_name, config_path)

    entry: dict = {"type": "http", "url": gateway_url}
    if auth_token:
        entry["headers"] = {"Authorization": f"Bearer {auth_token}"}
    config["servers"][server_name] = entry

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]Configured VS Code with Arcade gateway '{server_name}'[/green]")
    console.print(f"   Gateway URL: {gateway_url}", style="dim")
    console.print(f"   Config file: {_format_path_for_display(config_path)}", style="dim")
    console.print("   Restart VS Code for changes to take effect.", style="yellow")


def configure_windsurf_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure Windsurf to connect to an Arcade Cloud MCP gateway."""
    _configure_mcpservers_arcade(
        server_name, gateway_url, auth_token, config_path or get_windsurf_config_path(), "Windsurf"
    )


def configure_amazonq_arcade(
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure Amazon Q Developer to connect to an Arcade Cloud MCP gateway."""
    _configure_mcpservers_arcade(
        server_name, gateway_url, auth_token, config_path or get_amazonq_config_path(), "Amazon Q"
    )


def get_toolkit_stdio_config(tool_packages: list[str], server_name: str) -> dict:
    """Build a stdio config that runs ``arcade mcp stdio`` with ``--tool-package`` flags.

    This configuration is used by MCP clients (Claude Desktop, Cursor, VS Code) to
    launch an Arcade MCP server via ``uv tool run`` (or direct Python) with one or more
    toolkit packages loaded.
    """
    uv_executable = shutil.which("uv")
    if uv_executable:
        args = ["tool", "run", "arcade-mcp", "mcp", "stdio"]
        for pkg in tool_packages:
            args.extend(["--tool-package", pkg])
        return {
            "command": uv_executable,
            "args": args,
            "env": get_tool_secrets(),
        }
    else:
        import sys

        args = ["-m", "arcade_mcp_server", "stdio"]
        for pkg in tool_packages:
            args.extend(["--tool-package", pkg])
        return {
            "command": sys.executable,
            "args": args,
            "env": get_tool_secrets(),
        }


def get_toolkit_http_config(client: str, tool_packages: list[str], port: int = 8000) -> dict:
    """Build an HTTP/SSE config entry pointing at a local ``arcade mcp http`` server.

    The server must be started separately, e.g.::

        arcade mcp http --tool-package github --port 8000

    Each MCP client uses a slightly different JSON shape:
    - Claude Desktop / Cursor: ``url`` (+ optional ``type`` for Cursor)
    - VS Code: ``type: "http"`` + ``url``
    """
    url = f"http://localhost:{port}/mcp"
    client_lower = client.lower()
    if client_lower == "cursor":
        return {"type": "sse", "url": url}
    elif client_lower == "vscode":
        return {"type": "http", "url": url}
    else:
        # Claude Desktop and anything else: just url
        return {"url": url}


def configure_client_gateway(
    client: str,
    server_name: str,
    gateway_url: str,
    auth_token: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Configure an MCP client to connect to an Arcade Cloud gateway.

    If *auth_token* is ``None`` the config contains only the URL and the MCP
    client handles OAuth natively.  If an API key is provided it is written as
    a ``Bearer`` header.
    """
    client_lower = client.lower()
    dispatch = {
        "claude": configure_claude_arcade,
        "cursor": configure_cursor_arcade,
        "vscode": configure_vscode_arcade,
        "windsurf": configure_windsurf_arcade,
        "amazonq": configure_amazonq_arcade,
    }
    func = dispatch.get(client_lower)
    if not func:
        supported = ", ".join(sorted(dispatch))
        raise typer.BadParameter(f"Unknown client: {client}. Supported clients: {supported}.")
    func(server_name, gateway_url, auth_token, config_path)


def configure_client_toolkit(
    client: str,
    server_name: str,
    tool_packages: list[str],
    config_path: Path | None = None,
    transport: str = "stdio",
    port: int = 8000,
) -> None:
    """Configure an MCP client for Arcade toolkits.

    When *transport* is ``"stdio"`` (default), writes a config that launches
    ``arcade mcp stdio --tool-package <pkg>`` via the MCP client.

    When *transport* is ``"http"``, writes a config pointing the client at
    ``http://localhost:{port}/mcp``.  The user must start the server separately::

        arcade mcp http --tool-package <pkg> --port <port>
    """
    client_lower = client.lower()
    if transport == "http":
        server_config = get_toolkit_http_config(client, tool_packages, port)
    else:
        server_config = get_toolkit_stdio_config(tool_packages, server_name)

    if client_lower == "claude":
        _config_path = config_path or get_claude_config_path()
        if _config_path and not _config_path.is_absolute():
            _config_path = Path.cwd() / _config_path
        _config_path.parent.mkdir(parents=True, exist_ok=True)

        config: dict = {}
        if _config_path.exists():
            with open(_config_path, encoding="utf-8") as f:
                config = json.load(f)
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        _warn_overwrite(config, "mcpServers", server_name, _config_path)
        config["mcpServers"][server_name] = server_config
        with open(_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        console.print(
            f"[green]Configured Claude Desktop with Arcade toolkits: {', '.join(tool_packages)}[/green]"
        )
        console.print(f"   Config file: {_format_path_for_display(_config_path)}", style="dim")
        console.print("   Restart Claude Desktop for changes to take effect.", style="yellow")

    elif client_lower == "cursor":
        if config_path is not None:
            target_paths = [config_path]
        elif platform.system() == "Windows":
            primary_path = get_cursor_config_path()
            target_paths = _dedupe_paths([primary_path, *_get_windows_cursor_config_paths()])
        else:
            target_paths = [get_cursor_config_path()]

        resolved_paths: list[Path] = []
        for path in target_paths:
            resolved_paths.append(path if path.is_absolute() else Path.cwd() / path)

        for idx, target in enumerate(resolved_paths):
            target.parent.mkdir(parents=True, exist_ok=True)
            config = {}
            if target.exists():
                with open(target, encoding="utf-8") as f:
                    config = json.load(f)
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            if idx == 0:
                _warn_overwrite(config, "mcpServers", server_name, target)
            config["mcpServers"][server_name] = server_config
            with open(target, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

        console.print(
            f"[green]Configured Cursor with Arcade toolkits: {', '.join(tool_packages)}[/green]"
        )
        console.print(f"   Config file: {_format_path_for_display(resolved_paths[0])}", style="dim")
        console.print("   Restart Cursor for changes to take effect.", style="yellow")

    elif client_lower == "vscode":
        _config_path = config_path or get_vscode_config_path()
        if _config_path and not _config_path.is_absolute():
            _config_path = Path.cwd() / _config_path
        _config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {}
        if _config_path.exists():
            with open(_config_path, encoding="utf-8") as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"\n\tFailed to load MCP configuration file at {_format_path_for_display(_config_path)} "
                        f"\n\tThe file contains invalid JSON: {e}. "
                        "\n\tPlease check the file format or delete it to create a new configuration."
                    )
        if "servers" not in config:
            config["servers"] = {}
        _warn_overwrite(config, "servers", server_name, _config_path)
        config["servers"][server_name] = server_config
        with open(_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        console.print(
            f"[green]Configured VS Code with Arcade toolkits: {', '.join(tool_packages)}[/green]"
        )
        console.print(f"   Config file: {_format_path_for_display(_config_path)}", style="dim")
        console.print("   Restart VS Code for changes to take effect.", style="yellow")

    elif client_lower in ("windsurf", "amazonq"):
        path_fn = (
            get_windsurf_config_path if client_lower == "windsurf" else get_amazonq_config_path
        )
        display = "Windsurf" if client_lower == "windsurf" else "Amazon Q"
        _config_path = config_path or path_fn()
        if _config_path and not _config_path.is_absolute():
            _config_path = Path.cwd() / _config_path
        _config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {}
        if _config_path.exists():
            with open(_config_path, encoding="utf-8") as f:
                config = json.load(f)
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        _warn_overwrite(config, "mcpServers", server_name, _config_path)
        config["mcpServers"][server_name] = server_config
        with open(_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        console.print(
            f"[green]Configured {display} with Arcade toolkits: {', '.join(tool_packages)}[/green]"
        )
        console.print(f"   Config file: {_format_path_for_display(_config_path)}", style="dim")
        console.print(f"   Restart {display} for changes to take effect.", style="yellow")

    else:
        supported = "claude, cursor, vscode, windsurf, amazonq"
        raise typer.BadParameter(f"Unknown client: {client}. Supported clients: {supported}.")


def configure_client(
    client: str,
    entrypoint_file: str,
    server_name: str | None = None,
    transport: str = "stdio",
    host: str = "local",
    port: int = 8000,
    config_path: Path | None = None,
) -> None:
    """
    Configure an MCP client to connect to a server.

    Args:
        client: The MCP client to configure (claude, cursor, vscode)
        entrypoint_file: The name of the Python file in the current directory that runs the server. This file must run the server when invoked directly. Only used for stdio servers.
        server_name: Name of the server to add to the configuration
        transport: The transport to use for the MCP server configuration
        host: The host of the server to configure (local or arcade)
        port: Port for local HTTP servers (default: 8000)
        config_path: Custom path to the MCP client configuration file
    """
    if not server_name:
        # Use the name of the current directory as the server name
        server_name = Path.cwd().name

    if transport == "stdio":
        if "/" in entrypoint_file or "\\" in entrypoint_file:
            raise ValueError(
                f"Entrypoint file '{entrypoint_file}' must be a filename in the current "
                f"directory, not a path"
            )

        if not (Path.cwd() / entrypoint_file).exists():
            raise ValueError(f"Entrypoint file '{entrypoint_file}' is not in the current directory")

        if not bool(re.match(r"^[a-zA-Z0-9_-]+\.py$", entrypoint_file)):
            raise ValueError(f"Entrypoint file '{entrypoint_file}' is not a valid Python file name")

    client_lower = client.lower()

    if host == "arcade":
        console.print(
            "Use [bold]arcade connect[/bold] to connect to Arcade Cloud gateways.\n"
            "Example: [bold]arcade connect claude --gateway my-gateway[/bold]",
            style="yellow",
        )
        return

    if client_lower == "claude":
        if transport != "stdio":
            raise ValueError("Claude Desktop only supports stdio transport via configuration file")
        configure_claude_local(entrypoint_file, server_name, port, config_path)
    elif client_lower == "cursor":
        configure_cursor_local(entrypoint_file, server_name, transport, port, config_path)
    elif client_lower == "vscode":
        configure_vscode_local(entrypoint_file, server_name, transport, port, config_path)
    else:
        raise typer.BadParameter(
            f"Unknown client: {client}. Supported clients: claude, cursor, vscode."
        )

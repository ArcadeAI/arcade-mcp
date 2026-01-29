"""Connect command for configuring MCP clients."""

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

import typer
from dotenv import dotenv_values
from rich.console import Console

console = Console()


def is_wsl() -> bool:
    """Check if running in Windows Subsystem for Linux."""
    # Check for WSL environment variable
    if os.environ.get("WSL_DISTRO_NAME"):
        return True

    # Check /proc/version for WSL indicators
    try:
        with open("/proc/version") as f:
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
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
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
        return Path(os.environ["APPDATA"]) / "Cursor" / "mcp.json"
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
        return Path(os.environ["APPDATA"]) / "Code" / "User" / "mcp.json"
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


def is_uv_installed() -> bool:
    """Check if uv is installed and available in PATH."""
    return shutil.which("uv") is not None


def get_tool_secrets() -> dict:
    """Only useful for stdio servers, because HTTP servers load in envvars at runtime"""
    # TODO: Allow for a custom .env file to be used
    env_path = Path.cwd() / ".env"
    if env_path.exists():
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

    if is_uv_installed():
        return {
            "command": "uv",
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
        with open(config_path) as f:
            config = json.load(f)

    # Add or update MCP servers configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Claude Desktop uses stdio transport
    config["mcpServers"][server_name] = get_stdio_config(entrypoint_file, server_name)

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Claude Desktop by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    console.print(f"   Server file: {Path.cwd() / entrypoint_file}", style="dim")
    if is_uv_installed():
        console.print("   Using uv to run server", style="dim")
    else:
        console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart Claude Desktop for changes to take effect.", style="yellow")


def configure_claude_arcade(
    server_name: str, transport: str, config_path: Path | None = None
) -> None:
    """Configure Claude Desktop to add an Arcade Cloud MCP server to the configuration."""
    # This would connect to the Arcade Cloud to get the server URL
    # For now, this is a placeholder
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


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

    config_path = config_path or get_cursor_config_path()

    # Handle both absolute and relative config paths
    if config_path and not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new one
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    # Add or update MCP servers configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"][server_name] = (
        get_stdio_config(entrypoint_file, server_name)
        if transport == "stdio"
        else http_config(server_name, port)
    )

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Cursor by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    if transport == "http":
        console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    elif transport == "stdio":
        if is_uv_installed():
            console.print("   Using uv to run server", style="dim")
        else:
            console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart Cursor for changes to take effect.", style="yellow")


def configure_cursor_arcade(
    server_name: str, transport: str, config_path: Path | None = None
) -> None:
    """Configure Cursor to add an Arcade Cloud MCP server to the configuration."""
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


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
        with open(config_path) as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"\n\tFailed to load MCP configuration file at {config_path.as_posix()} "
                    f"\n\tThe file contains invalid JSON: {e}. "
                    "\n\tPlease check the file format or delete it to create a new configuration."
                )

    # Add or update MCP servers configuration
    if "servers" not in config:
        config["servers"] = {}

    config["servers"][server_name] = (
        get_stdio_config(entrypoint_file, server_name)
        if transport == "stdio"
        else http_config(port)
    )

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured VS Code by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    if transport == "http":
        console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    elif transport == "stdio":
        if is_uv_installed():
            console.print("   Using uv to run server", style="dim")
        else:
            console.print(f"   Python interpreter: {find_python_interpreter()}", style="dim")
    console.print("   Restart VS Code for changes to take effect.", style="yellow")


def configure_vscode_arcade(server_name: str, transport: str, path: Path | None = None) -> None:
    """Configure VS Code to add an Arcade Cloud MCP server to the configuration."""
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


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
        if not bool(re.match(r"^[a-zA-Z0-9_-]+\.py$", entrypoint_file)):
            raise ValueError(f"Entrypoint file '{entrypoint_file}' is not a valid Python file name")

        if not (Path.cwd() / entrypoint_file).exists():
            raise ValueError(f"Entrypoint file '{entrypoint_file}' is not in the current directory")

    client_lower = client.lower()

    if client_lower == "claude":
        if transport != "stdio":
            raise ValueError("Claude Desktop only supports stdio transport via configuration file")
        if host == "local":
            configure_claude_local(entrypoint_file, server_name, port, config_path)
        else:
            configure_claude_arcade(server_name, transport, config_path)
    elif client_lower == "cursor":
        if host == "local":
            configure_cursor_local(entrypoint_file, server_name, transport, port, config_path)
        else:
            configure_cursor_arcade(server_name, transport, config_path)
    elif client_lower == "vscode":
        if host == "local":
            configure_vscode_local(entrypoint_file, server_name, transport, port, config_path)
        else:
            configure_vscode_arcade(server_name, transport, config_path)
    else:
        raise typer.BadParameter(
            f"Unknown client: {client}. Supported clients: claude, cursor, vscode."
        )

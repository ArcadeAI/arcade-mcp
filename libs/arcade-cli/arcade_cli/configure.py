"""Connect command for configuring MCP clients."""

import json
import os
import platform
from pathlib import Path

import typer
from rich.console import Console

console = Console()


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
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_cursor_config_path() -> Path:
    """Get the Cursor configuration file path."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / ".cursor" / "mcp.json"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "Cursor" / "mcp.json"
    else:  # Linux
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
        return Path.home() / ".config" / "Code" / "User" / "mcp.json"


def configure_claude_local(server_name: str, port: int = 8000, path: Path | None = None) -> None:
    """Configure Claude Desktop to add a local MCP server to the configuration."""
    config_path = path or get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new one
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    # Add or update MCP servers configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"][server_name] = {
        "command": "python",
        "args": ["-m", "arcade_mcp_server", "stream"],
        "url": f"http://localhost:{port}/mcp",
    }

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Claude Desktop by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    console.print("   Restart Claude Desktop for changes to take effect.", style="yellow")


def configure_claude_arcade(server_name: str, path: Path | None = None) -> None:
    """Configure Claude Desktop to add an Arcade Cloud MCP server to the configuration."""
    # This would connect to the Arcade Cloud to get the server URL
    # For now, this is a placeholder
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


def configure_cursor_local(server_name: str, port: int = 8000, path: Path | None = None) -> None:
    """Configure Cursor to add a local MCP server to the configuration."""
    config_path = path or get_cursor_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new one
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    # Add or update MCP servers configuration
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"][server_name] = {
        "name": server_name,
        "type": "stream",  # Cursor prefers stream
        "url": f"http://localhost:{port}/mcp",
    }

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Cursor by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    console.print("   Restart Cursor for changes to take effect.", style="yellow")


def configure_cursor_arcade(server_name: str, path: Path | None = None) -> None:
    """Configure Cursor to add an Arcade Cloud MCP server to the configuration."""
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


def configure_vscode_local(server_name: str, port: int = 8000, path: Path | None = None) -> None:
    """Configure VS Code to add a local MCP server to the configuration."""
    config_path = path or get_vscode_config_path()
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

    config["servers"][server_name] = {
        "type": "http",
        "url": f"http://localhost:{port}/mcp",
    }

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured VS Code by adding local MCP server '{server_name}' to the configuration",
        style="green",
    )
    config_file_path = config_path.as_posix().replace(" ", "\\ ")
    console.print(f"   MCP client config file: {config_file_path}", style="dim")
    console.print(f"   MCP Server URL: http://localhost:{port}/mcp", style="dim")
    console.print("   Restart VS Code for changes to take effect.", style="yellow")


def configure_vscode_arcade(server_name: str, path: Path | None = None) -> None:
    """Configure VS Code to add an Arcade Cloud MCP server to the configuration."""
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


def configure_client(
    client: str,
    server_name: str | None = None,
    from_local: bool = False,
    from_arcade: bool = False,
    port: int = 8000,
    path: Path | None = None,
) -> None:
    """
    Configure an MCP client to connect to a server.

    Args:
        client: The MCP client to configure (claude, cursor, vscode)
        server_name: Name of the server to add to the configuration
        from_local: Add a local server to the configuration
        from_arcade: Add an Arcade Cloud server to the configuration
        port: Port for local servers (default: 8000)
        path: Custom path to the MCP client configuration file
    """
    if not from_local and not from_arcade:
        raise typer.BadParameter("Must specify either --from-local or --from-arcade")

    if from_local and from_arcade:
        raise typer.BadParameter("Cannot specify both --from-local and --from-arcade")

    # Default server name if not provided
    if not server_name:
        # Try to detect from current directory
        server_name = Path.cwd().name if Path("server.py").exists() else "arcade-mcp-server"

    client_lower = client.lower()

    if client_lower == "claude":
        if from_local:
            configure_claude_local(server_name, port, path)
        else:
            configure_claude_arcade(server_name, path)
    elif client_lower == "cursor":
        if from_local:
            configure_cursor_local(server_name, port, path)
        else:
            configure_cursor_arcade(server_name, path)
    elif client_lower == "vscode":
        if from_local:
            configure_vscode_local(server_name, port, path)
        else:
            configure_vscode_arcade(server_name, path)
    else:
        raise typer.BadParameter(
            f"Unknown client: {client}. Supported clients: claude, cursor, vscode."
        )

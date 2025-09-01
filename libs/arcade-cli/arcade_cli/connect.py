"""Connect command for configuring MCP clients."""

import json
import os
import platform
from pathlib import Path
from typing import Optional

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
    """Get the Cursor configuration directory path."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / ".cursor" / "mcp"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "Cursor" / "mcp"
    else:  # Linux
        return Path.home() / ".config" / "Cursor" / "mcp"


def connect_claude_local(server_name: str, port: int = 8000) -> None:
    """Configure Claude Desktop to connect to a local MCP server."""
    config_path = get_claude_config_path()
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
        "args": ["-m", "arcade_mcp", "stream"],
        "url": f"http://localhost:{port}/mcp",
    }

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Claude Desktop to connect to local MCP server '{server_name}'",
        style="green",
    )
    console.print(f"   URL: http://localhost:{port}/mcp", style="dim")
    console.print("   Restart Claude Desktop for changes to take effect.", style="yellow")


def connect_claude_arcade(server_name: str) -> None:
    """Configure Claude Desktop to connect to an Arcade Cloud MCP server."""
    # This would connect to the Arcade Cloud to get the server URL
    # For now, this is a placeholder
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


def connect_cursor_local(server_name: str, port: int = 8000) -> None:
    """Configure Cursor to connect to a local MCP server."""
    config_dir = get_cursor_config_path()
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create MCP configuration file for Cursor
    config_file = config_dir / f"{server_name}.json"

    config = {
        "name": server_name,
        "type": "sse",  # Cursor prefers stream
        "url": f"http://localhost:{port}/mcp",
    }

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(
        f"✅ Configured Cursor to connect to local MCP server '{server_name}'",
        style="green",
    )
    console.print(f"   URL: http://localhost:{port}/mcp", style="dim")
    console.print("   Restart Cursor for changes to take effect.", style="yellow")


def connect_cursor_arcade(server_name: str) -> None:
    """Configure Cursor to connect to an Arcade Cloud MCP server."""
    console.print("[red]Connecting to Arcade Cloud servers not yet implemented[/red]")


def connect_client(
    client: str,
    server_name: Optional[str] = None,
    from_local: bool = False,
    from_arcade: bool = False,
    port: int = 8000,
) -> None:
    """
    Connect an MCP client to a server.

    Args:
        client: The MCP client to configure (claude, cursor, vscode)
        server_name: Name of the server to connect to
        from_local: Connect to a local server
        from_arcade: Connect to an Arcade Cloud server
        port: Port for local servers (default: 8000)
    """
    if not from_local and not from_arcade:
        console.print("[red]Must specify either --from-local or --from-arcade[/red]")
        raise typer.Exit(1)

    if from_local and from_arcade:
        console.print("[red]Cannot specify both --from-local and --from-arcade[/red]")
        raise typer.Exit(1)

    # Default server name if not provided
    if not server_name:
        # Try to detect from current directory
        server_name = Path.cwd().name if Path("server.py").exists() else "arcade-mcp-server"

    client_lower = client.lower()

    if client_lower == "claude":
        if from_local:
            connect_claude_local(server_name, port)
        else:
            connect_claude_arcade(server_name)
    elif client_lower == "cursor":
        if from_local:
            connect_cursor_local(server_name, port)
        else:
            connect_cursor_arcade(server_name)
    elif client_lower == "vscode":
        console.print("[yellow]VS Code MCP configuration coming soon![/yellow]")
        console.print("For now, configure VS Code manually to use stdio transport.")
    else:
        console.print(f"[red]Unknown client: {client}[/red]")
        console.print("Supported clients: claude, cursor, vscode")
        raise typer.Exit(1)

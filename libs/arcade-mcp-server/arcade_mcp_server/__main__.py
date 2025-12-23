"""
Arcade MCP Server Runner

Provides a unified interface for running MCP servers with either:
- stdio transport for direct client connections
- HTTP/SSE transport with FastAPI for web-based connections

Usage:
    # Run with stdio transport
    python -m arcade_mcp_server stdio

    # Run with HTTP transport (default)
    python -m arcade_mcp_server

    # Run with specific toolkit
    python -m arcade_mcp_server --toolkit my_toolkit

    # Run in development mode with hot reload
    python -m arcade_mcp_server --reload --debug
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from arcade_core.catalog import ToolCatalog
from arcade_core.discovery import discover_tools
from arcade_core.toolkit import ToolkitLoadError
from dotenv import load_dotenv
from loguru import logger

from arcade_mcp_server.logging_utils import intercept_standard_logging
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings


def setup_logging(level: str = "INFO", stdio_mode: bool = False) -> None:
    """Configure logging with Loguru."""
    # Remove existing handlers
    logger.remove()

    # In stdio mode, use stderr (stdout is reserved for JSON-RPC)
    sink = sys.stderr if stdio_mode else sys.stdout

    # Add handler with appropriate format
    if level == "DEBUG":
        format_str = "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <cyan>{name}:{line}</cyan> | <level>{message}</level>"
    else:
        format_str = (
            "<level>{level: <8}</level> | <green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        )

    logger.add(
        sink,
        format=format_str,
        level=level,
        colorize=(not stdio_mode),
        diagnose=(level == "DEBUG"),
    )

    # Intercept standard logging
    intercept_standard_logging()


def initialize_tool_catalog(
    tool_package: str | None = None,
    show_packages: bool = False,
    discover_installed: bool = False,
    server_name: str | None = None,
    server_version: str | None = None,
) -> ToolCatalog:
    """
    Discover and load tools from various sources.

    Returns a ToolCatalog or exits with a friendly error if nothing found.
    """
    try:
        catalog = discover_tools(
            tool_package=tool_package,
            show_packages=show_packages,
            discover_installed=discover_installed,
            server_name=server_name,
            server_version=server_version,
        )
    except ToolkitLoadError as exc:
        logger.error(str(exc))
        sys.exit(1)

    total_tools = len(catalog)
    if total_tools == 0:
        logger.error("No tools found. Create Python files with @tool decorated functions.")
        sys.exit(1)

    logger.info(f"Total tools loaded: {total_tools}")
    return catalog


async def run_stdio_server(
    catalog: ToolCatalog,
    debug: bool = False,
    env_file: str | None = None,
    settings: MCPSettings | None = None,
    **kwargs: Any,
) -> None:
    """Run MCP server with stdio transport."""
    from arcade_mcp_server.transports.stdio import StdioTransport

    # Load settings
    # Ensure env from provided .env is loaded for stdio runs as well
    if env_file:
        load_dotenv(env_file)
        logger.debug(f"Loaded environment variables from --env-file={env_file}")

    # Use provided settings or load from environment
    if settings is None:
        settings = MCPSettings.from_env()

    if debug:
        settings.debug = True
        settings.middleware.enable_logging = True
        settings.middleware.log_level = "DEBUG"

    # Debug log settings and env var names (without values)
    try:
        tool_env_keys = sorted(settings.tool_secrets().keys())
        logger.debug(
            f"Arcade settings: \n\
                ARCADE_ENVIRONMENT={settings.arcade.environment} \n\
                ARCADE_API_URL={settings.arcade.api_url}, \n\
                ARCADE_USER_ID={settings.arcade.user_id}, \n\
                api_key_present - {bool(settings.arcade.api_key)}"
        )
        logger.debug(f"Tool environment variable names available to tools: {tool_env_keys}")
    except Exception as e:
        logger.debug(f"Unable to log settings/tool env keys: {e}")

    # Create server
    server = MCPServer(
        catalog=catalog,
        settings=settings,
        **kwargs,
    )

    # Create transport
    transport = StdioTransport()

    try:
        # Start server and transport
        await server.start()
        await transport.start()

        # Run connection
        async with transport.connect_session() as session:
            await server.run_connection(
                session.read_stream,
                session.write_stream,
                session.init_options,
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server error: {e}")
        raise
    finally:
        # Stop transport and server
        try:
            await transport.stop()
        finally:
            await server.stop()


def main() -> None:
    """Main entry point for arcade_mcp_server module."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Arcade MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-discover tools from current directory
  python -m arcade_mcp_server

  # Run with stdio transport for Claude Desktop
  python -m arcade_mcp_server stdio

  # Load specific arcade package
  python -m arcade_mcp_server --tool-package github
  python -m arcade_mcp_server -p slack

  # Discover all installed arcade packages
  python -m arcade_mcp_server --discover-installed --show-packages

  # Development mode with hot reload
  python -m arcade_mcp_server --debug --reload

  # Run from a different directory
  python -m arcade_mcp_server --cwd /path/to/project
  python -m arcade_mcp_server --cwd ~/my-tools stdio

Auto-discovery looks for Python files with @tool decorated functions in:
  - Current directory (*.py)
  - tools/ subdirectory
  - arcade_tools/ subdirectory
        """,
    )

    # Transport selection (positional for backwards compatibility)
    parser.add_argument(
        "transport",
        nargs="?",
        default="http",
        choices=["stdio", "http", "streamable-http"],
        help="Transport type (default: http)",
    )

    # Optional arguments
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (HTTP mode only)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (HTTP mode only)",
    )
    parser.add_argument(
        "--tool-package",
        "--package",
        "-p",
        dest="tool_package",
        help="Specific tool package to load (e.g., 'github' for arcade-github)",
    )
    parser.add_argument(
        "--discover-installed",
        "--all",
        action="store_true",
        help="Discover all installed arcade tool packages",
    )
    parser.add_argument(
        "--show-packages",
        action="store_true",
        help="Show loaded packages during discovery",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (HTTP mode only)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging",
    )
    parser.add_argument(
        "--otel-enable",
        action="store_true",
        help="Send logs to OpenTelemetry",
    )
    parser.add_argument(
        "--env-file",
        help="Path to environment file",
    )
    parser.add_argument(
        "--name",
        help="Server name",
    )
    parser.add_argument(
        "--version",
        help="Server version",
    )
    parser.add_argument(
        "--cwd",
        help="Directory to change to before running (for tool discovery)",
    )
    parser.add_argument(
        "--workers",
        default=1,
        type=int,
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    # Change working directory if specified
    if args.cwd:
        cwd_path = Path(args.cwd).resolve()
        if not cwd_path.exists():
            print(f"Error: Directory does not exist: {args.cwd}", file=sys.stderr)
            sys.exit(1)
        if not cwd_path.is_dir():
            print(f"Error: Path is not a directory: {args.cwd}", file=sys.stderr)
            sys.exit(1)
        os.chdir(cwd_path)
        # Update logging to show the new directory

    # Load environment variables
    if args.env_file:
        load_dotenv(args.env_file)

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, stdio_mode=(args.transport == "stdio"))

    if args.workers > 1 and args.transport == "stdio":
        logger.error("Cannot use --workers > 1 with stdio transport")
        sys.exit(1)

    # Build kwargs for server
    server_kwargs = {}
    if args.name:
        server_kwargs["name"] = args.name
    if args.version:
        server_kwargs["version"] = args.version

    # Run appropriate server
    try:
        if args.transport == "stdio":
            # Discover tools only for stdio mode (HTTP mode handles its own discovery)
            catalog = initialize_tool_catalog(
                tool_package=args.tool_package,
                show_packages=args.show_packages,
                discover_installed=args.discover_installed,
                server_name=server_kwargs.get("name"),
                server_version=server_kwargs.get("version"),
            )
            logger.info("Starting MCP server with stdio transport")
            asyncio.run(
                run_stdio_server(catalog, debug=args.debug, env_file=args.env_file, **server_kwargs)
            )
        else:
            logger.info(f"Starting MCP server with HTTP transport on {args.host}:{args.port}")
            from arcade_mcp_server.worker import run_arcade_mcp

            run_arcade_mcp(
                host=args.host,
                port=args.port,
                reload=args.reload,
                debug=args.debug,
                otel_enable=args.otel_enable,
                tool_package=args.tool_package,
                discover_installed=args.discover_installed,
                show_packages=args.show_packages,
                workers=args.workers,
                **server_kwargs,
            )
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Server stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

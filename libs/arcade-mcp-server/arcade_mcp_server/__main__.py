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

from dotenv import load_dotenv
from loguru import logger

from arcade_mcp_server.logging_utils import setup_logging
from arcade_mcp_server.stdio_runner import initialize_tool_catalog, run_stdio_server


def _build_manifest_command(argv: list[str]) -> int:
    """Discover installed toolkits and write a precomputed catalog manifest.

    Run at Docker image build time to skip toolkit discovery + Pydantic
    model construction on every container start.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m arcade_mcp_server build-manifest",
        description="Build a precomputed tool catalog manifest from installed toolkits.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path where the manifest JSON should be written.",
    )
    parser.add_argument(
        "--tool-package",
        "-p",
        dest="tool_package",
        help="Build for a single installed package instead of all of them.",
    )
    parser.add_argument(
        "--discover-installed",
        "--all",
        action="store_true",
        default=True,
        help="Include every installed arcade-* toolkit (default).",
    )
    parser.add_argument(
        "--show-packages",
        action="store_true",
        help="Log loaded packages during discovery.",
    )
    args = parser.parse_args(argv)

    # Set up logging before any toolkit imports
    setup_logging(level="INFO", stdio_mode=False)

    from arcade_core.discovery import discover_tools
    from arcade_core.manifest import write_manifest

    catalog = discover_tools(
        tool_package=args.tool_package,
        show_packages=args.show_packages,
        discover_installed=args.discover_installed,
    )
    if len(catalog) == 0:
        logger.error("No tools discovered. Manifest would be empty.")
        return 1

    # Force materialization of every tool definition so the manifest
    # captures the full ToolDefinition for each one.
    for tool in catalog:
        _ = tool.definition

    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    written = write_manifest(catalog, out)
    logger.info(f"Wrote manifest with {len(catalog)} tools to {written}")
    return 0


def main() -> None:
    """Main entry point for arcade_mcp_server module."""
    import argparse

    # Subcommand dispatch: handle build-manifest before the main parser so it
    # doesn't collide with the legacy transport positional.
    if len(sys.argv) >= 2 and sys.argv[1] == "build-manifest":
        sys.exit(_build_manifest_command(sys.argv[2:]))

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

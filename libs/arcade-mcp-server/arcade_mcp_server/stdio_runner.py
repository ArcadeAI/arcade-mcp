"""
Stdio transport runner for MCP server.

Provides the async entry point for running the MCP server over stdio,
and tool catalog initialization used by both stdio and HTTP modes.
"""

import sys
from typing import Any

from arcade_core.catalog import ToolCatalog
from arcade_core.discovery import discover_tools
from arcade_core.toolkit import ToolkitLoadError
from dotenv import load_dotenv
from loguru import logger

from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings


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

    if env_file:
        load_dotenv(env_file)
        logger.debug(f"Loaded environment variables from --env-file={env_file}")

    if settings is None:
        settings = MCPSettings.from_env()

    if debug:
        settings.debug = True
        settings.middleware.enable_logging = True
        settings.middleware.log_level = "DEBUG"

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

    server = MCPServer(
        catalog=catalog,
        settings=settings,
        **kwargs,
    )

    transport = StdioTransport()

    try:
        await server.start()
        await transport.start()

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
        try:
            await transport.stop()
        finally:
            await server.stop()

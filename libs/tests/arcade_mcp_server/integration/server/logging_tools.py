from typing import Annotated

from arcade_mcp_server import Context, tool


@tool
async def logging_tool(context: Context, message: Annotated[str, "The message to log"]) -> str:
    """Log a message at varying levels."""
    await context.log.log("debug", f"Debug via log.log: {message}")
    await context.log.debug(f"Debug via log.debug: {message}")
    await context.log.info(f"Info via log.info: {message}")
    await context.log.warning(f"Warning via log.warning: {message}")
    await context.log.error(f"Error via log.error: {message}")

    return message

from typing import Annotated

from arcade_mcp_server import Context, MCPApp
from loguru import logger

app = MCPApp("LoggingServer")


@app.tool
async def log_message(context: Context, message: Annotated[str, "The message to log"]) -> str:
    """Log a message at varying levels."""
    await context.log.log("debug", f"Debug via log.log: {message}")
    await context.log.debug(f"Debug via log.debug: {message}")
    await context.log.info(f"Info via log.info: {message}")
    await context.log.warning(f"Warning via log.warning: {message}")
    await context.log.error(f"Error via log.error: {message}")
    await context.log.log("info", f"Info via log.log: {message}")

    return message


if __name__ == "__main__":
    logger.info("Just about to start running the server...")
    app.run(transport="http")
    logger.info("Server has finished running...")

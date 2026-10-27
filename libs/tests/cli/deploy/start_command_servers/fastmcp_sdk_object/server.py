# An MCP SDK server object in a fastmcp project: `fastmcp run` serves it too.
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return text

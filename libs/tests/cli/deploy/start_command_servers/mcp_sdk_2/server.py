import os

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("echo-server")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return text


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=int(os.environ.get("FIXTURE_PORT", "8000")))

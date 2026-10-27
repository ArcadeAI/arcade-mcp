import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("echo-server", port=int(os.environ.get("FIXTURE_PORT", "8000")))


@mcp.tool()
def echo(text: str) -> str:
    """Echo the text back."""
    return text


if __name__ == "__main__":
    mcp.run("streamable-http")

from fastmcp import FastMCP

mcp = FastMCP("echo-server")


@mcp.tool
def echo(text: str) -> str:
    """Echo the text back."""
    return text


if __name__ == "__main__":
    mcp.run()

from fastmcp import FastMCP

# Two server objects: only fastmcp.json says which one to serve.
server = FastMCP("echo-server")
draft = FastMCP("draft-server")


@server.tool
def echo(text: str) -> str:
    """Echo the text back."""
    return text

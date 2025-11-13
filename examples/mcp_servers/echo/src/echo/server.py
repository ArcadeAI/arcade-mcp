from typing import Annotated

from arcade_mcp_server import MCPApp

app = MCPApp("EchoServer")


@app.tool
def echo(message: Annotated[str, "The message to echo"]) -> str:
    """Echo a message back to the caller."""
    return message


if __name__ == "__main__":
    app.run(transport="http")

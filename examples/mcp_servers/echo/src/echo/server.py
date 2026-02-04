from typing import Annotated

from arcade_mcp_server import MCPApp
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Domain,
    SystemType,
    ToolMetadata,
    Verb,
)

app = MCPApp("EchoServer")


@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.TRANSFORM],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.READ],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
    ),
)
def echo(message: Annotated[str, "The message to echo"]) -> str:
    """Echo a message back to the caller."""
    return message


if __name__ == "__main__":
    app.run(transport="http")

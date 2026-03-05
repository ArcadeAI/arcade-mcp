from typing import Annotated

from arcade_mcp_server import Context, tool
from arcade_mcp_server.metadata import Behavior, Classification, ToolMetadata


@tool(
    metadata=ToolMetadata(
        classification=Classification(),
        behavior=Behavior(
            read_only=True,
            destructive=False,
            idempotent=True,
        ),
    ),
)
async def say_hello(
    context: Context,
    name: Annotated[str, "The name of the person to greet"],
) -> str:
    """Say a greeting!"""

    return "Hello, " + name + "!"

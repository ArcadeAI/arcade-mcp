from arcade_mcp_server import Context, tool


@tool
def the_other_tool() -> str:
    """A tool that is called by a tool"""
    return "I am the other tool."


@tool
async def call_other_tool(
    context: Context,
) -> str:
    """Get the hash value of a secret"""

    other_tool_response = await context.tools.call_raw("Server_TheOtherTool", {})

    if other_tool_response.isError:
        return (
            "Sorry, but I couldn't call the other tool, because: "
            + other_tool_response.structuredContent["error"]
        )

    return "SUCCESS: " + other_tool_response.structuredContent["result"]

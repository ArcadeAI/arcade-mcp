from arcade_mcp_server import Context, tool


@tool
async def elicit_nickname(context: Context) -> str:
    """Ask the end user for their nickname, and then use it to greet them."""
    elicitation_schema = {"type": "object", "properties": {"nickname": {"type": "string"}}}
    result = await context.ui.elicit(
        "What is your nickname?",
        schema=elicitation_schema,
    )

    if result.action == "accept":
        return f"Hello, {result.content['nickname']}!"
    elif result.action == "decline":
        return "User declined to provide a nickname."
    elif result.action == "cancel":
        return "User cancelled the elicitation."

    return "Unknown response from client"

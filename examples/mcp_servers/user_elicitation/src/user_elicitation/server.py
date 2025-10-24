#!/usr/bin/env python3
"""user_elicitation MCP server"""

import sys

from arcade_mcp_server import Context, MCPApp

app = MCPApp(name="user_elicitation", version="1.0.0", log_level="DEBUG")

elicitation_schema = {"type": "object", "properties": {"nickname": {"type": "string"}}}


@app.tool
async def elicit_nickname(context: Context) -> str:
    """Ask the end user for their nickname, and then use it to greet them."""

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


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)

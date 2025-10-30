#!/usr/bin/env python3
"""sampling MCP server"""

import sys
from typing import Annotated

from arcade_mcp_server import Context, MCPApp

app = MCPApp(name="sampling", version="1.0.0", log_level="DEBUG")


@app.tool
async def summarize_text(
    context: Context, text: Annotated[str, "The text to be summarized by the client's model"]
) -> str:
    """Summarize the text using the client's model."""
    result = await context.sampling.create_message(
        messages=text,
        system_prompt=(
            "You are a helpful assistant that summarizes text. "
            "Given a text, you should summarize it in a few sentences."
        ),
    )
    return result.text


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)

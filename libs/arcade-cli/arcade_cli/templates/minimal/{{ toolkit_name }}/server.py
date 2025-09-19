#!/usr/bin/env python3
"""{{ toolkit_name }} MCP server"""

import sys
from typing import Annotated

from arcade_mcp import Context, MCPApp

app = MCPApp(name="{{ toolkit_name }}", version="1.0.0", log_level="DEBUG")


@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


@app.tool(requires_secrets=["MY_SECRET_KEY"])
def whisper_secret(context: Context) -> Annotated[str, "The last 4 characters of the secret"]:
    """Reveal the last 4 characters of a secret"""
    # Secrets are injected into the tool context at runtime.
    # This means that LLMs and MCP clients cannot see or access your secrets
    # You can define secrets in a .env file.
    try:
        secret = context.get_secret("MY_SECRET_KEY")
    except Exception as e:
        return str(e)

    return "The last 4 characters of the secret are: " + secret[-4:]


# Run with specific transport
if __name__ == "__main__":
    # Get transport from command line argument, default to "stream"
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    # Run the server
    # - "https" (default): HTTPS streaming for Claude Desktop, Claude Code, Cursor
    # - "stdio": Standard I/O for VS Code and CLI tools
    app.run(transport=transport, host="127.0.0.1", port=8000)

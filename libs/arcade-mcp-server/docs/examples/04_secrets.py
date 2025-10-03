#!/usr/bin/env python3
"""04: Read secrets from .env via Context

Run:
  uv run 04_secrets.py           # HTTP transport (default)
  uv run 04_secrets.py stdio     # stdio transport for Claude Desktop

Environment:
  # Create a .env in the working directory with:
  #   API_KEY=supersecret
"""

import sys

from arcade_mcp_server import Context, MCPApp

# Create the MCP application
app = MCPApp(
    name="secrets_example",
    version="1.0.0",
    instructions="Example server demonstrating secrets usage",
)


@app.tool(
    requires_secrets=["API_KEY"],  # declare we need API_KEY
)
def use_secret(context: Context) -> str:
    """Read API_KEY from context and return a masked confirmation string."""
    try:
        value = context.get_secret("API_KEY")
        masked = value[:2] + "***" if len(value) >= 2 else "***"
        return f"Got API_KEY of length {len(value)} -> {masked}"
    except Exception as e:
        return f"Error getting secret: {e}"


if __name__ == "__main__":
    # Check if stdio transport was requested
    transport = "stdio" if len(sys.argv) > 1 and sys.argv[1] == "stdio" else "http"

    print(f"Starting {app.name} v{app.version}")
    print(f"Transport: {transport}")

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)

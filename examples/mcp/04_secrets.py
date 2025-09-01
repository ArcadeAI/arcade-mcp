#!/usr/bin/env python3
"""04: Read secrets from .env via ToolContext.

Run:
  # Create a .env in the working directory with:
  #   API_KEY=supersecret
  # Then start the server:
  python 04_secrets.py [stream|sse|stdio]

Clients or the server will inject secrets into ToolContext. This example declares
required secrets so the server fetches them from local context/.env.
"""

# standard library
import sys

from arcade_core.schema import ToolContext

# third-party
from arcade_mcp import Server
from arcade_tdk import tool


@tool(
    name="UseSecret",
    desc="Echo a masked secret read from the context",
    requires_secrets=["API_KEY"],  # declare we need API_KEY
)
def use_secret(context: ToolContext) -> str:
    """Read API_KEY from context and return a masked confirmation string."""
    # The server loads .env automatically; secret is accessible via context
    try:
        value = context.get_secret("API_KEY")
        masked = value[:2] + "***" if len(value) >= 2 else "***"
        return f"Got API_KEY of length {len(value)} -> {masked}"
    except Exception as e:
        return f"Error getting secret: {e}"


server = Server(name="secrets_example", version="0.1.0")
server.add_tool(use_secret)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stream"
    server.run(transport=transport, host="0.0.0.0", port=8000)  # noqa: S104

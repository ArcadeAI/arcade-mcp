#!/usr/bin/env python3
"""01: Inline tool and server in one file.

Run:
  python 01_inline_server.py [stream|sse|stdio]
"""

# standard library
import sys
from typing import Annotated

# third-party
from arcade_mcp import Server
from arcade_tdk import tool


@tool(desc="Echo back the provided text")
def echo(text: Annotated[str, "The text to echo back"]) -> str:
    """Return the same text that was provided.

    Minimal example of a tool defined in the same file as the server.
    """
    return text


# Create server and register the local tool
server = Server(name="inline_example", version="0.1.0")
server.add_tool(echo)


if __name__ == "__main__":
    # Default to streaming transport for local dev (Cursor/Claude Desktop compatible)
    transport = sys.argv[1] if len(sys.argv) > 1 else "stream"
    server.run(transport=transport, host="0.0.0.0", port=8000)

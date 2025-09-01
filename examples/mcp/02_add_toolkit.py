#!/usr/bin/env python3
"""02: Add a Toolkit by importing and registering it on the server.

This demonstrates using Arcade toolkits through importing and adding to the server.

Run:
  python 02_add_toolkit.py [stream|sse|stdio]
"""

# standard library
import sys

# third-party
from arcade_core.toolkit import Toolkit
from arcade_mcp import Server

# Example: use the "simple_mcp" example toolkit shipped in this repo
# Adjust the package name if you want to load a different installed toolkit.
TOOLKIT_PACKAGE = "simple_mcp"

# Load Toolkit metadata + tool discovery from an installed/local package
# (Will read pyproject metadata and scan the package for @tool functions.)
toolkit = Toolkit.from_package(TOOLKIT_PACKAGE)

# Create server and add the toolkit
server = Server(name="add_toolkit_example", version="0.1.0")
server.add_toolkit(toolkit)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stream"
    server.run(transport=transport, host="0.0.0.0", port=8000)  # noqa: S104

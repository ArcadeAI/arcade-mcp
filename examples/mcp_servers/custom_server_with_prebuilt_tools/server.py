#!/usr/bin/env python3
"""custom_server_with_prebuilt_tools MCP server"""

import random
import string
import sys
from typing import Annotated

import arcade_math  # comes from arcade-math PyPI package
from arcade_math.tools.random import generate_random_int
from arcade_mcp_server import MCPApp

app = MCPApp(name="Math", version="1.0.0", log_level="DEBUG")
app.add_tools_from_module(arcade_math)  # adds 20+ math related tools


# A tool that calls another tool in the same server via context.tools
@app.tool
async def generate_random_string(
    min_length: Annotated[int, "The minimum length of the string"],
    max_length: Annotated[int, "The maximum length of the string"],
) -> str:
    """Generate a random string between min_length and max_length."""

    length = generate_random_int(str(min_length), str(max_length))

    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=int(length)))


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)

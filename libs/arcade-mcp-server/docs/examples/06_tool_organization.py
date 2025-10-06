#!/usr/bin/env python3
"""
06_tool_organization.py - Demonstrating modular tool organization

This example showcases the power of the direct Python approach by demonstrating:
- Tools defined in separate files and imported
- Tools imported from other Arcade packages
- Mixed approaches: @app.tool decorators + imported tools
- Explicit control over which tools are added to the server

Project Structure (recommended):
    my_server/
    ├── .env
    ├── server.py          # Main MCPApp
    ├── tools/
    │   ├── __init__.py
    │   ├── math_tools.py  # @tool decorated functions
    │   └── text_tools.py  # @tool decorated functions
    ├── pyproject.toml
    └── README.md

To run (HTTP transport by default):
    uv run 06_tool_organization.py

To run with stdio transport (for Claude Desktop):
    uv run 06_tool_organization.py stdio
"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp

# Import tools from our 'mock' other_files module
# In a real project, these could come from actual separate files
from tools_math import add, multiply
from tools_text import capitalize_string, word_count

# In a real project, you could also import from Arcade PyPI packages:
# from arcade_gmail.tools import list_emails

# Create the MCP application
app = MCPApp(
    name="organized_server",
    version="1.0.0",
    instructions="Example server demonstrating modular tool organization",
)

# Method 1: Add imported tools explicitly
app.add_tool(add)
app.add_tool(multiply)
app.add_tool(capitalize_string)
app.add_tool(word_count)


# Method 2: Define tools directly on the app
@app.tool
def server_info() -> Annotated[dict, "Information about this server"]:
    """Return information about this MCP server."""
    return {
        "name": "Organized Server",
        "version": "1.0.0",
        "description": "Demonstrates modular tool organization",
        "total_tools": 6,  # 4 imported + 2 defined here
    }


@app.tool
def combine_results(
    text: Annotated[str, "Text to process"],
    add_num: Annotated[int, "Number to add"],
    multiply_num: Annotated[int, "Number to multiply"],
) -> Annotated[dict, "Combined results from multiple tools"]:
    """Demonstrate using multiple tools together."""
    return {
        "original_text": text,
        "capitalized": capitalize_string(text),
        "word_count": word_count(text),
        "math_result": multiply(add(5, add_num), multiply_num),
    }


if __name__ == "__main__":
    # Check if stdio transport was requested
    transport = "stdio" if len(sys.argv) > 1 and sys.argv[1] == "stdio" else "http"

    print(f"Starting {app.name} v{app.version}")
    print(f"Transport: {transport}")
    print("Setting up database...")
    # simulate a database setup
    print("Database setup complete")

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)

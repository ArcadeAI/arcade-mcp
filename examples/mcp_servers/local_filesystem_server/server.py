#!/usr/bin/env python3
"""local_filesystem MCP server"""

import sys

from arcade_mcp_server import MCPApp

from tools import (
    copy_path,
    create_directory,
    list_directory,
    move_path,
    read_file,
    search_files,
    stat_path,
    tail_file,
    write_file,
)

app = MCPApp(name="local_filesystem", version="1.0.0", log_level="DEBUG")


app.add_tool(list_directory)
app.add_tool(read_file)
app.add_tool(write_file)
app.add_tool(tail_file)
app.add_tool(stat_path)
app.add_tool(create_directory)
app.add_tool(move_path)
app.add_tool(copy_path)
app.add_tool(search_files)

# Run with specific transport
if __name__ == "__main__":
    # Get transport from command line argument, default to "http"
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    # Run the server
    # - "http" (default): HTTPS streaming for Cursor, VS Code, etc.
    # - "stdio": Standard I/O for Claude Desktop, CLI tools, etc.
    app.run(transport=transport, host="127.0.0.1", port=8000)

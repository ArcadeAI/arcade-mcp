# Arcade MCP Examples

This directory contains examples demonstrating how to build MCP servers with your Arcade tools.

## Examples Overview

### Basic Examples

1. **[00_hello_world.py](00_hello_world.py)** – Minimal tool example
   - Single `@tool` function showing the basics
   - Run: `python -m arcade_mcp_server` (or `python -m arcade_mcp_server stdio`)

2. **[01_tools.py](01_tools.py)** – Creating tools and discovery
   - Simple parameters, lists, and `TypedDict`
   - How arcade_mcp_server discovers tools automatically
   - Run: `python -m arcade_mcp_server`

3. **[02_building_apps.py](02_building_apps.py)** – Building apps with MCPApp
   - Create an `MCPApp`, register tools with `@app.tool`
   - Run HTTP: `python 02_building_apps.py`
   - Run stdio: `python 02_building_apps.py stdio`

4. **[03_context.py](03_context.py)** – Using `Context`
   - Access secrets, logging, and user context
   - Run: `python -m arcade_mcp_server`

5. **[04_tool_secrets.py](04_tool_secrets.py)** – Working with secrets
   - Use `requires_secrets` and access masked values
   - Run: `python -m arcade_mcp_server`

6. **[05_logging.py](05_logging.py)** – Logging with MCP
   - Demonstrates debug/info/warning/error levels and structured logs
   - Run: `python 05_logging.py`

## Running Examples

Most examples can be run directly with the arcade_mcp_server CLI:

```bash
# Auto-discover tools in current directory
python -m arcade_mcp_server

# With specific transport
python -m arcade_mcp_server stdio  # For Claude Desktop
python -m arcade_mcp_server        # HTTP by default

# With debugging
python -m arcade_mcp_server --debug

# With hot reload (HTTP only)
python -m arcade_mcp_server --reload
```

For MCPApp examples, run the script directly to start an HTTP server.

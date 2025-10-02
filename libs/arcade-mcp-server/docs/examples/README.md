# Arcade MCP Examples

This directory contains examples demonstrating how to build MCP servers with your Arcade tools.

## Getting Started

The easiest way to get started is with the `arcade new` command:

```bash
# Install the Arcade CLI
uv pip install arcade-mcp

# Create a new server with example tools
arcade new my_server
cd my_server

# Run the server
arcade mcp
```

## Examples Overview

### Basic Examples

1. **[00_hello_world.py](00_hello_world.py)** – Minimal tool example
   - Single `@tool` function showing the basics
   - Run: `arcade mcp` (or `arcade mcp stdio`)

2. **[01_tools.py](01_tools.py)** – Creating tools and discovery
   - Simple parameters, lists, and `TypedDict`
   - How the server discovers tools automatically
   - Run: `arcade mcp`

3. **[02_building_apps.py](02_building_apps.py)** – Building apps with MCPApp
   - Create an `MCPApp`, register tools with `@app.tool`
   - Run HTTP: `python 02_building_apps.py`
   - Run stdio: `python 02_building_apps.py stdio`

4. **[03_context.py](03_context.py)** – Using `Context`
   - Access secrets, logging, and user context
   - Run: `arcade mcp`

5. **[04_tool_secrets.py](04_tool_secrets.py)** – Working with secrets
   - Use `requires_secrets` and access masked values
   - Run: `arcade mcp`

6. **[05_logging.py](05_logging.py)** – Logging with MCP
   - Demonstrates debug/info/warning/error levels and structured logs
   - Run: `python 05_logging.py`

## Running Examples

### Recommended: Using the Arcade CLI

Most examples can be run with the `arcade mcp` command:

```bash
# Auto-discover tools in current directory
arcade mcp

# With specific transport
arcade mcp stdio  # For Claude Desktop
arcade mcp        # HTTP by default

# With debugging
arcade mcp --debug

# With hot reload (HTTP only)
arcade mcp --reload
```

### Alternative: Direct Python Execution

For MCPApp examples, you can run the script directly:

```bash
python 02_building_apps.py
```

Or use the server module directly:

```bash
python -m arcade_mcp_server
```

**Note:** We recommend using `arcade mcp` for a better development experience.

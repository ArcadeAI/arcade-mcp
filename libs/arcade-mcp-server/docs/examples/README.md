# Arcade MCP Examples

This directory contains examples demonstrating how to build MCP servers with your Arcade tools.

## Getting Started

The easiest way to get started is with `arcade new`:

```bash
# Install the CLI
uv pip install arcade-mcp

# Create a new server project with example tools
arcade new my_server
cd my_server

# Run your server
uv run server.py
```

This creates a complete project with `server.py`, `pyproject.toml`, and example tools showing best practices.

## Examples Overview

### Basic Examples

1. **[00_hello_world.py](00_hello_world.py)** – Minimal tool example
   - Single `@tool` function showing the basics
   - Run: `uv run 00_hello_world.py` (or `uv run 00_hello_world.py stdio`)

2. **[01_tools.py](01_tools.py)** – Creating tools and discovery
   - Simple parameters, lists, and `TypedDict`
   - How the server discovers tools automatically
   - Run: `uv run 01_tools.py`

3. **[02_building_apps.py](02_building_apps.py)** – Building apps with MCPApp
   - Create an `MCPApp`, register tools with `@app.tool`
   - Run HTTP: `uv run 02_building_apps.py`
   - Run stdio: `uv run 02_building_apps.py stdio`

4. **[03_context.py](03_context.py)** – Using `Context`
   - Access secrets, logging, and user context
   - Run: `uv run 03_context.py`

5. **[04_tool_secrets.py](04_secrets.py)** – Working with secrets
   - Use `requires_secrets` and access masked values
   - Run: `uv run 04_secrets.py`

6. **[05_logging.py](05_logging.py)** – Logging with MCP
   - Demonstrates debug/info/warning/error levels and structured logs
   - Run: `uv run 05_logging.py`

7. **[06_tool_organization.py](06_tool_organization.py)** – Tool organization and imports
   - Demonstrate modular tool organization, importing from files and packages
   - Run: `uv run 06_tool_organization.py`

8. **[07_auth.py](07_auth.py)** – Tools that require auth
   - Create tools that require OAuth scopes
   - Use Reddit OAuth to fetch posts
   - Prerequisites: Run `arcade login` to authenticate with Arcade
   - Run: `uv run 07_auth.py`

## Running Examples

### Recommended: Direct Python Execution

Most examples can be run directly with Python using `uv`:

```bash
# Run any example file directly
uv run 00_hello_world.py
uv run 02_building_apps.py
uv run 06_tool_organization.py

# With specific transport
uv run server.py stdio  # For Claude Desktop
uv run server.py http   # HTTP by default

# You can also run with python directly
python 00_hello_world.py
python 02_building_apps.py stdio
```

All example files include proper command-line argument handling with `if __name__ == "__main__":` blocks.

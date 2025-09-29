# arcade mcp Command

The `arcade mcp` command is the recommended way to run MCP servers. It automatically discovers tools in your project, creates a server, and runs it with your chosen transport.

## Installation

```bash
uv pip install arcade-mcp
```

The `arcade-mcp` package includes the CLI and the `arcade-mcp-server` library.

## Command Line Options

```
usage: arcade mcp [-h] [--host HOST] [--port PORT]
                  [--tool-package PACKAGE] [--discover-installed]
                  [--show-packages] [--reload] [--debug]
                  [--env-file ENV_FILE] [--name NAME] [--version VERSION]
                  [--cwd CWD]
                  [transport]

Run Arcade MCP Server

positional arguments:
  transport             Transport type: stdio, http (default: http)

optional arguments:
  -h, --help           show this help message and exit
  --host HOST          Host to bind to (HTTP mode only, default: 127.0.0.1)
  --port PORT          Port to bind to (HTTP mode only, default: 8000)
  --tool-package PACKAGE, --package PACKAGE, -p PACKAGE
                       Specific tool package to load (e.g., 'github' for arcade-github)
  --discover-installed, --all
                       Discover all installed arcade tool packages
  --show-packages      Show loaded packages during discovery
  --reload             Enable auto-reload on code changes (HTTP mode only)
  --debug              Enable debug mode with verbose logging
  --env-file ENV_FILE  Path to environment file
  --name NAME          Server name
  --version VERSION    Server version
  --cwd CWD            Working directory to run from
```

## Basic Usage

```bash
# Run HTTP server (default)
arcade mcp

# Run stdio server (for Claude Desktop, Cursor, etc.)
arcade mcp stdio

# Run with debug logging
arcade mcp --debug

# Run with hot reload (development mode)
arcade mcp --reload --debug
```

## Tool Discovery

The CLI discovers tools in three ways:

### 1. Auto-Discovery (Default)

Automatically finds Python files with `@tool` decorated functions in:
- Current directory (`*.py`)
- `tools/` subdirectory
- `arcade_tools/` subdirectory

Example file structure:
```
my_project/
├── hello.py          # Contains @tool functions
├── tools/
│   └── math.py      # More @tool functions
└── arcade_tools/
    └── utils.py     # Even more @tool functions
```

### 2. Package Loading

Load specific arcade packages installed in your environment:

```bash
# Load arcade-github package
arcade mcp --tool-package github

# Load custom package (tries arcade_ prefix first)
arcade mcp -p mycompany_tools
```

### 3. Discover All Installed

Find and load all arcade packages in your Python environment:

```bash
# Load all arcade packages
arcade mcp --discover-installed

# Show what's being loaded
arcade mcp --discover-installed --show-packages
```

### Example Tool File

Create any Python file with `@tool` decorated functions:

```python
from arcade_mcp_server import tool

@tool
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

Then run:
```bash
arcade mcp  # Auto-discovers and loads these tools
```

## Alternative: Direct Python Usage

While we recommend using `arcade mcp`, you can also run the server module directly:

```bash
python -m arcade_mcp_server [options]
```

This provides the same functionality but without the benefits of the Arcade CLI ecosystem (like `arcade configure` for client setup).

# CLI

The `arcade_mcp` CLI is a simple tool for running MCP servers.

It is used to discover tools and run the server.



## Command Line Options

```
usage: python -m arcade_mcp [-h] [--host HOST] [--port PORT]
                           [--tool-package PACKAGE] [--discover-installed]
                           [--show-packages] [--reload] [--debug]
                           [--env-file ENV_FILE] [--name NAME] [--version VERSION]
                           [transport]

Run Arcade MCP Server

positional arguments:
  transport             Transport type: stdio, http, streamable-http (default: http)

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
python -m arcade_mcp --tool-package github

# Load custom package (tries arcade_ prefix first)
python -m arcade_mcp -p mycompany_tools
```

### 3. Discover All Installed

Find and load all arcade packages in your Python environment:

```bash
# Load all arcade packages
python -m arcade_mcp --discover-installed

# Show what's being loaded
python -m arcade_mcp --discover-installed --show-packages
```

### Example Tool File

Create any Python file with `@tool` decorated functions:

```python
from arcade_tdk import tool

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
python -m arcade_mcp  # Auto-discovers and loads these tools
```
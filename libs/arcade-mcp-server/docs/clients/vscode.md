# Visual Studio Code

While VSCode doesn't have native MCP support yet, you can integrate Arcade MCP servers with VSCode through extensions and custom configurations. This guide shows various integration approaches.

## Prerequisites

- Visual Studio Code installed
- Python 3.10+ installed
- `arcade-mcp` package installed (`pip install arcade-mcp`)
- Python extension for VSCode

## Integration Methods

### Method 1: Terminal Integration

Use VSCode's integrated terminal to run MCP servers:

1. Open integrated terminal (`Ctrl/Cmd + ` `)
2. Start your MCP server:
   ```bash
   uv run server.py
   ```
3. Use split terminals for multiple servers

### Method 2: Task Runner

Create tasks to manage MCP servers:

#### Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start MCP Server",
      "type": "shell",
      "command": "python",
      "args": ["-m", "arcade_mcp_server", "--reload", "--debug"],
      "isBackground": true,
      "problemMatcher": {
        "pattern": {
          "regexp": "^(ERROR|WARNING):\\s+(.+)$",
          "severity": 1,
          "message": 2
        },
        "background": {
          "activeOnStart": true,
          "beginsPattern": "^Starting.*",
          "endsPattern": "^.*Server ready.*"
        }
      },
      "presentation": {
        "reveal": "always",
        "panel": "dedicated"
      }
    },
    {
      "label": "Start MCP (HTTP)",
      "type": "shell",
      "command": "python",
      "args": [
        "-m", "arcade_mcp_server",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
      ],
      "isBackground": true,
      "problemMatcher": []
    },
    {
      "label": "Test Tools",
      "type": "shell",
      "command": "python",
      "args": ["${workspaceFolder}/test_tools.py"],
      "problemMatcher": "$python"
    }
  ]
}
```

Run tasks via:
- Command Palette: `Tasks: Run Task`
- Terminal menu: `Terminal > Run Task`

### Method 3: Launch Configurations

Debug your MCP tools with VSCode's debugger:

#### Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug MCP Server",
      "type": "python",
      "request": "launch",
      "module": "arcade_mcp_server",
      "args": ["--debug", "--reload"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "ARCADE_API_KEY": "${env:ARCADE_API_KEY}"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Specific Tool",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/tools/my_tool.py",
      "args": ["--test"],
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal"
    },
    {
      "name": "Debug with Package",
      "type": "python",
      "request": "launch",
      "module": "arcade_mcp_server",
      "args": [
        "--tool-package", "github",
        "--debug"
      ],
      "env": {
        "GITHUB_TOKEN": "${input:githubToken}"
      }
    }
  ],
  "inputs": [
    {
      "id": "githubToken",
      "type": "promptString",
      "description": "Enter your GitHub token",
      "password": true
    }
  ]
}
```

## Development Workflow

### Project Setup

Recommended project structure:

```
my-mcp-project/
├── .vscode/
│   ├── launch.json      # Debug configurations
│   ├── tasks.json       # Task definitions
│   ├── settings.json    # Workspace settings
│   └── extensions.json  # Recommended extensions
├── .env                 # Environment variables
├── .env.example
├── tools/
│   ├── __init__.py
│   └── my_tools.py
├── tests/
│   └── test_tools.py
├── requirements.txt
└── pyproject.toml
```

### Workspace Settings

Configure `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  },
  "terminal.integrated.env.linux": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "${workspaceFolder}"
  }
}
```

### Recommended Extensions

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-vscode.live-server",
    "humao.rest-client",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

## Testing Tools

### REST Client Extension

Test HTTP MCP servers using REST Client:

Create `test-mcp.http`:

```http
### Get Server Info
GET http://localhost:8000/health

### List Tools
POST http://localhost:8000/catalog
Content-Type: application/json
Authorization: Bearer {{$env ARCADE_API_KEY}}

{}

### Call Tool
POST http://localhost:8000/call_tool
Content-Type: application/json
Authorization: Bearer {{$env ARCADE_API_KEY}}

{
  "tool_name": "greet",
  "tool_arguments": {
    "name": "World"
  }
}
```

### Python Test Scripts

Create test scripts for your tools:

```python
# test_tools.py
import asyncio
from arcade_core.catalog import ToolCatalog

async def test_tools():
    # Import your tools
    from tools import my_tools

    # Create catalog
    catalog = ToolCatalog()
    catalog.add_tool(my_tools.greet, "test")

    # Test tool
    result = await catalog.call_tool(
        "test.greet",
        {"name": "Test"}
    )
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_tools())
```

## Debugging Tips

### Breakpoint Debugging

1. Set breakpoints in your tool code
2. Launch debugger with "Debug MCP Server"
3. Trigger tool execution
4. Step through code execution

### Logging Configuration

Enhanced logging for debugging:

```python
# tools/__init__.py
import logging
from loguru import logger

# Configure loguru
logger.add(
    "debug.log",
    rotation="10 MB",
    level="DEBUG",
    format="{time} {level} {message}"
)

# Intercept standard logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)
```

### Performance Profiling

Profile your tools:

```json
{
  "name": "Profile MCP Server",
  "type": "python",
  "request": "launch",
  "module": "cProfile",
  "args": [
    "-o", "profile.stats",
    "-m", "arcade_mcp_server",
    "--debug"
  ],
  "cwd": "${workspaceFolder}"
}
```

## Snippets

Create useful code snippets in `.vscode/python.code-snippets`:

```json
{
  "Arcade Tool": {
    "prefix": "atool",
    "body": [
      "from arcade_tdk import tool",
      "from typing import Annotated",
      "",
      "@tool",
      "def ${1:tool_name}(",
      "    ${2:param}: Annotated[${3:str}, \"${4:Parameter description}\"]",
      ") -> Annotated[${5:str}, \"${6:Return description}\"]:",
      "    \"\"\"${7:Tool description}.\"\"\"",
      "    ${8:# Implementation}",
      "    return ${9:result}"
    ],
    "description": "Create an Arcade tool"
  },
  "Async Tool": {
    "prefix": "atoolasync",
    "body": [
      "from arcade_tdk import tool",
      "from typing import Annotated",
      "",
      "@tool",
      "async def ${1:tool_name}(",
      "    ${2:param}: Annotated[${3:str}, \"${4:Parameter description}\"]",
      ") -> Annotated[${5:str}, \"${6:Return description}\"]:",
      "    \"\"\"${7:Tool description}.\"\"\"",
      "    ${8:# Async implementation}",
      "    return ${9:result}"
    ],
    "description": "Create an async Arcade tool"
  }
}
```

## Integration Examples

### Multi-Server Setup

Run multiple MCP servers for different purposes:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start All Servers",
      "dependsOn": [
        "Start API Tools",
        "Start Data Tools",
        "Start Utility Tools"
      ],
      "problemMatcher": []
    },
    {
      "label": "Start API Tools",
      "type": "shell",
      "command": "uv run server.py",
      "options": {
        "cwd": "${workspaceFolder}/api_tools"
      },
      "isBackground": true
    },
    {
      "label": "Start Data Tools",
      "type": "shell",
      "command": "uv run server.py",
      "options": {
        "cwd": "${workspaceFolder}/data_tools"
      },
      "isBackground": true
    },
    {
      "label": "Start Utility Tools",
      "type": "shell",
      "command": "uv run server.py",
      "options": {
        "cwd": "${workspaceFolder}/util_tools"
      },
      "isBackground": true
    }
  ]
}
```

### Environment Management

Handle multiple environments:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "MCP Server (Dev)",
      "type": "shell",
      "command": "uv run --env-file .env.dev server.py",
      "problemMatcher": []
    },
    {
      "label": "MCP Server (Staging)",
      "type": "shell",
      "command": "uv run --env-file .env.staging server.py",
      "problemMatcher": []
    },
    {
      "label": "MCP Server (Prod)",
      "type": "shell",
      "command": "uv run --env-file .env.prod server.py",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "showReuseMessage": true,
        "clear": true
      }
    }
  ]
}
```

## Best Practices

1. **Use Virtual Environments**: Always work in isolated environments
2. **Version Control Settings**: Include `.vscode` in your repository
3. **Environment Files**: Use `.env` files for secrets
4. **Consistent Formatting**: Configure formatters and linters
5. **Test Automation**: Set up test tasks and debug configs
6. **Documentation**: Keep README and docstrings updated
7. **Git Hooks**: Use pre-commit for code quality

## Troubleshooting

### Common Issues

1. **Python interpreter not found**:
   - Select interpreter: `Cmd/Ctrl + Shift + P` > "Python: Select Interpreter"
   - Ensure virtual environment is activated

2. **Module import errors**:
   - Check PYTHONPATH in settings
   - Verify package installation
   - Restart VSCode

3. **Debug breakpoints not working**:
   - Ensure you're using the debug configuration
   - Check that debugpy is installed
   - Verify source maps are correct

4. **Task execution fails**:
   - Check task definition syntax
   - Verify working directory
   - Review terminal output for errors

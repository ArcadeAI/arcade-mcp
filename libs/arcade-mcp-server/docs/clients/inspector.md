# MCP Inspector

The MCP Inspector is a powerful debugging and testing tool for MCP servers. It provides a web-based interface to interact with your Arcade MCP server, test tools, and monitor protocol messages.

## Installation

Install the MCP Inspector globally:

```bash
npm install -g @modelcontextprotocol/inspector
```

Or use npx to run without installing:

```bash
npx @modelcontextprotocol/inspector
```

## Basic Usage

### Connecting to HTTP Servers

For MCP servers running over HTTP:

```bash
# Start your MCP server
uv run server.py

# In another terminal, start the inspector
mcp-inspector http://localhost:8000/mcp
```

### Connecting to stdio Servers

For stdio-based servers:

```bash
# Start the inspector with your server command
mcp-inspector "uv run server.py stdio"

# With additional project directory
mcp-inspector --cwd /path/to/project "uv run server.py stdio"
```

## Inspector Features

### Tool Explorer

The Tool Explorer shows all available tools with:

- Tool names and descriptions
- Parameter schemas
- Return type information
- Example invocations

### Interactive Testing

Test tools directly from the interface:

1. Select a tool from the explorer
2. Fill in parameter values
3. Click "Execute" to run the tool
4. View results and execution time

### Protocol Monitor

Monitor all MCP protocol messages:

- Request/response pairs
- Message timing
- Protocol errors
- Raw JSON data

### Resource Browser

If your server provides resources:

- Browse available resources
- View resource contents
- Test resource operations

### Prompt Templates

Test prompt templates if supported:

- View available prompts
- Fill template parameters
- Preview rendered prompts

## Advanced Usage

### Custom Environment

Pass environment variables to your server:

```bash
# Using env command
env ARCADE_API_KEY=your-key mcp-inspector "uv run server.py stdio"

# Using inspector's env option
mcp-inspector --env ARCADE_API_KEY=your-key "uv run server.py stdio"
```

### Working Directory

Set the working directory for your server:

```bash
mcp-inspector --cwd /path/to/project "uv run server.py stdio"
```

### Debug Mode

Enable verbose logging:

```bash
# Debug the inspector
mcp-inspector --debug "uv run server.py stdio"

# Server debug logging is configured in your server.py
# app = MCPApp(name="my_server", version="1.0.0", log_level="DEBUG")
```

## Testing Workflows

### Tool Development

1. **Configure your server with hot reload**:
   ```python
   # In your server.py
   if __name__ == "__main__":
       transport = sys.argv[1] if len(sys.argv) > 1 else "http"
       app.run(transport=transport, host="127.0.0.1", port=8000, reload=True)
   ```

   Then run:
   ```bash
   uv run server.py
   ```

2. **Connect the inspector**:
   ```bash
   mcp-inspector http://localhost:8000/mcp
   ```

3. **Develop and test**:
   - Modify your tool code
   - Server auto-reloads
   - Test immediately in inspector

### Performance Testing

Use the inspector to measure tool performance:

1. Enable timing in the Protocol Monitor
2. Execute tools multiple times
3. Analyze response times
4. Identify bottlenecks

### Error Debugging

Debug tool errors effectively:

1. Enable debug mode on your server
2. Execute the failing tool
3. Check Protocol Monitor for error details
4. View server logs in terminal

## Integration Testing

### Test Suites

Create test suites using the inspector:

```javascript
// test-tools.js
const tests = [
  {
    tool: "greet",
    params: { name: "World" },
    expected: "Hello, World!"
  },
  {
    tool: "calculate",
    params: { expression: "2 + 2" },
    expected: 4
  }
];

// Run tests via inspector API
```

### Automated Testing

Combine with testing frameworks:

```python
# test_mcp_tools.py
import subprocess
import json
import pytest

def test_tool_via_inspector():
    # Start server
    server = subprocess.Popen(
        ["python", "-m", "arcade_mcp_server"],
        stdout=subprocess.PIPE
    )

    # Use inspector's API to test tools
    # ...
```

## Best Practices

### Development Setup

1. **Use Split Terminal**:
   - Terminal 1: MCP server with reload
   - Terminal 2: Inspector
   - Terminal 3: Code editor

2. **Enable All Debugging**:
   ```python
   # In server.py
   app = MCPApp(name="my_server", version="1.0.0", log_level="DEBUG")

   # Run with reload
   app.run(transport="http", host="127.0.0.1", port=8000, reload=True)
   ```

   Then run with environment file:
   ```bash
   uv run server.py
   ```

3. **Save Test Cases**:
   - Export successful tool calls
   - Build regression test suite
   - Document edge cases

### Production Testing

1. **Test Against Production Config**:
   ```bash
   mcp-inspector "uv run server.py stdio"
   ```

2. **Verify Security**:
   - Test with limited permissions
   - Verify API key handling
   - Check error messages don't leak secrets

3. **Load Testing**:
   - Execute tools rapidly
   - Monitor memory usage
   - Check for resource leaks

## Troubleshooting

### Connection Issues

#### "Failed to connect"

1. Verify server is running
2. Check correct URL/command
3. Ensure ports aren't blocked
4. Try with `--debug` flag

#### "Protocol error"

1. Ensure server implements MCP correctly
2. Check for version compatibility
3. Review server logs
4. Verify transport type

### Tool Issues

#### "Tool not found"

1. Verify tool is decorated with `@tool`
2. Check tool discovery in server
3. Ensure no import errors
4. Restart server and inspector

#### "Parameter validation failed"

1. Check parameter types match schema
2. Verify required parameters
3. Test with simpler values
4. Review tool documentation

## Examples

### Quick Test Session

```bash
# 1. Start a simple MCP server
cat > test_tools.py << 'EOF'
from arcade_mcp_server import tool
from typing import Annotated

@tool
def echo(message: Annotated[str, "Message to echo"]) -> str:
    """Echo the message back."""
    return message

@tool
def add(
    a: Annotated[int, "First number"],
    b: Annotated[int, "Second number"]
) -> Annotated[int, "Sum"]:
    """Add two numbers."""
    return a + b
EOF

# 2. Start inspector
mcp-inspector "uv run server.py stdio"

# 3. Test tools in the web interface
```

### HTTP Server Testing

```bash
# 1. Create an MCPApp server
cat > app.py << 'EOF'
from arcade_mcp_server import MCPApp
from typing import Annotated

app = MCPApp(name="test-server", version="1.0.0")

@app.tool
def get_time() -> Annotated[str, "Current time"]:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().isoformat()

if __name__ == "__main__":
    app.run(port=9000, reload=True)
EOF

# 2. Run the server
python app.py

# 3. Connect inspector
mcp-inspector http://localhost:9000/mcp
```

### Debugging Session

```bash
# 1. Enable all debugging
export DEBUG=*
export MCP_DEBUG=true

# 2. Start server with verbose logging
# (configure log_level="DEBUG" in your server.py)
uv run server.py stdio 2>server.log

# 3. Start inspector with debugging
mcp-inspector --debug "uv run server.py stdio"
```

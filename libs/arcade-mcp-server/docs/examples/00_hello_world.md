# 00 - Hello World

The simplest possible MCP server with a single tool using arcade-mcp-server.

## Running the Example

- **Run (HTTP default)**: `uv run 00_hello_world.py`
- **Run (stdio for Claude Desktop)**: `uv run 00_hello_world.py stdio`

## Source Code

```python
--8<-- "docs/examples/00_hello_world.py"
```

## Key Concepts

- **Minimal Setup**: Create `MCPApp`, define tools with `@app.tool`, and run with `app.run()`
- **Direct Execution**: Run your server file directly with `uv run` or `python`
- **Transport Flexibility**: Works with both stdio (for Claude Desktop) and HTTP
- **Type Annotations**: Use `Annotated` to provide descriptions for parameters and return values
- **Command Line Args**: Pass transport type as command line argument

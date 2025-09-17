# 00 - Hello World

The simplest possible MCP server with a single tool using arcade-mcp.

## Running the Example

- **Run (HTTP default)**: `python -m arcade_mcp`
- **Run (stdio for Claude Desktop)**: `python -m arcade_mcp stdio`

## Source Code

```python
--8<-- "docs/examples/00_hello_world.py"
```

## Key Concepts

- **Minimal Setup**: Just import `@tool` decorator and annotate your function
- **Auto-Discovery**: The CLI automatically finds tools in your current directory
- **Transport Flexibility**: Works with both stdio (for Claude Desktop) and HTTP
- **Type Annotations**: Use `Annotated` to provide descriptions for parameters and return values

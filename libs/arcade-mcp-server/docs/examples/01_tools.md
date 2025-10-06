# 01 - Tools

Learn how to create tools with different parameter types and how arcade_mcp_server discovers them automatically.

## Running the Example

- **Run (HTTP default)**: `uv run 01_tools.py`
- **Run (stdio for Claude Desktop)**: `uv run 01_tools.py stdio`

## Source Code

```python
--8<-- "docs/examples/01_tools.py"
```

## Creating Tools

### 1. Simple Tools

Basic tools with simple parameter types:

```python
@app.tool
def hello(name: Annotated[str, "Name to greet"]) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

@app.tool
def add(
    a: Annotated[float, "First number"],
    b: Annotated[float, "Second number"]
) -> Annotated[float, "Sum of the numbers"]:
    """Add two numbers together."""
    return a + b
```

### 2. List Parameters

Working with lists of values:

```python
@app.tool
def calculate_average(
    numbers: Annotated[list[float], "List of numbers to average"]
) -> Annotated[float, "Average of all numbers"]:
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
```

### 3. Complex Types with TypedDict

Using TypedDict for structured input and output:

```python
class PersonInfo(TypedDict):
    name: str
    age: int
    email: str
    is_active: bool

@tool
def create_user_profile(
    person: Annotated[PersonInfo, "Person's information"]
) -> Annotated[str, "Formatted user profile"]:
    """Create a formatted user profile from person information."""
    # Implementation here
```

## Managing Tools in MCPApp

With the direct Python approach, you have full control over your tools:

### 1. Defining Tools Directily
Use `@app.tool` to define tools directly on your MCPApp instance:
```python
@app.tool
def my_tool(param: str) -> str:
    """Tool description."""
    return f"Processed: {param}"
```

### 2. Importing Tools from Files
You can import tools from other files and add them explicitly:
```python
from my_tools import calculate, process_data

# Add imported tools to the app
app.add_tool(calculate)
app.add_tool(process_data)
```

### 3. Project Organization

Example project structure:
```
my_project/
├── server.py          # Main MCPApp
├── tools/
│   ├── math.py       # Tools using @tool decorator
│   └── utils.py      # More tools
└── pyproject.toml    # Dependencies
```

This approach gives you explicit control over which tools are loaded and how they're organized.

## Best Practices

### Parameter Annotations
- **Always use `Annotated`**: Provide descriptions for all parameters
- **Clear descriptions**: Help the AI understand what each parameter does
- **Type hints**: Use proper Python type hints for validation

### Tool Design
- **Single purpose**: Each tool should do one thing well
- **Error handling**: Add validation and helpful error messages
- **Return types**: Always annotate return types with descriptions

### Organization
- **Group related tools**: Use directories to organize by functionality
- **Naming conventions**: Use clear, descriptive names
- **Documentation**: Write clear docstrings for each tool

## Key Concepts

- **Explicit Control**: Use `@app.tool` decorators and `app.add_tool()` for precise tool management
- **Type Safety**: Full type annotation support with runtime validation
- **TypedDict Support**: Use TypedDict for complex structured data
- **Import Flexibility**: Import tools from your own files and external packages
- **Direct Execution**: Run servers directly with `uv run` for better development experience

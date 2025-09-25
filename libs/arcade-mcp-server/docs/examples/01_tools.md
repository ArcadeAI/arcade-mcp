# 01 - Tools

Learn how to create tools with different parameter types and how arcade_mcp_server discovers them automatically.

## Running the Example

- **Run**: `python -m arcade_mcp_server`
- **Run (stdio)**: `python -m arcade_mcp_server stdio`
- **Show loaded packages**: `python -m arcade_mcp_server --show-packages`
- **Load specific package**: `python -m arcade_mcp_server --tool-package github`
- **Discover all installed**: `python -m arcade_mcp_server --discover-installed`

## Source Code

```python
--8<-- "docs/examples/01_tools.py"
```

## Creating Tools

### 1. Simple Tools

Basic tools with simple parameter types:

```python
@tool
def hello(name: Annotated[str, "Name to greet"]) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

@tool
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
@tool
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

## Tool Discovery

The arcade_mcp_server CLI discovers tools in multiple ways:

### 1. Current Directory
- Scans all `*.py` files in the current directory
- Imports and checks for `@tool` decorated functions

### 2. Standard Directories
- `tools/` directory - Common convention for organizing tools
- `arcade_tools/` directory - Alternative naming convention
- Both are recursively scanned for Python files

### 3. Package Loading
```bash
# Load a specific package
python -m arcade_mcp_server --tool-package github

# Discover all installed arcade packages
python -m arcade_mcp_server --discover-installed
```

### 4. File Organization

Example project structure:
```
my_project/
├── hello.py          # Contains @tool functions
├── tools/
│   └── math.py      # More @tool functions
└── arcade_tools/
    └── utils.py     # Even more @tool functions
```

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

- **Auto-Discovery**: Automatically finds tools without explicit registration
- **Type Safety**: Full type annotation support with runtime validation
- **TypedDict Support**: Use TypedDict for complex structured data
- **Flexible Organization**: Structure your tools however makes sense for your project
- **Multiple Sources**: Discover from files, directories, and packages

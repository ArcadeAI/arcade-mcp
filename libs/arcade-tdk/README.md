# Arcade TDK (Toolkit Development Kit)

Toolkit Development Kit for building and testing Arcade tools.

## Overview

Arcade TDK provides the essential tools and utilities for building Arcade tools:

- **Tool Decorator**: Simple `@tool` decorator for creating Arcade tools
- **Authentication**: Auth providers and helpers for tool security
- **Annotations**: Type annotations and parameter validation
- **Core Integration**: Seamless integration with arcade-core components

## Installation

```bash
pip install arcade-tdk
```

## Usage

```python
from typing import Annotated

from arcade_tdk import tool

@tool
def hello_world(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

# The tool is automatically registered and available for use
```

## Advanced Usage

```python
from typing import Annotated

from arcade_tdk import tool, ToolCatalog, Toolkit

# Create tools with more complex parameters
@tool
def calculate_sum(numbers: Annotated[list[float], "The numbers to sum"]) -> float:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)

# Access the tool catalog
catalog = ToolCatalog()
tools = catalog.get_all_tools()

# Work with toolkits
toolkit = Toolkit.from_directory("my_toolkit")
```

## License

MIT License - see LICENSE file for details.

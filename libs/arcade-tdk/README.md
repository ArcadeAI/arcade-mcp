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
from arcade_tdk.auth import Reddit

# Create tools with auth requirement
@tool(requires_auth=Reddit(scopes=["read"]))
def get_posts_in_subreddit(
    subreddit: Annotated[str, "The name of the subreddit"],
    limit: Annotated[int, "The number of posts to return]
) -> dict:
    """Get posts from a specific subreddit"""
    # TODO: Implement your Reddit tool
    return {}
```

## License

MIT License - see LICENSE file for details.

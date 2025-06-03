# Arcade Serve

Serving infrastructure for Arcade tools and workers.

## Overview

Arcade Serve provides the infrastructure for serving Arcade tools:

- **FastAPI Worker**: High-performance FastAPI-based worker implementation
- **MCP Server**: Model Context Protocol server for tool integration
- **Core Abstractions**: Base worker classes and components
- **Authentication**: Auth utilities and routing
- **Runtime Management**: Tool execution and lifecycle management

## Installation

```bash
pip install arcade-serve
```

## Usage

### FastAPI Worker

```python
from arcade_serve import FastAPIWorker

# Create a FastAPI worker
worker = FastAPIWorker()

# Add tools to the worker
worker.add_toolkit("path/to/toolkit")

# Start the server
worker.start(host="0.0.0.0", port=8000)
```

### MCP Server

```python
from arcade_serve import StdioServer

# Create an MCP server
server = StdioServer()

# Add tools
server.add_toolkit("path/to/toolkit")

# Start the server
server.run()
```

### Custom Worker

```python
from arcade_serve import BaseWorker, WorkerComponent

class MyWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.add_component(MyCustomComponent())

    async def handle_request(self, request):
        # Custom request handling
        return await super().handle_request(request)
```

## License

MIT License - see LICENSE file for details.

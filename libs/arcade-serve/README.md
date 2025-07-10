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

To add a toolkit to a hosted worker such as FastAPI, you can register them in the worker itself.
This allows you to explicitly define which tools should be included on a particular worker.


Here is an example of adding the math toolkit (pip install arcade-math) to a FastAPI Worker:
```python
import arcade_math
from fastapi import FastAPI
from arcade_tdk import Toolkit
from arcade_serve.fastapi import FastAPIWorker

app = FastAPI()

worker_secret = os.environ.get("ARCADE_WORKER_SECRET")
worker = FastAPIWorker(app, secret=worker_secret)

worker.register_toolkit(Toolkit.from_module(arcade_math))
```

Here is an example of adding the math toolkit (pip install arcade-math) to a MCP Worker
```python
import arcade_math
from arcade_core.catalog import ToolCatalog
from arcade_serve.mcp.stdio import StdioServer

# 1. Create and populate the tool catalog
catalog = ToolCatalog()
catalog.add_module(arcade_math)


# 2. Main entrypoint
async def main():
    # Create the worker with the tool catalog
    worker = StdioServer(catalog)

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## License

MIT License - see LICENSE file for details.

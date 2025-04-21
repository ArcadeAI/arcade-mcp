import arcade_google

from arcade.core.catalog import ToolCatalog
from arcade.worker.mcp.stdio import StdioServer

# 2. Create and populate the tool catalog
# Ensure you have run `pip install arcade_google`
catalog = ToolCatalog()
catalog.add_module(arcade_google)  # Registers all tools in the package


# 3. Main entrypoint
async def main():
    # Create the worker with the tool catalog
    worker = StdioServer(catalog)

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

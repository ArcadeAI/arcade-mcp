import arcade_gmail  # pip install arcade_gmail
import arcade_search  # pip install arcade_search
from arcade_core.catalog import ToolCatalog
from arcade_serve.mcp.stdio import StdioServer

# 2. Create and populate the tool catalog
catalog = ToolCatalog()
catalog.add_module(arcade_gmail)  # Registers all tools in the package
catalog.add_module(arcade_search)


# 3. Main entrypoint
async def main():
    # Create the worker with the tool catalog
    worker = StdioServer(catalog)

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

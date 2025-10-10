#!/usr/bin/env python3
"""
03_context.py - Using Context with namespaced runtime APIs

This example shows how tools can access runtime features through
Context (provided at runtime by the TDK wrapper), including logging,
secrets, and progress reporting.

To run:
    uv run 03_context.py           # HTTP transport (default)
    uv run 03_context.py stdio     # stdio transport for Claude Desktop

Set environment variables for secrets:
    export API_KEY="your-secret-key"
    export DATABASE_URL="postgresql://localhost/mydb"
"""

import sys
from typing import Annotated, Any

from arcade_mcp_server import Context, MCPApp

# Create the MCP application
app = MCPApp(
    name="context_example",
    version="1.0.0",
    instructions="Example server demonstrating Context usage",
)


@app.tool
async def secure_api_call(
    context: Context,
    endpoint: Annotated[str, "API endpoint to call"],
    method: Annotated[str, "HTTP method (GET, POST, etc.)"] = "GET",
) -> Annotated[str, "API response or error message"]:
    """Make a secure API call using secrets from context."""

    # Access secrets from environment via Context helper
    try:
        api_key = context.get_secret("API_KEY")
    except ValueError:
        await context.log.error("API_KEY not found in environment")
        return "Error: API_KEY not configured"

    # Log the API call
    await context.log.info(f"Making {method} request to {endpoint}")

    # Simulate API call (in real code, use httpx or aiohttp)
    return f"Successfully called {endpoint} with API key: {api_key[:4]}..."


# Don't forget to add the secret to the .env file or export it as an environment variable
@app.tool(requires_secrets=["DATABASE_URL"])
async def database_info(
    context: Context, table_name: Annotated[str | None, "Specific table to check"] = None
) -> Annotated[str, "Database connection info"]:
    """Get database connection information from context."""

    # Get database URL from secrets
    try:
        db_url = context.get_secret("DATABASE_URL")
    except ValueError:
        db_url = "Not configured"

    # Log at different levels
    if db_url == "Not configured":
        await context.log.warning("DATABASE_URL not set")
    else:
        await context.log.debug(f"Checking database: {db_url.split('@')[-1]}")

    # Get user info
    user_info = f"User: {context.user_id or 'anonymous'}"

    if table_name:
        return f"{user_info}\nDatabase: {db_url}\nChecking table: {table_name}"
    else:
        return f"{user_info}\nDatabase: {db_url}"


@app.tool
async def debug_context(
    context: Context,
    show_secrets: Annotated[bool, "Whether to show secret keys (not values)"] = False,
) -> Annotated[dict, "Current context information"]:
    """Debug tool to inspect the current context."""

    info: dict[str, Any] = {
        "user_id": context.user_id,
    }

    if show_secrets:
        # Only show keys, not values for security
        info["secret_keys"] = [s.key for s in (context.secrets or [])]

    # Log that debug info was accessed
    await context.log.info(f"Debug context accessed by {context.user_id or 'unknown'}")

    return info


@app.tool
async def process_with_progress(
    context: Context,
    items: Annotated[list[str], "Items to process"],
    delay_seconds: Annotated[float, "Delay between items"] = 0.1,
) -> Annotated[dict, "Processing results"]:
    """Process items with progress notifications."""

    results: dict[str, list] = {"processed": [], "errors": []}

    # Log start
    await context.log.info(f"Starting to process {len(items)} items")

    for i, item in enumerate(items):
        try:
            # Simulate processing
            import asyncio

            await asyncio.sleep(delay_seconds)

            # Report progress (current, total, message)
            await context.progress.report(i + 1, len(items), f"Processing: {item}")
            await context.log.debug(f"Processing item {i + 1}/{len(items)}: {item}")

            results["processed"].append(item.upper())

        except Exception as e:
            await context.log.error(f"Failed to process {item}: {e}")
            results["errors"].append({"item": item, "error": str(e)})

    # Log completion
    await context.log.info(
        f"Processing complete: {len(results['processed'])} succeeded, "
        f"{len(results['errors'])} failed"
    )

    return results


# The Context provides at runtime (via TDK wrapper):
# - context.user_id: ID of the user making the request
# - context.get_secret(key): Retrieve a secret value (raises if missing)
# - context.log.<level>(msg): Send log messages to the client (debug/info/warning/error)
# - context.progress.report(progress, total=None, message=None): Progress updates

if __name__ == "__main__":
    # Check if stdio transport was requested
    transport = "stdio" if len(sys.argv) > 1 and sys.argv[1] == "stdio" else "http"

    print(f"Starting {app.name} v{app.version}")
    print(f"Transport: {transport}")

    # Run the server
    app.run(transport=transport, host="127.0.0.1", port=8000)

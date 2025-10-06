#!/usr/bin/env python
"""
05_logging.py - MCP logging capabilities

This example demonstrates the various logging levels and patterns
available through the MCP protocol for debugging and monitoring.

To run:
    python 05_logging.py

To see debug logs:
    Set log_level="DEBUG" when creating MCPApp
"""

import asyncio
import time
import traceback
from typing import Annotated, Optional

from arcade_mcp_server import Context, MCPApp

# Create the app with debug logging
app = MCPApp(name="logging_examples", version="0.1.0", log_level="DEBUG")


@app.tool
async def demonstrate_log_levels(
    context: Context, message: Annotated[str, "Base message to log at different levels"]
) -> Annotated[dict, "Summary of logged messages"]:
    """Demonstrate all MCP logging levels."""

    # Log at each level
    levels = ["debug", "info", "warning", "error"]
    logged = {}

    for level in levels:
        log_message = f"[{level.upper()}] {message}"
        await context.log(level, log_message)
        logged[level] = log_message

    return {"logged_messages": logged, "note": "Check your MCP client to see these messages"}


@app.tool
async def timed_operation(
    context: Context,
    operation_name: Annotated[str, "Name of the operation"],
    duration_seconds: Annotated[float, "How long the operation takes"] = 2.0,
) -> Annotated[dict, "Operation timing details"]:
    """Perform a timed operation with detailed logging."""

    start_time = time.time()

    # Log operation start
    await context.log.info(
        f"Starting operation: {operation_name} (expected duration: {duration_seconds}s)"
    )

    # Simulate work with progress logging
    steps = 5
    for i in range(steps):
        await context.log.debug(f"Progress: step {i + 1}/{steps} ({(i + 1) / steps * 100:.0f}%)")

        await asyncio.sleep(duration_seconds / steps)

    # Calculate results
    end_time = time.time()
    actual_duration = end_time - start_time

    # Log completion
    await context.log.info(f"Completed operation: {operation_name} in {actual_duration:.2f}s")

    return {
        "operation": operation_name,
        "expected_duration": duration_seconds,
        "actual_duration": round(actual_duration, 2),
        "start_time": start_time,
        "end_time": end_time,
    }


@app.tool
async def error_handling_example(
    context: Context,
    should_fail: Annotated[bool, "Whether to simulate an error"],
    error_type: Annotated[str, "Type of error to simulate"] = "ValueError",
) -> Annotated[dict, "Result or error details"]:
    """Demonstrate error logging and handling."""

    try:
        await context.log.debug(f"Error handling test: should_fail={should_fail}")

        if should_fail:
            if error_type == "ValueError":
                raise ValueError("This is a simulated value error")  # noqa: TRY301
            elif error_type == "KeyError":
                raise KeyError("missing_key")  # noqa: TRY301
            elif error_type == "ZeroDivisionError":
                result = 1 / 0
                return {"result": result}
            else:
                raise Exception(f"Generic error of type: {error_type}")  # noqa: TRY002, TRY301

        # Success case
        await context.log.info("Operation completed successfully")

    except Exception as e:
        # Log the error with details
        await context.log.error(f"Operation failed with {type(e).__name__}: {e!s}")

        # Log traceback separately at debug level
        await context.log.debug(f"Traceback:\n{traceback.format_exc()}")

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "handled": True,
        }
    else:
        return {"status": "success", "message": "No errors occurred"}


@app.tool
async def structured_logging(
    context: Context,
    user_action: Annotated[str, "Action the user is performing"],
    metadata: Annotated[dict | None, "Additional metadata to log"] = None,
) -> Annotated[str, "Confirmation message"]:
    """Demonstrate structured logging patterns."""

    # Log main action
    await context.log.info(
        f"User action: {user_action} (user_id: {context.user_id or 'anonymous'})"
    )

    # Log additional details at debug level
    await context.log.debug(
        f"Context details: {len(context.secrets) if context.secrets else 0} secrets available"
    )

    # Log metadata if provided
    if metadata:
        await context.log.debug(f"Custom metadata: {metadata}")

    return f"Logged user action: {user_action}"


@app.tool
async def batch_processing_logs(
    context: Context,
    items: Annotated[list[str], "Items to process"],
    fail_on_item: Annotated[Optional[str], "Item that should fail"] = None,
) -> Annotated[dict, "Processing results with detailed logs"]:
    """Process items with detailed logging for each step."""

    results: dict[str, list] = {"successful": [], "failed": []}

    await context.log.info(f"Starting batch processing of {len(items)} items")

    for i, item in enumerate(items):
        try:
            # Log item start
            await context.log.debug(f"Processing item {i + 1}/{len(items)}: {item}")

            # Simulate failure if requested
            if item == fail_on_item:
                raise ValueError(f"Simulated failure for item: {item}")  # noqa: TRY301

            # Simulate processing
            await asyncio.sleep(0.1)

            results["successful"].append(item)

        except Exception as e:
            await context.log.warning(f"Failed to process '{item}': {e!s}")
            results["failed"].append({"item": item, "error": str(e)})

    # Log summary
    await context.log.info(
        f"Batch processing complete: {len(results['successful'])} successful, "
        f"{len(results['failed'])} failed",
    )

    return results


if __name__ == "__main__":
    # Run the server
    app.run(host="127.0.0.1", port=8000)

"""
Example: Using MCP Notifications in Tools

This example demonstrates how to use the MCP notification system to send
progress updates, log messages, and resource notifications from tools.
"""

import asyncio
import random
from datetime import datetime
from typing import Any

from arcade_tdk import tool
from arcade_tdk.schema import ToolContext


@tool
async def process_files_with_progress(
    files: list[str],
    context: ToolContext,
) -> dict[str, Any]:
    """
    Process multiple files with progress notifications.

    This tool demonstrates how to use the notification API to send
    progress updates to the client.
    """
    # Process with progress notifications
    results = []

    # Use the progress tracker context manager
    async with context.notify.progress(
        message="Processing files...",
        total=len(files),
    ) as tracker:
        for i, file in enumerate(files):
            # Send info notification about current file
            await context.log.info(f"Starting to process {file}")

            try:
                # Simulate file processing
                await asyncio.sleep(0.5)

                # Simulate some processing steps
                if file.endswith(".csv"):
                    await context.log.debug("Detected CSV file, using CSV parser")
                elif file.endswith(".json"):
                    await context.log.debug("Detected JSON file, using JSON parser")

                results.append(f"Successfully processed {file}")

                # Update progress
                await tracker.update(
                    current=i + 1,
                    message=f"Processed {file} ({i + 1}/{len(files)})",
                )

                # Notify resource update
                await context.notify.resource_updated(
                    uri=f"file://{file}",
                    timestamp=datetime.now().isoformat(),
                )

            except Exception as e:
                # Send error notification
                await context.log.error(
                    f"Failed to process {file}: {e!s}",
                    data={"file": file, "error": str(e)},
                )
                results.append(f"Failed to process {file}: {e!s}")

    # Send completion notification
    await context.log.info(
        f"Completed processing {len(files)} files",
        data={
            "total_files": len(files),
            "successful": len([r for r in results if "Successfully" in r]),
        },
    )

    return {"results": results}


@tool
async def long_running_analysis(
    data_size: int,
    context: ToolContext,
) -> str:
    """
    Perform a long-running analysis with detailed progress updates.

    This tool demonstrates fine-grained progress tracking and logging.
    """
    if not hasattr(context, "log"):
        # Fallback without notifications
        await asyncio.sleep(2)
        return f"Analysis complete for {data_size} items"

    # Start analysis with notifications
    await context.log.info(f"Starting analysis of {data_size} items")

    # Create a progress tracker for the entire operation
    async with context.notify.progress(
        message="Initializing analysis...",
        total=data_size,
    ) as tracker:
        # Phase 1: Data preparation (30% of work)
        await context.log.debug("Phase 1: Preparing data")
        await asyncio.sleep(0.5)

        # Update progress to show preparation is complete
        prepared_items = int(data_size * 0.3)
        await tracker.update(
            current=prepared_items,
            message="Data preparation complete",
        )

        # Phase 2: Analysis (60% of work)
        await context.log.debug("Phase 2: Running analysis")

        # Simulate processing in chunks
        chunk_size = max(1, data_size // 10)
        for i in range(prepared_items, data_size, chunk_size):
            processed = min(i + chunk_size, data_size)

            await tracker.update(
                current=processed,
                message=f"Analyzing items {i} to {processed}...",
            )
            await asyncio.sleep(0.2)

        # Phase 3: Generating report (final items)
        await context.log.debug("Phase 3: Generating report")
        await asyncio.sleep(0.3)

        # Mark complete
        await tracker.complete(message="Analysis complete!")

    # Send completion notification with summary
    await context.log.info(
        "Analysis completed successfully",
        data={
            "items_analyzed": data_size,
            "duration_seconds": 2.5,
            "phases_completed": 3,
        },
    )

    return f"Analysis complete for {data_size} items"


@tool
async def monitor_system_health(
    duration_seconds: int,
    context: ToolContext,
) -> dict[str, Any]:
    """
    Monitor system health and send notifications based on severity.

    This tool demonstrates using different log levels for notifications.
    """
    if not hasattr(context, "log"):
        await asyncio.sleep(duration_seconds)
        return {"status": "monitoring complete"}

    # Start monitoring
    await context.log.info("Starting system health monitoring")

    start_time = asyncio.get_event_loop().time()
    checks_performed = 0
    issues_found = []

    while asyncio.get_event_loop().time() - start_time < duration_seconds:
        checks_performed += 1

        # Simulate various health checks
        cpu_usage = random.uniform(0, 100)
        memory_usage = random.uniform(0, 100)
        disk_usage = random.uniform(0, 100)

        # Send appropriate notifications based on thresholds
        if cpu_usage > 90:
            await context.log.error(
                f"Critical CPU usage: {cpu_usage:.1f}%",
                data={"metric": "cpu", "value": cpu_usage},
            )
            issues_found.append(f"High CPU: {cpu_usage:.1f}%")
        elif cpu_usage > 70:
            await context.log.warning(
                f"High CPU usage: {cpu_usage:.1f}%",
                data={"metric": "cpu", "value": cpu_usage},
            )

        if memory_usage > 85:
            await context.log.warning(
                f"High memory usage: {memory_usage:.1f}%",
                data={"metric": "memory", "value": memory_usage},
            )
            issues_found.append(f"High memory: {memory_usage:.1f}%")

        # Debug level for normal operations
        await context.log.debug(
            f"Health check #{checks_performed}: CPU={cpu_usage:.1f}%, Memory={memory_usage:.1f}%, Disk={disk_usage:.1f}%"
        )

        await asyncio.sleep(1)

    # Send summary
    if issues_found:
        await context.log.warning(
            f"Monitoring complete with {len(issues_found)} issues",
            data={"issues": issues_found, "checks_performed": checks_performed},
        )
    else:
        await context.log.info(
            "Monitoring complete - all systems healthy",
            data={"checks_performed": checks_performed},
        )

    return {
        "status": "complete",
        "duration_seconds": duration_seconds,
        "checks_performed": checks_performed,
        "issues_found": issues_found,
    }


# Example of checking for notification support
@tool
async def conditional_notifications_example(
    enable_verbose: bool,
    context: ToolContext,
) -> str:
    """
    Example showing how to conditionally use notifications.

    This demonstrates checking if notifications are available and
    using them only when appropriate.
    """
    # Check if context has notification support (EnhancedToolContext)
    has_notifications = hasattr(context, "log") and hasattr(context, "notify")

    if has_notifications:
        await context.log.info("Notifications are available and enabled")

        if enable_verbose:
            await context.log.debug("Verbose mode enabled, sending detailed logs")
            # Send more detailed notifications
            for i in range(3):
                await context.log.debug(f"Verbose log entry {i + 1}")
        else:
            await context.log.info("Running in quiet mode")

    # Tool logic continues regardless of notification availability
    return "Operation completed"

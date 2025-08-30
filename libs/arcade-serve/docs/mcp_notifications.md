# MCP Notifications System

The MCP (Model Context Protocol) notifications system provides real-time, asynchronous communication between AI models and external services. This document covers the comprehensive notification support implemented in Arcade's MCP workers.

## Overview

The notification system enables:
- **Progress tracking** for long-running operations
- **Log/message notifications** with 8 severity levels
- **Resource notifications** for file/data updates
- **Tool notifications** for available tool changes

All notification types work seamlessly across all three MCP transport types:
- **stdio** - Standard input/output for CLI tools
- **SSE** - Server-Sent Events for web applications
- **stream** - HTTP streaming for real-time connections

## Architecture

### Core Components

1. **NotificationManager** - Centralized notification handling with:
   - Rate limiting (60 notifications/minute by default)
   - Debouncing for high-frequency events
   - Subscription management
   - Client capability negotiation

2. **ToolContext** - Standard context with integrated notification support
   - Built-in `log` and `notify` properties
   - Automatic injection when client supports notifications
   - Graceful fallback with no-op implementations

3. **Transport Adapters** - Protocol-specific delivery:
   - Write streams for each transport type
   - Automatic session management
   - Graceful disconnection handling

## Notification Types

### 1. Progress Notifications

Track long-running operations with percentage completion:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "unique-operation-id",
    "progress": 0.75,
    "total": 100.0,
    "message": "Processing item 75 of 100"
  }
}
```

### 2. Log/Message Notifications

System logging with severity levels:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "logger": "my-tool",
    "data": {
      "message": "Operation completed successfully",
      "timestamp": 1234567890
    }
  }
}
```

Supported levels:
- `debug` - Detailed debugging information
- `info` - General informational messages
- `notice` - Normal but significant conditions
- `warning` - Warning conditions
- `error` - Error conditions
- `critical` - Critical conditions
- `alert` - Action must be taken immediately
- `emergency` - System is unusable

### 3. Resource Notifications

#### Resource Updated
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "uri": "file:///path/to/resource",
    "timestamp": "2024-01-20T10:30:00Z"
  }
}
```

#### Resource List Changed
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/list_changed",
  "params": {}
}
```

### 4. Tool Notifications

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed",
  "params": {}
}
```

## Client Setup

### 1. Capability Declaration

Clients declare notification support during initialization:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "capabilities": {
      "notifications": {
        "notifications/progress": true,
        "notifications/message": true,
        "notifications/resources/updated": true,
        "notifications/resources/list_changed": true,
        "notifications/tools/list_changed": true
      }
    }
  }
}
```

### 2. Subscription Management

Subscribe to specific notification types:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "notifications/subscribe",
  "params": {
    "types": [
      "notifications/progress",
      "notifications/message"
    ]
  }
}
```

Unsubscribe:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "notifications/unsubscribe",
  "params": {
    "subscription_ids": ["sub-123", "sub-456"]
  }
}
```

## Tool Development

### Using Notifications in Tools

The standard ToolContext includes `log` and `notify` properties that are automatically available in all tools:

```python
from arcade.sdk import tool
from arcade.sdk.schema import ToolContext

@tool
async def my_long_running_tool(
    items: list[str],
    context: ToolContext,
) -> dict[str, Any]:
    # Log notifications are always available (no-op if client doesn't support)
    await context.log.info("Starting processing")

    # Track progress
    async with context.notify.progress(
        message="Processing items...",
        total=len(items)
    ) as tracker:
        for i, item in enumerate(items):
            # Process item
            result = await process_item(item)

            # Update progress
            await tracker.update(
                current=i + 1,
                message=f"Processed {item}"
            )

    await context.log.info("Processing complete")

    return {"status": "complete"}
```

### Progress Tracking Patterns

#### Simple Progress Updates
```python
# Using context manager for automatic progress tracking
async with context.notify.progress(
    message="Processing files...",
    total=100
) as tracker:
    for i in range(100):
        await do_work()
        await tracker.update(i + 1)
        # or use increment
        await tracker.increment()
```

#### Manual Progress Control
```python
# Create a progress context manually
progress = context.notify.progress(
    message="Starting operation",
    total=total_items
)

async with progress as tracker:
    # Update with custom messages
    await tracker.update(10, message="Completed initialization")
    await tracker.update(50, message="Halfway there")
    await tracker.complete(message="All done!")
```

### Logging Patterns

The `context.log` object provides methods for all severity levels:

```python
# Different severity levels
await context.log.debug("Detailed debug info")
await context.log.info("Operation started")
await context.log.notice("Important notification")
await context.log.warning("Resource usage high")
await context.log.error("Operation failed", data={"error": str(e)})
await context.log.critical("System critical error")

# Include structured data
await context.log.info(
    "Processing complete",
    data={
        "items_processed": 100,
        "duration_seconds": 45.2,
        "errors": 0
    }
)
```

### Resource Update Notifications

```python
# Notify when a resource is modified
await context.notify.resource_updated(
    uri="file:///data/output.json",
    timestamp=datetime.now().isoformat()
)

# Notify when resource list changes
await context.notify.resource_list_changed()
```

### Checking for Active Notification Support

While `context.log` and `context.notify` are always available, you can check if actual notification support is active:

```python
@tool
async def my_tool(context: ToolContext) -> str:
    # The log and notify methods are always safe to call
    await context.log.info("This works whether notifications are supported or not")

    # To check if notifications are actually being sent (vs no-op)
    # you can check the type of the logger
    from arcade_core.notifications import NoOpLogger

    if not isinstance(context.log, NoOpLogger):
        await context.log.info("Real notifications are enabled!")

    return "Done"
```

## Performance Considerations

### Rate Limiting

- Default: 60 notifications per minute per client
- Exceeding the limit results in dropped notifications
- Configure via `NotificationManager` initialization

### Debouncing

- Default: 100ms debounce window
- Reduces notification spam for high-frequency events
- Configurable per notification type

### Best Practices

1. **Just use it** - `context.log` and `context.notify` are always safe to use
2. **Use appropriate severity levels** - Don't send everything as `info`
3. **Batch related notifications** - Use debouncing for rapid updates
4. **Include meaningful context** - Add relevant data to notifications
5. **Clean up progress tracking** - Use context managers for automatic completion

## Transport-Specific Details

### stdio Transport

- Notifications sent as JSON-RPC messages on stdout
- One message per line
- Automatic queuing for concurrent notifications

### SSE Transport

- Notifications sent as Server-Sent Events
- Automatic reconnection support
- Session-based delivery with cleanup

### Stream Transport

- HTTP streaming with newline-delimited JSON
- Keep-alive pings for connection health
- Session management with timeouts

## Error Handling

The notification system is designed to fail gracefully:

- Missing notification support uses no-op implementations
- Failed notification delivery is logged but doesn't raise exceptions
- Rate-limited notifications are dropped with warnings
- Transport failures trigger automatic cleanup

## Examples

See `examples/mcp_notifications_example.py` for complete examples including:
- File processing with progress tracking
- Long-running analysis with phases
- System monitoring with severity-based notifications
- Conditional notification usage

## Configuration

Notification behavior can be configured at multiple levels:

### Server Level
```python
NotificationManager(
    sender=sender,
    rate_limit_per_minute=100,  # Increase rate limit
    default_debounce_ms=50,     # Reduce debounce time
    max_queued_notifications=2000  # Increase queue size
)
```

### Tool Level
```python
# Notifications are always available through context
await context.log.info("This always works")

# Progress tracking with automatic cleanup
async with context.notify.progress("Working...") as p:
    await p.update(50, "Halfway done")
```

## Compatibility

The notification system is designed with simplicity in mind:

- All tools have access to `context.log` and `context.notify`
- No-op implementations ensure tools never break
- Graceful enhancement when client supports notifications
- Protocol versioning for future extensions

## Security Considerations

- Notifications respect the same authentication as tool calls
- Client isolation prevents cross-client notification leakage
- Rate limiting prevents denial-of-service attacks
- No sensitive data should be included in notifications

## Troubleshooting

### Notifications Not Received

1. Check client capabilities in initialize request
2. Verify subscription is active
3. Check rate limiting hasn't been exceeded
4. Ensure transport connection is healthy

### Performance Issues

1. Enable debouncing for high-frequency notifications
2. Reduce notification data payload size
3. Check for notification queue backlog
4. Monitor client processing capacity

### Debug Logging

Enable debug logging for detailed notification flow:

```python
import logging
logging.getLogger("arcade.mcp.notifications").setLevel(logging.DEBUG)
```

## Summary

The MCP notification system is seamlessly integrated into the standard ToolContext, providing:

- Zero-configuration usage - just call `context.log` and `context.notify`
- Automatic enhancement when clients support notifications
- Clean, intuitive API for logging and progress tracking
- Works across all transport types without code changes

Tools can now easily add real-time feedback and logging without any setup or compatibility concerns.
# 05 - Logging

Demonstrates MCP logging capabilities with various levels and patterns for debugging and monitoring.

## Running the Example

- **Run**: `python examples/05_logging.py`
- Set `log_level="DEBUG"` in `MCPApp` to see debug logs

## Source Code

```python
--8<-- "docs/examples/05_logging.py"
```

## Logging Features

### 1. Log Levels

MCP supports standard log levels:
```python
await context.log.debug("Detailed debugging information")
await context.log.info("General information")
await context.log.warning("Warning messages")
await context.log.error("Error messages")
```

### 2. Structured Logging

Log with context and metadata:
```python
# Include user context
await context.log.info(
    f"Action performed by user: {context.user_id}"
)

# Add operation details
await context.log.debug(
    f"Processing {item_count} items with options: {options}"
)
```

### 3. Error Logging

Proper error handling and logging:
```python
try:
    # Operation that might fail
    result = risky_operation()
except Exception as e:
    # Log error with type and message
    await context.log.error(
        f"Operation failed: {type(e).__name__}: {str(e)}"
    )

    # Log traceback at debug level
    await context.log.debug(
        f"Traceback:\n{traceback.format_exc()}"
    )
```

### 4. Progress Logging

Track long-running operations:
```python
for i, item in enumerate(items):
    # Log progress
    await context.log.debug(
        f"Progress: {i+1}/{len(items)} ({(i+1)/len(items)*100:.0f}%)"
    )

    # Process item
    process(item)
```

### 5. Batch Processing

Log batch operations effectively:
```python
# Log batch start
await context.log.info(f"Starting batch of {count} items")

# Log individual items at debug level
for item in items:
    await context.log.debug(f"Processing: {item}")

# Log summary
await context.log.info(
    f"Batch complete: {success_count} successful, {fail_count} failed"
)
```

## Best Practices

1. **Use Appropriate Levels**: Debug for details, info for general flow, warning for issues, error for failures
2. **Include Context**: Always include relevant context like user ID, operation names, counts
3. **Structure Messages**: Use consistent message formats for easier parsing
4. **Handle Errors Gracefully**: Log errors with enough detail to debug but not expose sensitive data
5. **Progress Updates**: For long operations, provide regular progress updates
6. **Batch Summaries**: For batch operations, log both individual items (debug) and summaries (info)
7. **Performance Considerations**: Be mindful of log volume in production environments

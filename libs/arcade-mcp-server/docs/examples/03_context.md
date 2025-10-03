# 03 - Tool Context

Access runtime features through Context including logging, secrets, and progress reporting.

## Running the Example

- **Run**: `uv run 03_context.py`
- **Run (stdio)**: `uv run 03_context.py stdio`
- **Env**: set `API_KEY`, `DATABASE_URL`

## Source Code

```python
--8<-- "docs/examples/03_context.py"
```

## Context Features

The Context provides access to runtime features:

### 1. Logging
Send log messages at different levels:
```python
await context.log.debug("Debug message")
await context.log.info("Information message")
await context.log.warning("Warning message")
await context.log.error("Error message")
```

### 2. Secrets Management
Access environment variables securely:
```python
try:
    api_key = context.get_secret("API_KEY")
except ValueError:
    # Handle missing secret
```

### 3. User Context
Access information about the current user:
```python
user_id = context.user_id or "anonymous"
```

### 4. Progress Reporting
Report progress for long-running operations:
```python
await context.progress.report(current, total, "Processing...")
```

### 5. Tool Decorator Options
Specify required secrets:
```python
@tool(requires_secrets=["DATABASE_URL", "API_KEY"])
async def my_tool(context: Context, ...):
```

## Key Concepts

- **Context Parameter**: Tools receive a `Context` as their first parameter
- **Async Functions**: Use `async def` for tools that use context features
- **Secure Secrets**: Secrets are accessed through context, not hardcoded
- **Structured Logging**: Log at appropriate levels for debugging
- **Progress Updates**: Keep users informed during long operations

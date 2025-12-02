# Testing Actionable Error Messages

This document describes how to test the improved error messages in `arcade-mcp-server`.

## Quick Demo

Run the demonstration script to see all improved error messages:

```bash
python3 demo_error_messages.py
```

This will show examples of all error categories with before/after comparisons.

## Overview of Changes

**111 error messages** across **15 files** have been improved to follow this pattern:

```
✗ [Clear problem statement]

  [Specific context about what failed]

To fix:
  1. [Concrete step 1]
  2. [Concrete step 2]

[Next step if applicable]
```

## Error Categories Improved

### 1. Missing Secrets Errors
**File:** `server.py`

**What was improved:**
- Shows exactly which secrets are missing
- Provides both `.env` and environment variable examples
- Includes restart instruction

**How to test:**
1. Create a tool that requires a secret
2. Don't set the secret in environment
3. Try to call the tool
4. Verify error shows both fix options

**Example error:**
```
✗ Missing secret: 'API_KEY'

  Tool 'fetch_data' requires this secret but it is not configured.

To fix, tell the developer to either:
  1. Add to .env file in the server's working directory:
     API_KEY=your_value_here

  2. Set as environment variable:
     export API_KEY=your_value_here

Then restart the MCP server for changes to take effect.
```

### 2. Authorization Failures
**Files:** `server.py`

**What was improved:**
- Missing API key shows `arcade login` command
- OAuth flow errors provide authorization URL
- Authorization failures suggest common causes

**How to test:**
1. Create a tool with `requires_auth`
2. Don't set ARCADE_API_KEY
3. Try to call the tool
4. Verify error shows login command

### 3. Configuration Errors
**Files:** `settings.py`, `mcp_app.py`, `worker.py`

**What was improved:**
- Invalid log level shows valid options and how to set them
- App name validation provides specific examples
- Tool discovery errors explain setup steps

**How to test:**
```python
from arcade_mcp_server.settings import MiddlewareSettings
from pydantic import ValidationError

try:
    MiddlewareSettings(log_level="INVALID")
except ValidationError as e:
    print(str(e))
    # Should contain "✗ Invalid log level" and "To fix"
```

### 4. Transport Errors
**Files:** `stdio.py`, `http_streamable.py`, `http_session_manager.py`

**What was improved:**
- Stdio multiple sessions error suggests HTTP transport
- HTTP protocol errors explain required order
- Session manager errors provide initialization steps

**How to test:**
1. Try to create multiple stdio sessions
2. Verify error suggests using HTTP transport

### 5. Context & Validation Errors
**File:** `context.py`

**What was improved:**
- Schema validation shows exact expected formats
- Session availability errors explain when operations can be called
- Resource errors provide listing commands

**How to test:**
```python
from arcade_mcp_server.context import UI

class MockContext:
    def __init__(self):
        self._session = None

ui = UI(MockContext())

try:
    ui._validate_elicitation_schema({"type": "array"})
except ValueError as e:
    print(str(e))
    # Should contain "✗" and "To fix" with correct format
```

### 6. Manager Errors
**Files:** `managers/tool.py`, `managers/resource.py`, `managers/prompt.py`, `managers/base.py`

**What was improved:**
- Not found errors include listing commands
- Missing arguments show required parameters

## Running Unit Tests

The test suite includes comprehensive tests for error messages:

```bash
# Run all error message tests
pytest libs/tests/arcade_mcp_server/test_actionable_errors.py -v

# Run specific test category
pytest libs/tests/arcade_mcp_server/test_actionable_errors.py::TestSettingsErrors -v

# Run with output to see error messages
pytest libs/tests/arcade_mcp_server/test_actionable_errors.py -v -s
```

## Test Coverage by File

| File | Errors Improved | Coverage |
|------|----------------|----------|
| `server.py` | 2/2 | 100% |
| `settings.py` | 2/2 | 100% |
| `worker.py` | 4/4 | 100% |
| `context.py` | 30/30 | 100% |
| `mcp_app.py` | 23/23 | 100% |
| `convert.py` | 2/2 | 100% |
| `session.py` | 8/8 | 100% |
| `lifespan.py` | 3/3 | 100% |
| `managers/tool.py` | 2/2 | 100% |
| `managers/resource.py` | 4/4 | 100% |
| `managers/prompt.py` | 5/5 | 100% |
| `managers/base.py` | 2/2 | 100% |
| `transports/stdio.py` | 2/2 | 100% |
| `transports/http_streamable.py` | 12/12 | 100% |
| `transports/http_session_manager.py` | 10/10 | 100% |
| **TOTAL** | **111/111** | **100%** |

## Manual Testing Scenarios

### Scenario 1: Missing Environment Variable

```bash
# Remove API key
unset ARCADE_API_KEY

# Start server with auth-required tool
arcade mcp --tool-package my_tools

# Try to call auth tool
# Expected: Clear error with login instructions
```

### Scenario 2: Invalid Configuration

```bash
# Set invalid log level
export MCP_MIDDLEWARE_LOG_LEVEL=TRACE

# Start server
# Expected: Error listing valid options
```

### Scenario 3: Tool Not Found

```bash
# Call non-existent tool via MCP protocol
# Expected: Error suggesting to list available tools
```

### Scenario 4: Schema Validation

```python
# In a tool, try to elicit with invalid schema
await context.ui.elicit(
    "Enter data",
    schema={"type": "object", "properties": {"data": {"type": "object"}}}
)
# Expected: Error showing allowed primitive types
```

## Error Message Quality Checklist

For each error, verify:

- ✅ Starts with `✗` symbol (or `→` for informational)
- ✅ Clearly states what went wrong
- ✅ Provides specific context (which tool, file, value, etc.)
- ✅ Includes "To fix:" or "Possible causes:" section
- ✅ Shows concrete examples (commands, config values, etc.)
- ✅ States next steps (e.g., "Then restart the server")
- ✅ Avoids jargon or assumes minimal knowledge
- ✅ Points to documentation or listing commands when helpful

## Integration Testing

The error messages work end-to-end with:

1. **MCP Protocol**: Errors are properly formatted in JSON-RPC responses
2. **LLM Instructions**: Separate field provides detailed guidance
3. **Logging**: Errors are logged with full context
4. **Error Handling Middleware**: Converts exceptions to user-friendly messages

## Before/After Examples

### Before
```
ValueError: Invalid log level: TRACE. Must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
```

### After
```
✗ Invalid log level: 'TRACE'

  Valid options: DEBUG, INFO, WARNING, ERROR, CRITICAL

To fix, set MCP_MIDDLEWARE_LOG_LEVEL to one of the valid options:
  export MCP_MIDDLEWARE_LOG_LEVEL=INFO

Or in .env file:
  MCP_MIDDLEWARE_LOG_LEVEL=INFO
```

## Key Benefits Demonstrated

1. **Reduces friction** - Users don't need to search docs or guess
2. **Better DX** - Errors become self-service documentation
3. **Fewer support questions** - The answer is in the error
4. **Faster debugging** - Specific fix instructions save time
5. **Improved onboarding** - New users can self-correct issues

## Inspiration

These error messages follow patterns from:
- **Elm Compiler**: Friendly, educational error messages
- **Rust Compiler**: Suggests specific fixes with examples
- **Next.js**: Clear problem statements with documentation links

## Related Documentation

- Linear Issue: TOO-199
- Error Handling Guide: (to be created)
- MCP Protocol Spec: https://modelcontextprotocol.io

## Contributing

When adding new errors:
1. Use the `✗` marker for errors
2. Provide concrete fix instructions
3. Show examples where helpful
4. Test that the error is clear to someone unfamiliar with the codebase
5. Add test case to `test_actionable_errors.py`

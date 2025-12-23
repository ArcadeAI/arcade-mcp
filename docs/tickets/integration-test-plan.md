# Integration Test Plan: New Evaluation Features

**Date:** December 2024
**Status:** Planning
**Scope:** Integration tests for staged changes (multi-format output, capture mode, comparative evaluations, auth headers, SSE transport)

---

## 🎯 Test Objectives

Test the following new features end-to-end with real MCP servers:

1. **Multi-Format Output** (`--format txt,md,html,json,all`)
2. **Capture Mode** (`--capture`, `--add-context`)
3. **Failed-Only Filtering** (`--failed-only`)
4. **Comparative Evaluations** (multiple tool tracks)
5. **Multi-Model Evaluations** (`--models gpt-4o,gpt-4o-mini`)
6. **SSE/HTTP Transport** (real server connection)
7. **Auth via Headers** (ResourceServerAuth)
8. **OpenAI Strict-Mode Enum Fix** (integer/boolean enums)

---

## 📁 Test Structure

```
examples/mcp_servers/integration_tests/
├── pyproject.toml
├── src/
│   └── integration_tests/
│       ├── __init__.py
│       ├── server.py              # MCP server with various tool types
│       └── tools/
│           ├── __init__.py
│           ├── basic_tools.py     # Simple tools for basic tests
│           ├── enum_tools.py      # Tools with integer/boolean enums
│           ├── auth_tools.py      # Tools requiring auth
│           └── complex_tools.py   # Tools for edge cases
└── evals/
    ├── __init__.py
    ├── test_multi_format.py       # Multi-format output tests
    ├── test_capture_mode.py       # Capture mode tests
    ├── test_comparative.py        # Comparative evaluation tests
    ├── test_multi_model.py        # Multi-model comparison tests
    ├── test_failed_only.py        # Failed-only filtering tests
    └── test_enum_handling.py      # OpenAI strict-mode enum tests
```

---

## 🔧 Test Server: `integration_tests`

### Basic Tools (`basic_tools.py`)

```python
from typing import Annotated
from arcade_mcp_server import Context

def greet(name: Annotated[str, "Name to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"

def add(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Add two numbers."""
    return a + b

def get_weather(
    city: Annotated[str, "City name"],
    units: Annotated[str, "Temperature units (celsius/fahrenheit)"] = "celsius"
) -> dict:
    """Get weather for a city (mock)."""
    return {"city": city, "temp": 22, "units": units}
```

### Enum Tools (`enum_tools.py`)

```python
from typing import Annotated, Literal

def set_priority(
    task: Annotated[str, "Task name"],
    priority: Annotated[Literal[1, 2, 3], "Priority level (1=high, 2=medium, 3=low)"]
) -> str:
    """Set task priority using integer enum."""
    return f"Set {task} to priority {priority}"

def toggle_feature(
    feature: Annotated[str, "Feature name"],
    enabled: Annotated[Literal[True, False], "Enable or disable"]
) -> str:
    """Toggle feature using boolean enum."""
    return f"Feature {feature} {'enabled' if enabled else 'disabled'}"

def set_status(
    item: Annotated[str, "Item name"],
    status: Annotated[Literal["pending", "active", "completed"], "Item status"]
) -> str:
    """Set item status using string enum."""
    return f"Set {item} to {status}"
```

### Auth Tools (`auth_tools.py`)

```python
from typing import Annotated
from arcade_mcp_server import Context

def get_user_profile(context: Context) -> dict:
    """Get authenticated user's profile (requires auth header)."""
    # This would use context.get_auth_token_or_empty()
    return {"user": "authenticated_user", "role": "admin"}

def whisper_secret(context: Context) -> str:
    """Reveal a secret (requires secrets)."""
    try:
        secret = context.get_secret("TEST_SECRET")
        return f"Secret ends with: {secret[-4:]}"
    except Exception as e:
        return f"Error: {e}"
```

---

## 📋 Test Cases by Feature

### 1. Multi-Format Output Tests

| Test Case | Description | Command |
|-----------|-------------|---------|
| `test_single_txt_format` | Output to .txt file | `arcade evals . --file results --format txt` |
| `test_single_md_format` | Output to .md file | `arcade evals . --file results --format md` |
| `test_single_html_format` | Output to .html file | `arcade evals . --file results --format html` |
| `test_single_json_format` | Output to .json file | `arcade evals . --file results --format json` |
| `test_multiple_formats` | Output to multiple files | `arcade evals . --file results --format md,html,json` |
| `test_all_formats` | Output to all formats | `arcade evals . --file results --format all` |
| `test_format_case_insensitive` | Uppercase formats work | `arcade evals . --file results --format MD,HTML` |
| `test_utf8_encoding` | Non-ASCII content preserved | Test with unicode tool args |

### 2. Capture Mode Tests

| Test Case | Description | Command |
|-----------|-------------|---------|
| `test_capture_basic` | Capture tool calls without scoring | `arcade evals . --capture` |
| `test_capture_with_context` | Include system/additional messages | `arcade evals . --capture --add-context` |
| `test_capture_json_output` | Default JSON format for capture | `arcade evals . --capture --file capture` |
| `test_capture_multi_format` | Capture to multiple formats | `arcade evals . --capture --file capture --format all` |
| `test_capture_multi_model` | Capture with multiple models | `arcade evals . --capture --models gpt-4o,gpt-4o-mini` |

### 3. Failed-Only Filtering Tests

| Test Case | Description | Expected |
|-----------|-------------|----------|
| `test_failed_only_shows_only_failures` | Filter to failed cases | Only failed cases in output |
| `test_failed_only_shows_original_counts` | Summary shows original totals | "Total: 5" even if showing 2 failed |
| `test_failed_only_disclaimer` | Shows disclaimer message | "Showing only X failed evaluation(s)" |
| `test_failed_only_with_file` | Works with file output | File contains only failed cases |

### 4. Comparative Evaluation Tests

| Test Case | Description | Setup |
|-----------|-------------|-------|
| `test_comparative_two_tracks` | Compare two tool implementations | Two different MCP servers |
| `test_comparative_results_structure` | Results show per-track data | Suite name includes `[track_name]` |
| `test_comparative_formatter_display` | Formatters show track differences | Side-by-side comparison |
| `test_comparative_multi_model` | Comparative with multiple models | 2 tracks × 2 models |

### 5. Multi-Model Evaluation Tests

| Test Case | Description | Command |
|-----------|-------------|---------|
| `test_multi_model_basic` | Run with two models | `--models gpt-4o,gpt-4o-mini` |
| `test_multi_model_comparison_table` | Results show model comparison | Grouped by case, models compared |
| `test_multi_model_best_model_indicator` | Best model marked | ✓ indicator on best performer |
| `test_multi_model_all_formats` | Multi-model works with all formats | JSON/MD/HTML/TXT all show comparison |

### 6. SSE/HTTP Transport Tests

| Test Case | Description | Setup |
|-----------|-------------|-------|
| `test_sse_connection` | Connect to HTTP/SSE server | Start server with `transport="http"` |
| `test_sse_tool_listing` | List tools via SSE | Verify tools are discoverable |
| `test_sse_tool_execution` | Execute tool via SSE | Call tool and verify response |
| `test_sse_streaming_response` | Handle streaming responses | Long-running tool with progress |

### 7. Auth via Headers Tests

| Test Case | Description | Setup |
|-----------|-------------|-------|
| `test_auth_header_passing` | Auth header passed to server | ResourceServerAuth configured |
| `test_secret_access` | Tool can access secrets | `requires_secrets=["KEY"]` |
| `test_oauth_token_flow` | OAuth token available | `requires_auth=Provider(scopes=[...])` |
| `test_unauthorized_rejection` | Missing auth is rejected | 401/403 response handling |

### 8. OpenAI Strict-Mode Enum Tests

| Test Case | Description | Input → Output |
|-----------|-------------|----------------|
| `test_integer_enum_conversion` | Int enums become strings | `[1, 2, 3]` → `["1", "2", "3"]` |
| `test_boolean_enum_conversion` | Bool enums become strings | `[True, False]` → `["True", "False"]` |
| `test_type_updated_to_string` | Type changes to match enum | `"integer"` → `"string"` |
| `test_nullable_type_preserved` | Null union preserved | `["integer", "null"]` → `["string", "null"]` |
| `test_string_enum_unchanged` | String enums untouched | `["a", "b"]` stays same |

---

## 🧪 Sample Eval Suite: `test_multi_format.py`

```python
from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    tool_eval,
)

import integration_tests
from integration_tests.tools.basic_tools import greet, add

catalog = ToolCatalog()
catalog.add_module(integration_tests)

rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


@tool_eval()
def multi_format_test_suite() -> EvalSuite:
    """Suite for testing multi-format output."""
    suite = EvalSuite(
        name="Multi-Format Output Tests",
        catalog=catalog,
        system_message="You are a helpful assistant. Use the available tools.",
        rubric=rubric,
    )

    # Case 1: Simple string argument
    suite.add_case(
        name="Greet Alice",
        user_message="Please greet Alice",
        expected_tool_calls=[
            ExpectedToolCall(func=greet, args={"name": "Alice"})
        ],
        critics=[BinaryCritic(critic_field="name", weight=1.0)],
    )

    # Case 2: Numeric arguments
    suite.add_case(
        name="Add numbers",
        user_message="What is 5 plus 3?",
        expected_tool_calls=[
            ExpectedToolCall(func=add, args={"a": 5, "b": 3})
        ],
        critics=[
            NumericCritic(critic_field="a", value_range=(0, 10), weight=0.5),
            NumericCritic(critic_field="b", value_range=(0, 10), weight=0.5),
        ],
    )

    # Case 3: Unicode content (for UTF-8 encoding test)
    suite.add_case(
        name="Greet with unicode",
        user_message="Greet 日本語",
        expected_tool_calls=[
            ExpectedToolCall(func=greet, args={"name": "日本語"})
        ],
        critics=[BinaryCritic(critic_field="name", weight=1.0)],
    )

    return suite
```

---

## 🧪 Sample Eval Suite: `test_enum_handling.py`

```python
from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import integration_tests
from integration_tests.tools.enum_tools import set_priority, toggle_feature, set_status

catalog = ToolCatalog()
catalog.add_module(integration_tests)


@tool_eval()
def enum_handling_test_suite() -> EvalSuite:
    """Suite for testing OpenAI strict-mode enum handling."""
    suite = EvalSuite(
        name="Enum Handling Tests",
        catalog=catalog,
        system_message="You are a task manager. Use tools to manage tasks.",
        rubric=EvalRubric(fail_threshold=0.8),
    )

    # Integer enum
    suite.add_case(
        name="Set high priority",
        user_message="Set 'urgent task' to high priority",
        expected_tool_calls=[
            ExpectedToolCall(func=set_priority, args={"task": "urgent task", "priority": 1})
        ],
        critics=[
            BinaryCritic(critic_field="task", weight=0.5),
            BinaryCritic(critic_field="priority", weight=0.5),
        ],
    )

    # Boolean enum
    suite.add_case(
        name="Enable dark mode",
        user_message="Enable the dark mode feature",
        expected_tool_calls=[
            ExpectedToolCall(func=toggle_feature, args={"feature": "dark mode", "enabled": True})
        ],
        critics=[
            BinaryCritic(critic_field="feature", weight=0.5),
            BinaryCritic(critic_field="enabled", weight=0.5),
        ],
    )

    # String enum
    suite.add_case(
        name="Mark as completed",
        user_message="Mark the 'review PR' item as completed",
        expected_tool_calls=[
            ExpectedToolCall(func=set_status, args={"item": "review PR", "status": "completed"})
        ],
        critics=[
            BinaryCritic(critic_field="item", weight=0.5),
            BinaryCritic(critic_field="status", weight=0.5),
        ],
    )

    return suite
```

---

## 🧪 Sample Eval Suite: `test_comparative.py`

```python
from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedMCPToolCall,
    TrackConfig,
    tool_eval,
)


@tool_eval()
def comparative_test_suite() -> EvalSuite:
    """Suite for testing comparative evaluations across tool tracks."""
    suite = EvalSuite(
        name="Comparative Tool Tests",
        system_message="You are a helpful assistant.",
        rubric=EvalRubric(fail_threshold=0.8),
    )

    # Define two tracks: original MCP server vs new MCP server
    suite.add_track(
        "original",
        TrackConfig(mcp_endpoint="http://localhost:8001/mcp")
    )
    suite.add_track(
        "optimized",
        TrackConfig(mcp_endpoint="http://localhost:8002/mcp")
    )

    # Add comparative case that runs on both tracks
    suite.add_comparative_case(
        name="Greet user",
        user_message="Greet the user named Charlie",
        expected_tool_calls={
            "original": [ExpectedMCPToolCall(tool_name="OriginalServer_Greet", args={"name": "Charlie"})],
            "optimized": [ExpectedMCPToolCall(tool_name="OptimizedServer_Greet", args={"name": "Charlie"})],
        },
        critics=[BinaryCritic(critic_field="name", weight=1.0)],
    )

    return suite
```

---

## 🏃 Running the Integration Tests

### Prerequisites

```bash
# Install dev dependencies
cd /path/to/arcade-mcp
uv sync --all-extras

# Set up API keys (required for real model calls)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Start Test Server (in separate terminal)

```bash
cd examples/mcp_servers/integration_tests
uv run python -m integration_tests.server http
# Server runs at http://127.0.0.1:8000/mcp
```

### Run All Integration Tests

```bash
# Full integration test suite
cd examples/mcp_servers/integration_tests
arcade evals evals/ --models gpt-4o --format all --file results/integration
```

### Run Specific Test Categories

```bash
# Multi-format tests
arcade evals evals/test_multi_format.py --format all --file results/multi_format

# Capture mode tests
arcade evals evals/test_capture_mode.py --capture --format json --file results/capture

# Comparative tests (requires two servers running)
arcade evals evals/test_comparative.py --format md --file results/comparative

# Enum handling tests
arcade evals evals/test_enum_handling.py --format json --file results/enums
```

---

## ✅ Verification Checklist

### Multi-Format Output
- [ ] `.txt` file created with plain text formatting
- [ ] `.md` file created with valid Markdown tables
- [ ] `.html` file created with styled HTML (viewable in browser)
- [ ] `.json` file created with valid, parseable JSON
- [ ] All files contain same evaluation data
- [ ] UTF-8 characters preserved correctly

### Capture Mode
- [ ] Tool calls recorded without scoring
- [ ] `--add-context` includes system message
- [ ] JSON output is properly structured
- [ ] Multi-model capture groups by case

### Failed-Only
- [ ] Only failed cases shown
- [ ] Original totals in summary
- [ ] Disclaimer message displayed
- [ ] Works with file output

### Comparative
- [ ] Results separated by track
- [ ] Track name in suite name (`Suite [track1]`)
- [ ] Differences highlighted

### Multi-Model
- [ ] Results grouped by case
- [ ] All models evaluated
- [ ] Best model indicated
- [ ] Comparison table in formatters

### SSE Transport
- [ ] Server starts on HTTP port
- [ ] Client connects via SSE
- [ ] Tools executed correctly
- [ ] Streaming responses work

### Auth Headers
- [ ] Auth header forwarded to server
- [ ] Secrets accessible
- [ ] Unauthorized requests rejected

### Enum Handling
- [ ] Integer enums converted to strings
- [ ] Boolean enums converted to strings
- [ ] Schema type updated to "string"
- [ ] No OpenAI validation errors

---

## 📊 Expected Outputs

### Sample JSON Output (`results.json`)
```json
{
  "evaluation": {
    "models": ["gpt-4o"],
    "total_cases": 3,
    "passed": 3,
    "failed": 0,
    "warned": 0
  },
  "suites": [
    {
      "name": "Multi-Format Output Tests",
      "model": "gpt-4o",
      "cases": [
        {
          "name": "Greet Alice",
          "status": "passed",
          "score": 1.0,
          "details": {
            "tool_selection": {"match": true, "score": 1.0},
            "arguments": [
              {"field": "name", "expected": "Alice", "actual": "Alice", "match": true}
            ]
          }
        }
      ]
    }
  ]
}
```

### Sample Markdown Output (`results.md`)
```markdown
# Evaluation Results

## Summary
| Metric | Value |
|--------|-------|
| Total Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Warnings | 0 |

## Multi-Format Output Tests (gpt-4o)

| Status | Case | Score |
|--------|------|-------|
| ✅ | Greet Alice | 100% |
| ✅ | Add numbers | 100% |
| ✅ | Greet with unicode | 100% |
```

---

## 🔍 Troubleshooting

### Common Issues

1. **"No evaluations completed successfully"**
   - Check API key is set
   - Verify server is running
   - Check network connectivity

2. **"Tool not found"**
   - Verify tool is registered in catalog
   - Check tool naming convention

3. **"Unsupported format"**
   - Use lowercase format names
   - Valid formats: txt, md, html, json

4. **OpenAI validation error with enums**
   - Ensure schema converter is applied
   - Check enum values are stringified

---

*This test plan covers all new features from the staged changes and provides a comprehensive framework for integration testing.*


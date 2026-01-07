# Arcade Evals Examples

This directory contains user-friendly examples demonstrating how to evaluate tools from different sources using the Arcade evals framework.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Example Files](#example-files)
- [CLI Reference](#cli-reference)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### What Makes These Examples Different

These examples are designed to be:
- **Production-ready**: Include proper error handling and timeouts
- **Copy-paste friendly**: Clear configuration sections you can modify
- **Informative**: Print status messages during loading
- **Focused**: One concept per example, no unnecessary complexity
- **Pattern-based**: Follow consistent structure from real-world evals

### Installation

```bash
# Install with evals support
pip install 'arcade-mcp[evals]'

# Or using uv (recommended)
uv tool install 'arcade-mcp[evals]'
```

### Basic Usage

```bash
# Run an evaluation with OpenAI
arcade evals examples/evals/eval_arcade_gateway.py \
    --api-key openai:YOUR_OPENAI_KEY

# Compare multiple models
arcade evals examples/evals/eval_stdio_mcp_server.py \
    -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \
    -k openai:YOUR_OPENAI_KEY \
    -k anthropic:YOUR_ANTHROPIC_KEY

# Output results to HTML
arcade evals examples/evals/eval_http_mcp_server.py \
    --api-key openai:YOUR_KEY \
    -o results.html -d
```

## 📚 Example Files

### Example Structure

All examples follow a consistent pattern:

```python
# 1. Configuration section - Update these values
ARCADE_API_KEY = os.environ.get("ARCADE_API_KEY", "YOUR_KEY_HERE")

# 2. Eval suite with async loading
@tool_eval()
async def eval_my_suite() -> EvalSuite:
    suite = EvalSuite(name="...", system_message="...", rubric=...)

    # 3. Load tools with timeout and error handling
    try:
        await asyncio.wait_for(
            suite.add_arcade_gateway(...),
            timeout=10.0,
        )
        print("  ✓ Source loaded")
    except Exception as e:
        print(f"  ✗ Source failed: {e}")
        return suite

    # 4. Add test cases
    suite.add_case(name="...", user_message="...", ...)

    return suite
```

This pattern ensures:
- Clear configuration at the top
- Robust error handling
- Informative output during loading
- Graceful degradation if sources fail

### 1. `eval_arcade_gateway.py`

Evaluates tools from Arcade Gateway (cloud-hosted toolkits).

**What it demonstrates:**

- Async loading from Arcade Gateway with timeout handling
- Error handling for connection failures
- Math toolkit evaluations
- BinaryCritic for parameter validation
- Conversational context with additional_messages

**Prerequisites:**

Before running this example, you need to set up an MCP Gateway:

1. **Get your API key** - [API Keys Setup Guide](https://docs.arcade.dev/en/get-started/setup/api-keys)
2. **Create an MCP Gateway** at [Arcade Portal](https://portal.arcade.dev)
3. **Add toolkits** (e.g., Math, GitHub, Slack) to your gateway
4. **Get your credentials:**
   - `ARCADE_API_KEY` - Your Arcade API key
   - `ARCADE_USER_ID` - Your user ID (found in portal settings)

📚 **Full setup guide:** [MCP Gateways Documentation](https://docs.arcade.dev/en/guides/create-tools/mcp-gateways)

**Requirements:**

- Arcade API key (get one at [arcade.dev](https://arcade.dev))
- LLM API key (OpenAI or Anthropic)

**Run it:**

```bash
# Set your Arcade API key
export ARCADE_API_KEY=your_arcade_key

arcade evals examples/evals/eval_arcade_gateway.py \
    --api-key openai:YOUR_OPENAI_KEY
```

### 2. `eval_stdio_mcp_server.py`

Evaluates tools from local MCP servers running via stdio (subprocess).

**What it demonstrates:**

- Loading from local stdio MCP servers (subprocesses)
- Using `add_mcp_stdio_server()` method
- Setting environment variables (PYTHONUNBUFFERED)
- Simple echo tool evaluations
- Async loading with timeout and error handling

**Requirements:**

- Local MCP server code
- Server dependencies installed
- LLM API key

**Run it:**

```bash
arcade evals examples/evals/eval_stdio_mcp_server.py \
    --api-key openai:YOUR_KEY
```

### 3. `eval_http_mcp_server.py`

Evaluates tools from remote MCP servers via HTTP or SSE.

**What it demonstrates:**

- Connecting to HTTP MCP endpoints
- Using SSE (Server-Sent Events) transport
- Authentication with Bearer tokens
- Error handling with timeouts

**Requirements:**

- Running HTTP/SSE MCP server
- Network connectivity
- LLM API key
- (Optional) Authentication token

**Run it:**

```bash
# Update the configuration in the file first, then run:
arcade evals examples/evals/eval_http_mcp_server.py \
    --api-key openai:YOUR_KEY
```

### 4. `eval_comprehensive_comparison.py`

Compares tool performance across multiple sources simultaneously.

**What it demonstrates:**

- Comparative evaluation across different tool sources
- Loading from multiple sources (Gateway, stdio, dict)
- Track-based evaluation (comparing same task across sources)
- Conditional test cases based on loaded sources
- Using SimilarityCritic for fuzzy matching

**Requirements:**

- Arcade API key (for Gateway)
- LLM API key
- (Optional) Local simple MCP server

**Run it:**

```bash
# Set environment variables
export ARCADE_API_KEY=your_key
export ARCADE_USER_ID=your_user_id

arcade evals examples/evals/eval_comprehensive_comparison.py \
    -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \
    -k openai:YOUR_KEY \
    -k anthropic:YOUR_KEY \
    -o comparison.html -d
```

## 🎯 CLI Reference

### New v2.0.0 Flags


| Flag                | Short | Description                                      | Example                                         |
| --------------------- | ------- | -------------------------------------------------- | ------------------------------------------------- |
| `--use-provider`    | `-p`  | Provider(s) and models (space-separated)         | `-p "openai:gpt-4o anthropic:claude-sonnet"`    |
| `--api-key`         | `-k`  | API key in`provider:key` format (repeatable)     | `-k openai:sk-... -k anthropic:sk-ant-...`      |
| `--output`          | `-o`  | Output file (auto-detects format from extension) | `-o results.html` or `-o results` (all formats) |
| `--only-failed`     | `-f`  | Show only failed evaluations                     | `--only-failed`                                 |
| `--include-context` |       | Include system messages and conversation history | `--include-context`                             |
| `--details`         | `-d`  | Show detailed output                             | `-d`                                            |
| `--max-concurrent`  |       | Max concurrent evaluations                       | `--max-concurrent 5`                            |
| `--capture`         |       | Capture mode (record tool calls without scoring) | `--capture`                                     |

### Provider & Model Selection

**Single provider with default model:**

```bash
arcade evals eval_file.py -p openai -k openai:YOUR_KEY
```

**Single provider with specific models:**

```bash
arcade evals eval_file.py -p "openai:gpt-4o,gpt-4o-mini" -k openai:YOUR_KEY
```

**Multiple providers (space-separated):**

```bash
arcade evals eval_file.py \
    -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \
    -k openai:YOUR_KEY \
    -k anthropic:YOUR_KEY
```

### Output Formats

**Auto-detect from extension:**

```bash
-o results.html    # HTML output
-o results.json    # JSON output
-o results.md      # Markdown output
-o results.txt     # Text output
```

**Multiple formats:**

```bash
-o results.html -o results.json  # Both HTML and JSON
```

**All formats:**

```bash
-o results  # Generates results.txt, results.md, results.html, results.json
```

## 🔧 Common Patterns

### Pattern 1: Compare OpenAI Models

```bash
arcade evals examples/evals/eval_arcade_gateway.py \
    -p "openai:gpt-4o,gpt-4o-mini,gpt-3.5-turbo" \
    -k openai:YOUR_KEY \
    -o comparison.html -d
```

### Pattern 2: OpenAI vs Anthropic

```bash
arcade evals examples/evals/eval_stdio_mcp_server.py \
    -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \
    -k openai:YOUR_OPENAI_KEY \
    -k anthropic:YOUR_ANTHROPIC_KEY \
    -o battle.html -d
```

### Pattern 3: Failed Tests Only

```bash
arcade evals examples/evals/eval_http_mcp_server.py \
    --api-key openai:YOUR_KEY \
    --only-failed -d
```

### Pattern 4: Comparative Evaluation

```bash
# Compare performance across multiple tool sources
arcade evals examples/evals/eval_comprehensive_comparison.py \
    -p "openai:gpt-4o anthropic:claude-sonnet-4-5-20250929" \
    -k openai:YOUR_KEY \
    -k anthropic:YOUR_KEY \
    -o comparison.html -d
```

### Pattern 5: Capture Mode (No Scoring)

```bash
# Record tool calls without evaluation
arcade evals examples/evals/eval_arcade_gateway.py \
    --capture \
    --api-key openai:YOUR_KEY \
    -o captured.json
```

### Pattern 6: Full Context Output

```bash
arcade evals examples/evals/eval_stdio_mcp_server.py \
    --api-key openai:YOUR_KEY \
    --include-context \
    -o full_results.html -d
```

## 🐛 Troubleshooting

### Error: "No module named 'openai'"

**Solution:** Install evals dependencies:

```bash
pip install 'arcade-mcp[evals]'
```

### Error: "API key not found for provider 'openai'"

**Solution:** Provide API key via flag or environment variable:

```bash
# Via flag
arcade evals eval_file.py --api-key openai:YOUR_KEY

# Via environment variable
export OPENAI_API_KEY=your_key
arcade evals eval_file.py
```

### Error: "Connection refused" (HTTP server)

**Solution:** Ensure your HTTP MCP server is running:

```bash
# Check if server is running
curl http://localhost:8000/mcp

# Start your server first
python server.py
```

### Error: "Module not found" (stdio server)

**Solution:** Install server dependencies:

```bash
cd examples/mcp_servers/simple
uv sync
```

### Evals run but all tests fail

**Possible causes:**

1. Wrong tool names - check your server's tool definitions
2. Incorrect argument names - verify expected vs actual
3. Server not responding - check server logs
4. API key issues - verify LLM provider keys

**Debug with verbose output:**

```bash
arcade evals eval_file.py --api-key openai:YOUR_KEY -d
```

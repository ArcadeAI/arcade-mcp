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
    -p openai:gpt-4o \
    -p anthropic:claude-sonnet-4-5-20250929 \
    -k openai:YOUR_OPENAI_KEY \
    -k anthropic:YOUR_ANTHROPIC_KEY

# Output results to HTML
arcade evals examples/evals/eval_http_mcp_server.py \
    --api-key openai:YOUR_KEY \
    -o results.html -d
```

## 📚 Example Files

### Judge critics and evaluation quality

These standalone scripts review text or eval definitions without running
the model that generates tool calls:

```bash
uv run --extra evals python examples/evals/eval_judge_critics.py
uv run --extra evals python examples/evals/eval_case_quality.py
```

Both default to offline demo backends with **illustrative scripted scores**.
They demonstrate the integration and pass/fail policies, not model accuracy.

- `eval_judge_critics.py`: semantic similarity, intention/tone, groundedness,
  completeness, repeated-call caching, and backend diagnostics. Four passing
  and four failing examples.
- `eval_case_quality.py`: context sufficiency, complexity, answer leakage,
  ambiguity, and realistic wording. Two passing and four failing examples;
  legitimate IDs and explicit arguments can pass.
- `eval_case_quality_calibration.py`: offline fixture calibration with
  per-dimension threshold ranges; `--backend jev --limit N` for bounded live runs.
- `eval_grouped_judges.py`: batched judgments over a structured document argument.

For actual judgments, select a provider explicitly:

```bash
# Uses JEV_API_KEY or TYPESAFE_API_KEY; sends the example data to Jev.
uv run --extra evals python examples/evals/eval_case_quality.py --backend jev

# Uses OPENAI_API_KEY; any configured OpenAI-compatible client can be injected.
uv run --extra evals python examples/evals/eval_judge_critics.py --backend llm --model YOUR_MODEL
```

`JudgeBackend` is the provider-neutral interface. Jev's System One endpoint,
an OpenAI-compatible LLM, and a custom backend share the same contract.
`CaseQualityGrader(backend=...)` can review `suite.cases` independently of
execution. Provider errors raise `JudgeError`; live outcomes may differ from
the scripted examples. The normal `arcade evals` CLI examples continue below.

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
    -p openai:gpt-4o \
    -p anthropic:claude-sonnet-4-5-20250929 \
    -k openai:YOUR_KEY \
    -k anthropic:YOUR_KEY \
    -o comparison.html -d
```

## 🎯 CLI Reference

### Flags


| Flag                    | Short | Description                                           | Example                                             |
| ----------------------- | ----- | ----------------------------------------------------- | --------------------------------------------------- |
| `--use-provider`        | `-p`  | Provider and models (repeatable)                      | `-p openai:gpt-4o -p anthropic:claude-sonnet`       |
| `--api-key`             | `-k`  | API key in `provider:key` format (repeatable)         | `-k openai:sk-... -k anthropic:sk-ant-...`          |
| `--output`              | `-o`  | Output file (auto-detects format from extension)      | `-o results.html` or `-o results` (all formats)     |
| `--only-failed`         | `-f`  | Show only failed evaluations                          | `--only-failed`                                     |
| `--include-context`     |       | Include system messages and conversation history      | `--include-context`                                 |
| `--details`             | `-d`  | Show detailed output                                  | `-d`                                                |
| `--max-concurrent`      |       | Max concurrent evaluations                            | `--max-concurrent 5`                                |
| `--capture`             |       | Capture mode (record tool calls without scoring)      | `--capture`                                         |
| `--num-runs`            | `-n`  | Number of runs per case (default: 1)                  | `-n 5`                                              |
| `--seed`                |       | Seed policy: `constant`, `random`, or an integer      | `--seed random` or `--seed 42`                      |
| `--multi-run-pass-rule` |       | Aggregation rule: `last` (default), `mean`, `majority`| `--multi-run-pass-rule majority`                    |

### Provider & Model Selection

**Single provider with default model:**

```bash
arcade evals eval_file.py -p openai -k openai:YOUR_KEY
```

**Single provider with specific models:**

```bash
arcade evals eval_file.py -p openai:gpt-4o,gpt-4o-mini -k openai:YOUR_KEY
```

**Multiple providers (use separate `-p` flags):**

```bash
arcade evals eval_file.py \
    -p openai:gpt-4o \
    -p anthropic:claude-sonnet-4-5-20250929 \
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
    -p openai:gpt-4o,gpt-4o-mini \
    -k openai:YOUR_KEY \
    -o comparison.html -d
```

### Pattern 2: OpenAI vs Anthropic

```bash
arcade evals examples/evals/eval_stdio_mcp_server.py \
    -p openai:gpt-4o \
    -p anthropic:claude-sonnet-4-5-20250929 \
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
    -p openai:gpt-4o \
    -p anthropic:claude-sonnet-4-5-20250929 \
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

### Pattern 7: Multi-Run Evaluation

Run each case multiple times to measure consistency and reduce variance:

```bash
# Run each case 5 times with random seeds, pass if majority of runs pass
arcade evals examples/evals/eval_arcade_gateway.py \
    --api-key openai:YOUR_KEY \
    --num-runs 5 \
    --seed random \
    --multi-run-pass-rule majority \
    -o stability.html -d
```

The output will include per-case statistics: mean score, standard deviation,
individual run results, and per-critic field breakdowns.

**Seed policies:**
- `constant` (default) — Uses a fixed seed (42) for reproducible results
- `random` — Uses a different random seed per run for variance testing
- An integer (e.g., `--seed 123`) — Uses the given seed for all runs

**Pass rules:**
- `last` (default) — Uses the last run's pass/fail result
- `mean` — Passes if mean score meets the rubric threshold
- `majority` — Passes if more than half of the runs pass

### Pattern 8: Multi-Run Capture Mode

Capture mode also supports multiple runs:

```bash
arcade evals examples/evals/eval_arcade_gateway.py \
    --capture \
    --num-runs 3 \
    --seed random \
    --api-key openai:YOUR_KEY \
    -o captured.json
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

# Integration Test Matrix: Comprehensive Feature Coverage

**Date:** December 2024
**Status:** Planning Phase
**Required naming:** Files must start with `eval_`

---

## 🎯 Test Dimensions

### Dimension 1: Tool/Input Source Types

| Source Type | Description | Transport | Example |
|-------------|-------------|-----------|---------|
| **Python Functions** | Tools defined as Python `@tool` decorated functions | N/A | `ExpectedToolCall(func=greet, args={"name": "Alice"})` |
| **Dict Args** | Tools with dict-based expected arguments | N/A | `ExpectedToolCall(func=add, args={"a": 1, "b": 2})` |
| **MCP Server (stdio)** | Tools from MCP server via stdio transport | stdio | `ExpectedMCPToolCall(tool_name="Server_Tool")` |
| **MCP Server (HTTP/SSE)** | Tools from MCP server via HTTP/SSE transport | HTTP | Local server at `http://localhost:8000/mcp` |
| **Remote MCP Server** | Tools from remote MCP servers | HTTP | `@modelcontextprotocol/server-*` |
| **MCP + Auth (GitHub)** | GitHub MCP server with PAT authentication | HTTP | `github.com/github/github-mcp-server` |

### Dimension 2: CLI Flags

| Flag | Values | Description | Compatibility |
|------|--------|-------------|---------------|
| `--format` | `txt`, `md`, `html`, `json`, `md,html`, `all` | Output format(s) | All modes |
| `--capture` | On/Off | Capture mode (no scoring) | Exclusive with `--failed-only`, `--details` |
| `--add-context` | On/Off | Include system/additional messages | Only with `--capture` |
| `--failed-only` | On/Off | Show only failures | Not with `--capture` |
| `--details` / `-d` | On/Off | Show detailed critic results | Not with `--capture` |
| `--models` | `gpt-4o`, `gpt-4o,gpt-4o-mini` | Single or multi-model | All modes |
| `--file` | Path | Output to file | With `--format` |
| `--provider` | `openai`, `anthropic` | Model provider | All modes |

---

## 📊 Master Test Combination Matrix

### A. Input Source × Mode Matrix

| Eval File | Source Type | Mode | --format | --models | Description |
|-----------|-------------|------|----------|----------|-------------|
| `eval_python_basic.py` | Python funcs | Eval | `all` | single | Basic Python tools with all formats |
| `eval_python_multi_model.py` | Python funcs | Eval | `all` | multi | Python tools comparing GPT-4o vs GPT-4o-mini |
| `eval_python_capture.py` | Python funcs | Capture | `json` | single | Capture Python tool calls |
| `eval_python_capture_context.py` | Python funcs | Capture | `all` | single | Capture with `--add-context` |
| `eval_dict_args.py` | Dict args | Eval | `json` | single | Dict-based expected args |
| `eval_enum_strict_mode.py` | Python funcs (enums) | Eval | `json` | single | OpenAI strict-mode enum handling |
| `eval_mcp_stdio.py` | MCP (stdio) | Eval | `md` | single | Local MCP server via stdio |
| `eval_mcp_http_sse.py` | MCP (HTTP) | Eval | `html` | single | Local MCP server via HTTP/SSE |
| `eval_mcp_capture.py` | MCP (HTTP) | Capture | `all` | single | Capture MCP tool calls |
| `eval_remote_fetch.py` | Remote MCP | Eval | `md` | single | `@modelcontextprotocol/server-fetch` |
| `eval_remote_time.py` | Remote MCP | Eval | `json` | single | `@modelcontextprotocol/server-time` |
| `eval_github_pat_auth.py` | GitHub MCP + PAT | Eval | `all` | single | GitHub server with PAT auth |
| `eval_mixed_python_mcp.py` | Python + MCP | Eval | `all` | multi | Mix of sources, multi-model |
| `eval_comparative_tracks.py` | Multiple MCP servers | Comparative | `md,json` | single | Compare two MCP server tracks |
| `eval_failed_only.py` | Python funcs | Eval | `txt` | single | Test `--failed-only` flag |

---

### B. Flag Combination Detail Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            FLAG COMBINATIONS BY MODE                                    │
├───────────────────┬────────────────────┬────────────────────┬──────────────────────────┤
│ Mode              │ Required Flags     │ Optional Flags     │ Incompatible Flags       │
├───────────────────┼────────────────────┼────────────────────┼──────────────────────────┤
│ Standard Eval     │ (none)             │ --format           │ --add-context            │
│                   │                    │ --models           │                          │
│                   │                    │ --file             │                          │
│                   │                    │ --failed-only      │                          │
│                   │                    │ --details          │                          │
│                   │                    │ --provider         │                          │
├───────────────────┼────────────────────┼────────────────────┼──────────────────────────┤
│ Capture Mode      │ --capture          │ --format           │ --failed-only (ignored)  │
│                   │                    │ --add-context      │ --details (ignored)      │
│                   │                    │ --models           │                          │
│                   │                    │ --file             │                          │
│                   │                    │ --provider         │                          │
├───────────────────┼────────────────────┼────────────────────┼──────────────────────────┤
│ Comparative Eval  │ TrackConfig setup  │ --format           │ (same as Standard)       │
│                   │                    │ --models           │                          │
│                   │                    │ --file             │                          │
└───────────────────┴────────────────────┴────────────────────┴──────────────────────────┘
```

---

### C. Comprehensive Test Scenarios

| # | Scenario | Eval File | Command | What It Tests |
|---|----------|-----------|---------|---------------|
| 1 | Single format output | `eval_python_basic.py` | `arcade evals evals/ --format txt --file results` | Basic txt output |
| 2 | Multi-format output | `eval_python_basic.py` | `arcade evals evals/ --format md,html,json --file results` | Multiple files created |
| 3 | All formats | `eval_python_basic.py` | `arcade evals evals/ --format all --file results` | All 4 format files |
| 4 | Capture basic | `eval_python_capture.py` | `arcade evals evals/ --capture --file capture` | Capture mode |
| 5 | Capture + context | `eval_python_capture_context.py` | `arcade evals evals/ --capture --add-context --file capture` | Context in capture |
| 6 | Multi-model eval | `eval_python_multi_model.py` | `arcade evals evals/ --models gpt-4o,gpt-4o-mini --format all --file results` | Model comparison |
| 7 | Multi-model capture | `eval_python_capture.py` | `arcade evals evals/ --capture --models gpt-4o,gpt-4o-mini --file capture` | Multi-model capture |
| 8 | Failed-only | `eval_failed_only.py` | `arcade evals evals/ --failed-only --file results` | Only failures shown |
| 9 | Failed + details | `eval_failed_only.py` | `arcade evals evals/ --failed-only --details` | Detailed failures |
| 10 | MCP stdio | `eval_mcp_stdio.py` | `arcade evals evals/ --format md --file results` | Stdio transport |
| 11 | MCP HTTP/SSE | `eval_mcp_http_sse.py` | `arcade evals evals/ --format html --file results` | HTTP/SSE transport |
| 12 | Remote MCP | `eval_remote_fetch.py` | `arcade evals evals/ --format json --file results` | Remote server |
| 13 | GitHub PAT auth | `eval_github_pat_auth.py` | `arcade evals evals/ --format all --file results` | Auth via headers |
| 14 | Comparative | `eval_comparative_tracks.py` | `arcade evals evals/ --format md,json --file results` | Track comparison |
| 15 | Enum handling | `eval_enum_strict_mode.py` | `arcade evals evals/ --format json --file results` | OpenAI enum fix |
| 16 | Mixed sources | `eval_mixed_python_mcp.py` | `arcade evals evals/ --models gpt-4o,gpt-4o-mini --format all --file results` | Combined sources |

---

## 🌐 Remote MCP Servers for Testing

### Official MCP Servers (from `modelcontextprotocol/servers`)

| Server | Package | Transport | Auth | Tools |
|--------|---------|-----------|------|-------|
| **Fetch** | `@modelcontextprotocol/server-fetch` | stdio | None | `fetch_url` |
| **Time** | `@modelcontextprotocol/server-time` | stdio | None | `get_current_time` |
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | stdio | None | File operations |
| **Memory** | `@modelcontextprotocol/server-memory` | stdio | None | KV store |
| **Git** | `@modelcontextprotocol/server-git` | stdio | None | Git operations |

### GitHub MCP Server (Requires PAT)

| Server | Package | Auth | Setup |
|--------|---------|------|-------|
| **GitHub** | `@github/github-mcp-server` | PAT via headers | `GITHUB_PERSONAL_ACCESS_TOKEN` env var |

---

## 📁 Proposed File Structure

```
examples/mcp_servers/integration_evals/
├── pyproject.toml                    
├── README.md                         
├── src/integration_evals/
│   ├── __init__.py                   
│   ├── server.py                     # Local MCP server
│   └── tools/
│       ├── __init__.py
│       ├── basic_tools.py            # greet, add, get_weather
│       ├── enum_tools.py             # set_priority (int enum), toggle_feature (bool enum)
│       └── auth_tools.py             # Tools requiring auth
└── evals/
    ├── __init__.py
    │
    │── # Python function tests
    ├── eval_python_basic.py          # Basic Python tools
    ├── eval_python_multi_model.py    # Multi-model comparison
    ├── eval_python_capture.py        # Capture mode
    ├── eval_python_capture_context.py # Capture with context
    │
    │── # Dict/enum tests
    ├── eval_dict_args.py             # Dict-based args
    ├── eval_enum_strict_mode.py      # OpenAI enum handling
    │
    │── # MCP server tests (local)
    ├── eval_mcp_stdio.py             # Local stdio
    ├── eval_mcp_http_sse.py          # Local HTTP/SSE
    ├── eval_mcp_capture.py           # MCP capture
    │
    │── # Remote MCP tests
    ├── eval_remote_fetch.py          # @modelcontextprotocol/server-fetch
    ├── eval_remote_time.py           # @modelcontextprotocol/server-time
    │
    │── # Auth tests
    ├── eval_github_pat_auth.py       # GitHub with PAT
    │
    │── # Advanced tests
    ├── eval_mixed_python_mcp.py      # Mixed sources
    ├── eval_comparative_tracks.py    # Comparative evaluation
    └── eval_failed_only.py           # Failed-only filtering
```

---

## 🔑 Environment Variables Required

```bash
# Required for all tests
export OPENAI_API_KEY="sk-..."

# Required for multi-provider tests
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for GitHub MCP tests
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
```

---

## 🚀 Execution Order

### Phase 1: Python Tools (No external dependencies)
1. `eval_python_basic.py` - Basic functionality
2. `eval_python_capture.py` - Capture mode
3. `eval_python_capture_context.py` - Context capture
4. `eval_dict_args.py` - Dict args
5. `eval_enum_strict_mode.py` - Enum handling
6. `eval_failed_only.py` - Failed-only filter

### Phase 2: Local MCP Server (Requires running server)
7. Start server: `uv run python -m integration_evals.server http`
8. `eval_mcp_http_sse.py` - HTTP/SSE transport
9. `eval_mcp_capture.py` - MCP capture
10. Start server: `uv run python -m integration_evals.server stdio` 
11. `eval_mcp_stdio.py` - stdio transport

### Phase 3: Remote MCP Servers (Requires npm install)
12. Install: `npm install @modelcontextprotocol/server-fetch`
13. `eval_remote_fetch.py`
14. `eval_remote_time.py`

### Phase 4: Auth Tests (Requires PAT)
15. Set `GITHUB_PERSONAL_ACCESS_TOKEN`
16. `eval_github_pat_auth.py`

### Phase 5: Advanced (All dependencies)
17. `eval_python_multi_model.py` - Multi-model
18. `eval_mixed_python_mcp.py` - Mixed sources
19. `eval_comparative_tracks.py` - Comparative

---

## ✅ Expected Outputs

After running all scenarios with `--format all --file results/`:

```
results/
├── python_basic.txt
├── python_basic.md
├── python_basic.html
├── python_basic.json
├── capture.json
├── capture_context.json
├── multi_model.txt
├── multi_model.md
├── multi_model.html
├── multi_model.json
├── mcp_stdio.md
├── mcp_http_sse.html
├── remote_fetch.json
├── github_auth.json
├── comparative.md
├── comparative.json
└── failed_only.txt
```

---

## ❓ Questions Before Implementation

1. **Priority order?** Which scenarios should I implement first?

2. **Remote servers:** Should I set up the npm-based servers locally, or mock them?

3. **GitHub PAT:** Do you have a test PAT available, or should I create a mock auth test?

4. **Anthropic testing:** Should multi-model include Anthropic (`claude-sonnet-4-5-20250929`)?

5. **Comparative:** Which two MCP servers should be compared? (e.g., stdio vs HTTP of same server?)

---

*Awaiting your feedback before implementation.*


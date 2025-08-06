# Using Local Resources Example

Demonstrates how Arcade tools can interact with local resources including:
- Secrets management (database URLs, API keys)
- Local filesystem operations
- External API calls with caching
- Workspace file processing

## Setup

1. Copy and configure environment:
```bash
cp env.example .env
# Edit .env with your values
```

2. Create workspace directory:
```bash
mkdir -p workspace
echo "Sample document for analysis" > workspace/sample.txt
```

3. Install and run:
```bash
pip install arcade-ai
arcade serve
```

## Tools Included

### check_connections
Verifies connections to databases and services using secrets from the environment.

```bash
curl -X POST http://localhost:8002/worker/tools/CheckConnections
```

### analyze_document
Analyzes documents in the workspace using AI (mocked in local mode).

```bash
curl -X POST http://localhost:8002/worker/tools/AnalyzeDocument \
  -H "Content-Type: application/json" \
  -d '{"file_path": "sample.txt", "analysis_type": "keywords"}'
```

### cache_resource
Downloads and caches web resources locally.

```bash
curl -X POST http://localhost:8002/worker/tools/CacheResource \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.github.com/users/github"}'
```

### process_workspace_files
Lists, counts, or analyzes files in the workspace.

```bash
curl -X POST http://localhost:8002/worker/tools/ProcessWorkspaceFiles \
  -H "Content-Type: application/json" \
  -d '{"pattern": "*.txt", "operation": "list"}'
```

## Directory Structure

```
.
├── worker.toml          # Configuration
├── .env                # Secrets (git ignored)
├── toolkit/            # Tool implementations
├── workspace/          # Working directory for tools
└── cache/             # Downloaded resources cache
```

## Secrets Management

Tools that require secrets are marked with `@tool(requires_secrets=["SECRET_NAME"])`.
These secrets are:
- Read from environment variables
- Injected into the tool context
- Never exposed in responses

## Customization

Modify `worker.toml` to change default paths:

```toml
[worker.config.local_context.metadata]
workspace_path = "/custom/workspace"
cache_dir = "/custom/cache"
```
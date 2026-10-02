# Darkmoon MCP Server

An MCP server, built with `arcade-mcp-server`, that lets an agent drive [Darkmoon](https://github.com/ASCIT31/Dark-Moon): an open source (GPL-3.0) autonomous AI penetration testing platform that orchestrates specialist agents and offensive tools, can run on a local model, and proves each finding with a real exploit.

## Open source vs Pro

The Darkmoon engine and CLI are open source. These tools call the **Darkmoon Dashboard API**, which is part of **Darkmoon Pro** and always self-hosted: there is no public hosted endpoint, so you supply the base URL. `list_pull_requests` reads fix pull requests prepared by the Pro remediation agent (read only, never merged).

## Tools

| Tool | Description |
|---|---|
| `run_pentest` | Start an autonomous pentest against one authorized target and return the `run_id` |
| `get_run_status` | Report whether a run is `running`, `completed` or `error` from its run log |
| `list_campaigns` | List campaigns visible to the dashboard user |
| `get_findings` | Vulnerabilities and severity statistics for a campaign |
| `list_pull_requests` | Fix pull requests prepared by Pro remediation, optionally filtered by campaign and state |

Only run assessments against systems you own or are explicitly authorized in writing to test. Findings can include false positives and must be reviewed by a qualified human.

## Secrets

| Secret | Description |
|---|---|
| `DARKMOON_BASE_URL` | Base URL of your self-hosted Dashboard API, without trailing slash |
| `DARKMOON_USERNAME` | Dashboard user |
| `DARKMOON_PASSWORD` | Dashboard password (a JWT is requested on every call, nothing is cached) |

Copy `.env.example` to `.env` and fill it in, or set them with `arcade secret set`.

## Run it

```bash
cd examples/mcp_servers/darkmoon
uv sync --extra dev
uv run python src/darkmoon/server.py         # stdio transport (default)
uv run python src/darkmoon/server.py http    # HTTP+SSE transport
```

## Tests and evals

```bash
uv run pytest                                  # unit tests against a mocked Dashboard API
uv run arcade evals evals                      # tool-selection evals (needs an LLM API key)
```

## Datacache (DuckDB) Example Server

This example demonstrates the `@app.tool(datacache={keys:[...], ttl:...})` feature and `context.datacache.*` helpers.

### What it does
- Uses a DuckDB file as a per-tool, per-identity cache
- Downloads the DuckDB file from S3 before tool execution
- Uploads it back to S3 after tool execution
- Uses a Redis lock to ensure only one tool execution per cache key runs at a time

### Required environment variables
- `ARCADE_DATACACHE_REDIS_URL` (locking; still required for local storage)

### Local backend (default for this example)
This example defaults `ARCADE_DATACACHE_STORAGE_BACKEND=local` in code, so you don’t need to set it explicitly unless you want S3.

Set:
- `ARCADE_DATACACHE_REDIS_URL` (e.g. `redis://localhost:6379/0`)

Optional:
- `ARCADE_DATACACHE_LOCAL_DIR` (default: `/tmp/arcade_datacache`)

### S3 backend (how to switch)
Set:
- `ARCADE_DATACACHE_STORAGE_BACKEND=s3`
- `ARCADE_DATACACHE_REDIS_URL`
- `ARCADE_DATACACHE_S3_BUCKET`

Optional:
- `ARCADE_DATACACHE_S3_PREFIX` (default: `arcade/datacache`)
- `ARCADE_DATACACHE_AWS_REGION`
- `ARCADE_DATACACHE_S3_ENDPOINT_URL` (e.g. MinIO)
- `ARCADE_DATACACHE_AWS_ACCESS_KEY_ID`, `ARCADE_DATACACHE_AWS_SECRET_ACCESS_KEY`, `ARCADE_DATACACHE_AWS_SESSION_TOKEN`

### Running (http by default)
From this directory:

```bash
uv sync
uv run python -m datacache.server
```

### Calling tools with `_meta`
The datacache keys `organization` and `project` are read from the request `_meta` and propagated into `ToolContext.metadata`.

Your MCP client must include:
- `_meta.organization`
- `_meta.project`

`user_id` comes from the server’s normal `ToolContext.user_id` behavior.

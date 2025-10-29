# Docker Setup for MCP Servers

This directory contains a generalized Docker configuration template that can be used with any MCP server in this repository.

## Quick Start

1. **Copy the Docker files to your MCP server directory:**

   ```bash
   cp -r examples/docker-template/docker your-mcp-server/
   cp examples/docker-template/.dockerignore your-mcp-server/
   ```

2. **Determine your package name:**
   - Check `pyproject.toml` for the `name` field (e.g., `name = "logging"`)
   - Or look at your `src/` directory structure (e.g., `src/logging/` means package is `logging`)

3. **Update the Dockerfile:**
   - If your server is at `src/<package>/server.py`, set `PACKAGE_NAME`
   - If your server is at the root (`server.py`), you can leave `PACKAGE_NAME` empty

4. **Build and run:**

   ```bash
   cd your-mcp-server
   docker-compose -f docker/docker-compose.yml up --build
   ```

## Configuration

### Environment Variables

- `PACKAGE_NAME`: The name of your package (from `pyproject.toml` or `src/` structure)
  - Default: `logging`
  - Example: For `src/simple/`, set `PACKAGE_NAME=simple`
- `ARCADE_SERVER_TRANSPORT`: The transport protocol to use
  - Default: `http`
  - Options: `http`, `stdio`
- `ARCADE_SERVER_PORT`: The port to run the server on
  - Default: `8001`
- `ARCADE_SERVER_HOST`: The host to bind to
  - Default: `0.0.0.0`

### Example: Simple MCP Server

```bash
# From examples/mcp_servers/simple/
export PACKAGE_NAME=simple
docker-compose -f docker/docker-compose.yml up --build
```

You can customize the port by editing `docker/docker-compose.yml` and changing both the `ARCADE_SERVER_PORT` environment variable and the port mapping.

## Building the Image

```bash
docker build \
  -f docker/Dockerfile \
  --build-arg PACKAGE_NAME=your-package-name \
  -t your-mcp-server \
  .
```

## Running with Docker

```bash
docker run -p 8001:8001 \
  -e ARCADE_SERVER_TRANSPORT=http \
  -e ARCADE_SERVER_HOST=0.0.0.0 \
  -e ARCADE_SERVER_PORT=8001 \
  your-mcp-server
```

## Features

- **Arcade environment variable support**: Uses `ARCADE_SERVER_*` environment variables
- **Environment-based config**: Easy customization via environment variables
- **uv integration**: Uses uv for fast dependency management
- **Lightweight**: Based on Python 3.11 Bookworm slim image with uv

## Connecting from Cursor

Add to your `~/.cursor/mcp.json`:

```json
"your-server-name": {
  "name": "your-server-name",
  "type": "stream",
  "url": "http://localhost:8001"
}
```

Then restart Cursor to connect to the server.

# Docker Setup for MCP Servers

This directory contains a generalized Docker configuration template that can be used with any MCP server in this repository.

## Quick Start

1. **Copy the Docker files to your MCP server directory:**

   ```bash
   cp -r examples/docker-template/docker your-mcp-server/
   cp examples/docker-template/.dockerignore your-mcp-server/
   ```

2. **Build and run:**

   ```bash
   cd your-mcp-server
   docker-compose -f docker/docker-compose.yml up --build
   ```

## Configuration

### Package Detection

The Dockerfile uses the package name from `pyproject.toml` by reading the `[project] name` field. It expects your server file at `src/<package_name>/server.py` (where `<package_name>` is from `pyproject.toml`).

If the server file is not found at this location, then the build will fail with an error message showing the detected package name and available directories in `src/`.

### Environment Variables

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
docker-compose -f docker/docker-compose.yml up --build
```

You can customize the port by editing `docker/docker-compose.yml` and changing both the `ARCADE_SERVER_PORT` environment variable and the port mapping.

## Building the Image

```bash
docker build \
  -f docker/Dockerfile \
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

- **Automatic package detection**: Reads package name from `pyproject.toml`
- **Standard server location**: Expects server file at `src/<package>/server.py`
- **Secure by default**: Runs as non-root user
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

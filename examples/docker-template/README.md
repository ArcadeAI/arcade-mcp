# Docker Template for MCP Servers

This is a generalized Docker setup template that can be applied to any MCP server built with Arcade MCP

The Dockerfile automatically detects your package name from `pyproject.toml` and expects your server file at `src/<package_name>/server.py`.

## Quick Setup

### Option 1: Using the Setup Script (Recommended)

Run the setup script to automatically copy the Docker files to your MCP server:

```bash
cd examples/docker-template
./setup-docker.sh ../path/to/your-server-name
```

This will copy all necessary Docker files to your server directory.

### Option 2: Manual Setup

Copy the `docker/` directory to your MCP server:

```bash
cp -r examples/docker-template/docker your-server-name/
cp examples/docker-template/.dockerignore your-server-name/
```

## Usage

After setup, navigate to your MCP server directory and build/run:

```bash
cd your-server-name

# Build and run with docker-compose
docker-compose -f docker/docker-compose.yml up --build

# Or build and run manually
docker build -f docker/Dockerfile -t your-server .
docker run -p 8001:8001 your-server
```

The package name is automatically detected from `pyproject.toml`

## Configuration

Edit `docker/docker-compose.yml` to configure:
- `ARCADE_SERVER_PORT`: Server port (default: 8001)
- `ARCADE_SERVER_HOST`: Bind host (default: 0.0.0.0)
- `ARCADE_SERVER_TRANSPORT`: Transport type (default: http)

The package name is automatically detected from `pyproject.toml`

## What Gets Copied

The setup script copies these files to your MCP server:
- `docker/Dockerfile` - Docker image build instructions
- `docker/docker-compose.yml` - Docker Compose configuration
- `docker/README.md` - Detailed usage documentation
- `.dockerignore` - Files to exclude from Docker build

## Requirements

- Docker and Docker Compose installed
- MCP server with `pyproject.toml` and `uv.lock`
- Server file at `src/<package>/server.py`

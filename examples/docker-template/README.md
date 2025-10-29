# Docker Template for MCP Servers

This is a generalized Docker setup template that can be applied to any MCP server built with Arcade MCP

This template assumes your server's entrypoint file is located at `your_server_name/src/your_server_name/server.py`. If this is not the case, then you will need to alter the path to your entrypoint file in the Dockerfile.

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

# Or build manually
docker build -f docker/Dockerfile -t your-server .
docker run -p 8001:8001 -e PACKAGE_NAME=your-package-name your-server
```

## Configuration

Edit `docker/docker-compose.yml` to configure:
- `PACKAGE_NAME`: Your package name from `pyproject.toml`
- `PORT`: Server port (default: 8001)
- `HOST`: Bind host (default: 0.0.0.0)

## What Gets Copied

The setup script copies these files to your MCP server:
- `docker/Dockerfile` - Docker image build instructions
- `docker/docker-compose.yml` - Docker Compose configuration
- `docker/start.sh` - Server startup script
- `docker/README.md` - Detailed usage documentation
- `.dockerignore` - Files to exclude from Docker build

## Requirements

- Docker and Docker Compose installed
- MCP server with `pyproject.toml` and `uv.lock`
- Server file at `src/<package>/server.py` or root-level `server.py`

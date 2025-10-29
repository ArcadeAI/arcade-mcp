#!/bin/bash

# Setup Docker for MCP Server
# This script copies the Docker template files to your MCP server directory

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Docker for MCP Server${NC}"
echo ""

# Get the template directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR"

# Default target directory is the parent directory
TARGET_DIR="$(dirname "$SCRIPT_DIR")"

# Allow specifying a target directory
if [ -n "$1" ]; then
    TARGET_DIR="$1"
fi

echo "Template directory: $TEMPLATE_DIR"
echo "Target directory: $TARGET_DIR"
echo ""

# Check if target is a valid MCP server
if [ ! -f "$TARGET_DIR/pyproject.toml" ]; then
    echo -e "${RED}Error: $TARGET_DIR is not a valid MCP server (missing pyproject.toml)${NC}"
    exit 1
fi

# Check if docker directory already exists
if [ -d "$TARGET_DIR/docker" ]; then
    echo -e "${YELLOW}Warning: $TARGET_DIR/docker already exists${NC}"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 0
    fi
    rm -rf "$TARGET_DIR/docker"
fi

# Create docker directory
mkdir -p "$TARGET_DIR/docker"

# Copy files
echo "Copying Docker files..."
cp "$TEMPLATE_DIR/docker/Dockerfile" "$TARGET_DIR/docker/"
cp "$TEMPLATE_DIR/docker/docker-compose.yml" "$TARGET_DIR/docker/"
cp "$TEMPLATE_DIR/docker/README.md" "$TARGET_DIR/docker/"
cp "$TEMPLATE_DIR/.dockerignore" "$TARGET_DIR/"

echo -e "${GREEN}✓ Docker setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. (Optional) Update docker-compose.yml to customize:"
echo "     - ARCADE_SERVER_PORT (default: 8001)"
echo "     - ARCADE_SERVER_HOST (default: 0.0.0.0)"
echo "  2. Build and run:"
echo "     cd $TARGET_DIR"
echo "     docker-compose -f docker/docker-compose.yml up --build"
echo ""

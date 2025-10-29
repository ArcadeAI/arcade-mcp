FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Define build arguments
ARG PACKAGE_NAME=logging

# Set environment variables
ENV PACKAGE_NAME=${PACKAGE_NAME}

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose the port (will be set via environment)
EXPOSE 8001

# Run the server
CMD uv run src/${PACKAGE_NAME}/server.py

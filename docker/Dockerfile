# Use a lightweight Python image
FROM python:3.10-slim

# Define build arguments with default values
ARG PORT=8001
ARG HOST=0.0.0.0

# Set environment variables using the build arguments
ENV PORT=${PORT}
ENV HOST=${HOST}
ENV WORK_DIR=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    apt-utils \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the parent directory contents into the container
COPY . .

# Build the project and install the wheel with extras
RUN python -m pip install dist/arcade_ai-0.1.0-py3-none-any.whl[fastapi,dev] uvicorn

# Install toolkits from the toolkits directory
RUN set -e; \
    for toolkit in dist/toolkits/*; do \
        echo "Installing toolkit $toolkit"; \
        pip install $toolkit; \
    done


# Expose the port
EXPOSE $PORT

# Run the arcade dev command
CMD arcade dev --host $HOST --port $PORT

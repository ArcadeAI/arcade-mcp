# Use a lightweight Python image
FROM python:3.10-slim

# Define build arguments with default values
ARG PORT=8001
ARG HOST=0.0.0.0
ARG VERSION=0.1.0

# Set environment variables using the build arguments
ENV PORT=${PORT}
ENV HOST=${HOST}
ENV VERSION=${VERSION}
ENV OTEL_ENABLE=false
ENV ARCADE_WORK_DIR=/app

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

WORKDIR /app/arcade

# Copy the parent directory contents into the container
COPY ./dist .

# Install the wheel with extras (not evals for now)
RUN python -m pip install ./arcade_ai-${VERSION}-py3-none-any.whl
RUN python -m pip install -r ./requirements.txt

# Install toolkits from the toolkits directory
RUN set -e; \
    for toolkit in ./toolkits/*; do \
    echo "Installing toolkit $toolkit"; \
    python -m pip install $toolkit; \
    done


# Expose the port
EXPOSE $PORT

# Run the arcade actorup (hidden cli command)
CMD arcade actorup --host $HOST --port $PORT

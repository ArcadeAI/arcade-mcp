# Use a lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV POETRY_VERSION=1.8.3
ENV PORT=8001
ENV HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    apt-utils \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN python -m pip install "poetry==$POETRY_VERSION"

# Set the working directory
WORKDIR /app

# Copy the parent directory contents into the container
COPY . .

WORKDIR /app/arcade

# Build the project and install the wheel with extras
RUN python -m poetry build && \
    pip install dist/arcade_ai-0.1.0-py3-none-any.whl[fastapi,dev]

WORKDIR /app

# Install toolkits from the toolkits directory
RUN set -e; \
    for toolkit in /app/toolkits/*; do \
        echo "Installing toolkit $(basename $toolkit) "; \
        cd $toolkit; \
        python -m poetry build; \
        pip install dist/*.whl; \
    done

# Expose the port
EXPOSE $PORT

WORKDIR /app/arcade

RUN pip install uvicorn

# Run the arcade dev command
CMD arcade dev --host $HOST --port $PORT

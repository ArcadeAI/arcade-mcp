# Use a lightweight Python image
FROM python:3.10-slim

# Define build arguments with default values
ARG PORT=8001
ARG HOST=0.0.0.0

# Set environment variables using the build arguments
ENV PORT=${PORT}
ENV HOST=${HOST}
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

WORKDIR /app

RUN pip install build poetry

# Copy the parent directory contents into the container
COPY . .

WORKDIR /app/arcade

# Build the project
RUN python -m build

# Build the project and install the wheel with extras
RUN poetry export --with fastapi,dev,evals --output requirements.txt

# This doesnt install the optional packages for some reason
RUN python -m pip install dist/arcade_ai-0.1.0-py3-none-any.whl[fastapi,dev,evals] uvicorn
RUN python -m pip install -r requirements.txt

WORKDIR /app/toolkits

# Install toolkits from the toolkits directory
RUN set -e; \
    for toolkit in ./*; do \
    echo "Installing toolkit $toolkit"; \
    pip install $toolkit; \
    done


# Expose the port
EXPOSE $PORT

# Run the arcade dev command
CMD arcade dev --host $HOST --port $PORT

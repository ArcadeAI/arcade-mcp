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
ENV TOOLKITS="arcade-code-sandbox,arcade-github,arcade-google,arcade-linkedin,arcade-math,arcade-search,arcade-slack,arcade-spotify,arcade-web,arcade-x,arcade-zoom"

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
COPY ../dist /app/arcade/

# List files for debugging purposes
RUN ls -lah /app/arcade/


# Install the wheel with extras (not evals for now)
RUN python -m pip install ./arcade_ai-${VERSION}-py3-none-any.whl fastapi
RUN python -m pip install -r ./requirements.txt


# Expose the port
EXPOSE $PORT

# Run the arcade workerup (hidden cli command)
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]

FROM python:3.11-slim

# Define build arguments with default values
ARG PORT=8001
ARG HOST=0.0.0.0
ARG VERSION=${VERSION:-0.1.0.dev0}
ARG INSTALL_TOOLKITS=true

# Set environment variables using the build arguments
ENV PORT=${PORT}
ENV HOST=${HOST}
ENV OTEL_ENABLE=false
ENV ARCADE_WORK_DIR=/app

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    libssl-dev \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/arcade

# Copy the parent directory contents into the container
COPY ./dist ./arcade /app/arcade/

# Copy the toolkits.txt file into the container
COPY ./docker/toolkits.txt /app/arcade/

# Expose the port
EXPOSE $PORT

# List files for debugging purposes
RUN ls -la /app/arcade/

# Conditional installation based on version
RUN if [ ! "$(echo ${VERSION} | grep -E '\.dev0$')" ]; then \
    echo "Installing wheel file" && \
    python -m pip install ./arcade_ai-${VERSION}-py3-none-any.whl && \
    python -m pip install -r ./requirements.txt; \
    else \
    echo "Installing from source" && \
    cd /app/arcade && \
    pip install poetry && \
    poetry lock && \
    poetry version 0.1.0 && \
    pip install -r requirements.txt && \
    pip install .; \
    fi

# Conditionally install toolkits.txt dependencies
RUN if [ "$INSTALL_TOOLKITS" = "true" ] ; then \
    python -m pip install -r ./toolkits.txt ; \
    fi

# Run the arcade workerup (hidden cli command)
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]

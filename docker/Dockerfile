FROM python:3.11-slim

# Define build arguments with default values
ARG PORT=8001
ARG HOST=0.0.0.0
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

WORKDIR /app

# Copy the dist directory contents into the container
COPY ./dist /app/dist/

# Copy the toolkits.txt file into the container
COPY ./docker/toolkits.txt /app/

# Expose the port
EXPOSE $PORT

# List wheel files for debugging purposes
RUN ls -la /app/dist/

# Install the worker and CLI package
RUN python -m pip install \
    /app/dist/arcade_serve-*.whl \
    /app/dist/arcade_ai-*.whl

# Conditionally install toolkit wheels from dist directory if INSTALL_TOOLKITS is true and the toolkit is in toolkits.txt
RUN if [ "$INSTALL_TOOLKITS" = "true" ] ; then \
    while IFS= read -r toolkit; do \
        # Skip empty lines and comments (lines starting with #)
        if [ -n "$toolkit" ] && [ "${toolkit#\#}" = "$toolkit" ]; then \
            # Convert toolkit name to match wheel filename format (replace - with _)
            wheel_name=$(echo "$toolkit" | sed 's/-/_/g'); \
            wheel_file="/app/dist/${wheel_name}-"*.whl; \
            # Check if this is not a core package and if the wheel file exists
            if [ "$wheel_name" != "arcade_core" ] && \
               [ "$wheel_name" != "arcade_serve" ] && \
               [ "$wheel_name" != "arcade_ai" ] && \
               [ "$wheel_name" != "arcade_tdk" ]; then \
                if ls $wheel_file 1> /dev/null 2>&1; then \
                    echo "Installing $toolkit from $wheel_file"; \
                    python -m pip install $wheel_file; \
                else \
                    echo "Warning: Wheel file not found for $toolkit (looked for $wheel_file)"; \
                fi; \
            else \
                echo "Skipping core package: $toolkit"; \
            fi; \
        fi; \
    done < /app/toolkits.txt ; \
    fi

# Run the arcade worker
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]

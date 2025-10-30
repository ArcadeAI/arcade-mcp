FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Auto-detect package name from pyproject.toml
# First try using Python's tomllib
# Fallback to grep/sed for compatibility
RUN PACKAGE_NAME=$(python3 -c "import tomllib; f=open('pyproject.toml','rb'); data=tomllib.load(f); print(data['project']['name'])" 2>/dev/null || \
    grep -E '^name\s*=' pyproject.toml | head -1 | sed -E "s/.*name\s*=\s*[\"']([^\"']+)[\"'].*/\1/" || \
    grep -E '^name\s*=' pyproject.toml | head -1 | sed -E 's/.*name\s*=\s*([^ ]+).*/\1/') && \
    if [ -z "$PACKAGE_NAME" ]; then \
        echo "ERROR: Could not detect package name from pyproject.toml" && exit 1; \
    fi && \
    echo "Detected package: $PACKAGE_NAME" && \
    echo "$PACKAGE_NAME" > /tmp/package_name.txt

# Install dependencies
RUN uv sync --frozen --no-dev

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Expose the port
EXPOSE 8001

# Run the server from src/<package>/server.py
CMD PACKAGE_NAME=$(cat /tmp/package_name.txt) && \
    if [ -f "src/${PACKAGE_NAME}/server.py" ]; then \
        uv run src/${PACKAGE_NAME}/server.py; \
    else \
        echo "ERROR: Could not find server.py at src/${PACKAGE_NAME}/server.py" && \
        echo "  Package detected: ${PACKAGE_NAME}" && \
        echo "  Available directories in src/:" && \
        ls -la src/ 2>/dev/null || echo "  src/ directory not found" && \
        exit 1; \
    fi

FROM ghcr.io/astral-sh/uv:0.11.21-python3.11-trixie-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies (pctx-client resolves from PyPI, not local path)
RUN uv sync --frozen --no-dev

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

CMD uv run src/pctx_code_mode/server.py http

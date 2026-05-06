FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

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

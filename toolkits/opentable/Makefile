.PHONY: install test lint typecheck format clean

install:
	uv sync --all-extras

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check arcade_opentable/

typecheck:
	uv run mypy arcade_opentable/

format:
	uv run ruff format arcade_opentable/ tests/

clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

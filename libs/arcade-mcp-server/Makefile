
.PHONY: help
help:
	@echo "🛠️ Arcade MCP Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'



.PHONY: sync
sync: ## Sync dependencies
	uv sync --all-extras --all-packages --group dev

.PHONY: format
format: ## Run ruff format
	uv run ruff format

.PHONY: lint
lint: ## Run ruff lint
	uv run ruff check

.PHONY: mypy
mypy: ## Run mypy
	uv run mypy .

.PHONY: test
test: ## Run tests
	uv run pytest --cov=arcade_mcp_server --cov-report=term-missing ../tests/arcade_mcp_server

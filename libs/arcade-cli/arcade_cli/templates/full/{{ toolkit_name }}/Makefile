.PHONY: install build test lint dev

TOOLKIT := $(shell basename $(CURDIR))

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies, then overlay any ../.local-overrides
	uv sync --all-extras
	@if [ -f ../.local-overrides ]; then \
		while IFS= read -r pkg || [ -n "$$pkg" ]; do \
			case "$$pkg" in \#*|"") continue ;; esac; \
			echo "Applying local override: $$pkg"; \
			uv pip install -e "$$pkg"; \
		done < ../.local-overrides; \
	fi

build: ## Build wheel
	rm -rf dist
	uv build

test: ## Run tests with coverage
	uv run pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml

lint: ## Run linting and type checking
	uv run pre-commit run -a
	uv run mypy --config-file=pyproject.toml

dev: ## Run toolkit locally as MCP server
	ARCADE_WORKER_SECRET=dev uv run arcade_$(TOOLKIT) http

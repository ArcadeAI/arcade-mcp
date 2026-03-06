.PHONY: help

help:
	@echo "🛠️ posthog Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the uv environment and install all packages with dependencies
	@echo "🚀 Creating virtual environment and installing all packages using uv"
	@uv sync --active --all-extras --no-sources
	@if [ -f .pre-commit-config.yaml ]; then uv run --no-sources pre-commit install; fi
	@echo "✅ All packages and dependencies installed via uv"

.PHONY: install-local
install-local: ## Install the uv environment and install all packages with dependencies with local Arcade sources
	@echo "🚀 Creating virtual environment and installing all packages using uv"
	@uv sync --active --all-extras
	@if [ -f .pre-commit-config.yaml ]; then uv run pre-commit install; fi
	@echo "✅ All packages and dependencies installed via uv"

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	uv build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@echo "🗑️ Cleaning dist directory"
	rm -rf dist

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run --no-sources pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: coverage
coverage: ## Generate coverage report
	@echo "coverage report"
	@uv run --no-sources coverage report
	@echo "Generating coverage report"
	@uv run --no-sources coverage html

.PHONY: bump-version
bump-version: ## Bump the version in the pyproject.toml file by a patch version
	@echo "🚀 Bumping version in pyproject.toml"
	uv version --no-sources --bump patch

.PHONY: check
check: ## Run code quality tools.
	@if [ -f .pre-commit-config.yaml ]; then\
		echo "🚀 Linting code: Running pre-commit";\
		uv run --no-sources pre-commit run -a;\
	fi
	@echo "🚀 Static type checking: Running mypy"
	@uv run --no-sources mypy --config-file=pyproject.toml

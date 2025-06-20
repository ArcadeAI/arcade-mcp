.PHONY: help

help:
	@echo "🛠️ Zendesk Toolkit Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the uv environment and install all packages with dependencies
	@echo "🚀 Creating virtual environment and installing all packages using uv"
	@uv sync --all-extras --no-sources
	@uv run pre-commit install
	@echo "✅ All packages and dependencies installed via uv"

.PHONY: install-local
install-local: ## Install the uv environment and install all packages with dependencies with local Arcade sources
	@echo "🚀 Creating virtual environment and installing all packages using uv"
	@uv sync --all-extras
	@uv run pre-commit install
	@echo "✅ All packages and dependencies installed via uv"

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	uv build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@echo "🗑️ Cleaning dist directory"
	rm -rf dist

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: coverage
coverage: ## Generate coverage report
	@echo "coverage report"
	coverage report
	@echo "Generating coverage report"
	coverage html

.PHONY: bump-version
bump-version: ## Bump the version in the pyproject.toml file by a patch version
	@echo "🚀 Bumping version in pyproject.toml"
	uv version --bump patch

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy --config-file=pyproject.toml

.PHONY: serve
serve: ## Run arcade serve with local development setup
	@echo "🚀 Starting arcade serve"
	@uv run arcade serve

.PHONY: eval
eval: ## Run tool evaluations
	@echo "🧪 Running evaluations for Zendesk toolkit"
	@uv run arcade evals ./evals --max-concurrent 5 --details 2>&1 | tee evals_log.txt

.PHONY: eval-cloud
eval-cloud: ## Run evaluations against Arcade Cloud
	@echo "☁️  Running evaluations against Arcade Cloud"
	@uv run arcade evals ./evals --cloud --details

.PHONY: eval-models
eval-models: ## Run evaluations with multiple models
	@echo "🤖 Running evaluations with multiple models (gpt-4o, claude-3-opus)"
	@uv run arcade evals ./evals --models gpt-4o,claude-3-opus --details

.PHONY: eval-fast
eval-fast: ## Run evaluations with increased concurrency
	@echo "⚡ Running evaluations with increased concurrency"
	@uv run arcade evals ./evals --max-concurrent 5 --details

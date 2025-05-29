.PHONY: help

help:
	@echo "🛠️ {{ toolkit_name }} Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "📦 Checking if Poetry is installed"
	@if ! command -v poetry >/dev/null 2>&1; then \
        echo "📦 Poetry not found. Checking if pip is available"; \
		if ! command -v pip >/dev/null 2>&1; then \
			echo "❌ pip is not installed. Please install pip first."; \
			exit 1; \
		fi; \
		echo "📦 Installing Poetry with pip"; \
		pip install poetry==1.8.5; \
	else \
		echo "📦 Poetry is already installed"; \
	fi
	@echo "🚀 Installing package in development mode with all extras"
	poetry install --all-extras

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	poetry build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@echo "🗑️ Cleaning dist directory"
	rm -rf dist

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@poetry run pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: coverage
coverage: ## Generate coverage report
	@echo "coverage report"
	coverage report
	@echo "Generating coverage report"
	coverage html

.PHONY: bump-version
bump-version: ## Bump the version in the pyproject.toml file
	@echo "🚀 Bumping version in pyproject.toml"
	poetry version patch

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check"
	@poetry check
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@poetry run mypy --config-file=pyproject.toml


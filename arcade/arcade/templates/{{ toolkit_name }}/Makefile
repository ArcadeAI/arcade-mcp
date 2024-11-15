.PHONY: help

help:
	@echo "🛠️ {{ toolkit_name }} Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "📦 Checking if Poetry is installed"
	@if ! command -v poetry &> /dev/null; then \
		echo "📦 Installing Poetry with pip"; \
		pip install poetry; \
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
	rm -rf dist

.PHONY: clean-dist
clean-dist: ## Clean all built distributions
	@echo "🗑️ Cleaning dist directory"
	@rm -rf dist

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

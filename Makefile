

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@cd arcade && poetry install
	@cd arcade && poetry run pre-commit install
	@cd arcade && poetry shell

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@cd arcade && poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@cd arcade && poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@cd arcade && poetry run mypy $(git ls-files '*.py')

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@cd arcade && poetry run pytest -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@cd arcade && poetry build

.PHONY: clean
clean: ## clean build artifacts
	@cd arcade && rm -rf dist

.PHONY: publish
publish: ## publish a release to pypi.
	@echo "🚀 Publishing: Dry run."
	@cd arcade && poetry config pypi-token.pypi $(PYPI_TOKEN)
	@cd arcade && poetry publish --dry-run
	@echo "🚀 Publishing."
	@cd arcade && poetry publish

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@cd arcade && poetry run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@cd arcade && poetry run mkdocs serve -a localhost:8777

.PHONY: docker
docker: ## Build and run the Docker container
	@cd docker && make docker-build
	@cd docker && make docker-run

.PHONY: help
help:
	@echo "🛠️ Arcade AI Dev Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

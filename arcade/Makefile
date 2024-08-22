VENDOR ?= ArcadeAI
PROJECT ?= ArcadeAI
SOURCE ?= https://github.com/ArcadeAI/arcade-ai
LICENSE ?= MIT
DESCRIPTION ?= "Arcade AI for LLM Tool Serving"
REPOSITORY ?= arcadeai/arcade-ai

VERSION ?= dev
COMMIT ?= $(shell git describe --dirty --always --abbrev=15)
BUILD_DATE ?= $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
IMAGE_NAME ?= actor
PORT ?= 8000

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@poetry install
	@poetry run pre-commit install
	@poetry shell

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@poetry run mypy $(git ls-files '*.py')

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@poetry run pytest -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@poetry build

.PHONY: clean
clean: ## clean build artifacts
	@rm -rf dist

.PHONY: publish
publish: ## publish a release to pypi.
	@echo "🚀 Publishing: Dry run."
	@poetry config pypi-token.pypi $(PYPI_TOKEN)
	@poetry publish --dry-run
	@echo "🚀 Publishing."
	@poetry publish

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@poetry run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@poetry run mkdocs serve -a localhost:8777

.PHONY: docker-build
docker-build: ## Build the Docker container
	@echo "🛠️ Building Docker image ($(VERSION)).."
	@echo "- Commit: $(COMMIT)"
	@echo "- Build Date: $(BUILD_DATE)"
	@docker build -f ../docker/Dockerfile ../ -t $(REPOSITORY):$(VERSION) \
	--build-arg PORT=$(PORT) \
	--build-arg VERSION="$(VERSION)" \
	--build-arg COMMIT="$(COMMIT)" \
	--build-arg BUILD_DATE="$(BUILD_DATE)" \
	--label=org.opencontainers.image.vendor="$(VENDOR)" \
	--label=org.opencontainers.image.title="$(PROJECT)" \
	--label=org.opencontainers.image.revision="$(COMMIT)" \
	--label=org.opencontainers.image.version="$(VERSION)" \
	--label=org.opencontainers.image.created="$(BUILD_DATE)" \
	--label=org.opencontainers.image.source="$(SOURCE)" \
	--label=org.opencontainers.image.licenses="$(LICENSE)" \
	--label=org.opencontainers.image.description=$(DESCRIPTION)

.PHONY: docker-run
docker-run: ## Run the Docker container
	@echo "🚀 Running Docker container ($(VERSION)).."
	@docker run -p $(PORT):$(PORT) \
		-e WORK_DIR=/app/docker/ \
		$(REPOSITORY):$(VERSION)

.PHONY: help
help:
	@echo "🛠️ Arcade AI Dev Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

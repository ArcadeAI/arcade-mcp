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
PORT ?= 8002


.PHONY: docker-build
docker-build: ## Build the Docker container
	@echo "🛠️ Building Docker image ($(VERSION)).."
	@echo "- Commit: $(COMMIT)"
	@echo "- Build Date: $(BUILD_DATE)"
	@docker build --build-arg PORT=$(PORT) -t $(REPOSITORY):$(VERSION) . \
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
	@echo "\n🚀 Run the container with the following ..."
	@echo ">>> docker run -d -p $(PORT):$(PORT) $(REPOSITORY):$(VERSION)"

.PHONY: help
help:
	@echo "🛠️ Actor Docker Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

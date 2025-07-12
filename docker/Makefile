VENDOR ?= ArcadeAI
PROJECT ?= ArcadeAI
SOURCE ?= https://github.com/ArcadeAI/arcade-ai
LICENSE ?= MIT
DESCRIPTION ?= "Arcade Worker for LLM Tool Serving"
REPOSITORY ?= arcadeai/worker
ARCH ?= $(shell uname -m)

VERSION ?= 0.1.0.dev0
COMMIT ?= $(shell git describe --dirty --always --abbrev=15)
BUILD_DATE ?= $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
IMAGE_NAME ?= worker
PORT ?= 8002
INSTALL_TOOLKITS ?= true

# If INSTALL_TOOLKITS is true, we are building the worker image with all toolkits
# Otherwise, we are building the worker image with no toolkits
ifeq ($(INSTALL_TOOLKITS), true)
    REPOSITORY := $(REPOSITORY)
else
    REPOSITORY := $(REPOSITORY)-base
endif

VERSION_TAG := $(VERSION)-$(ARCH)

.PHONY: docker-build
docker-build: ## Build the Docker container
	@echo "🛠️ Building Docker image ($(VERSION_TAG)).."
	@echo "- Commit: $(COMMIT)"
	@echo "- Build Date: $(BUILD_DATE)"
	@docker build --build-arg PORT=$(PORT) -f Dockerfile -t $(REPOSITORY):$(VERSION_TAG) \
    --build-arg INSTALL_TOOLKITS=$(INSTALL_TOOLKITS) \
	--build-arg PORT=$(PORT) \
	--build-arg VERSION="$(VERSION)" \
	--build-arg COMMIT="$(COMMIT)" \
	--build-arg BUILD_DATE="$(BUILD_DATE)" \
	--label=org.opencontainers.image.vendor="$(VENDOR)" \
	--label=org.opencontainers.image.title="$(PROJECT)" \
	--label=org.opencontainers.image.revision="$(COMMIT)" \
	--label=org.opencontainers.image.version="$(VERSION_TAG)" \
	--label=org.opencontainers.image.created="$(BUILD_DATE)" \
	--label=org.opencontainers.image.source="$(SOURCE)" \
	--label=org.opencontainers.image.licenses="$(LICENSE)" \
	--label=org.opencontainers.image.description=$(DESCRIPTION) \
     ..

ghcr-manifest: ## Make a manifest file for the image
	@echo "🛠️ Build manifest file for $(REPOSITORY):$(VERSION).."
	@echo "- Commit: $(COMMIT)"
	@echo "- Build Date: $(BUILD_DATE)"
	@export DOCKER_CLI_EXPERIMENTAL=enabled
	@echo "- Creating manifest ghcr.io/$(REPOSITORY):$(VERSION)"
	@docker manifest create ghcr.io/$(REPOSITORY):$(VERSION) \
    --amend ghcr.io/$(REPOSITORY):$(VERSION)-arm64 \
    --amend ghcr.io/$(REPOSITORY):$(VERSION)-amd64
	@echo "- Creating manifest ghcr.io/$(REPOSITORY):latest"
	@docker manifest create ghcr.io/$(REPOSITORY):latest \
    --amend ghcr.io/$(REPOSITORY):$(VERSION)-arm64 \
    --amend ghcr.io/$(REPOSITORY):$(VERSION)-amd64
	@echo "- Inspecting manifest ghcr.io/$(REPOSITORY):$(VERSION)"
	@docker manifest inspect ghcr.io/$(REPOSITORY):$(VERSION)
	@echo "- Inspecting manifest ghcr.io/$(REPOSITORY):latest"
	@docker manifest inspect ghcr.io/$(REPOSITORY):latest
	@echo "- Pushing manifest ghcr.io/$(REPOSITORY):$(VERSION)"
	@docker manifest push ghcr.io/$(REPOSITORY):$(VERSION)
	@echo "- Pushing manifest ghcr.io/$(REPOSITORY):latest"
	@docker manifest push ghcr.io/$(REPOSITORY):latest


.PHONY: docker-run
docker-run: ## Run the Docker container
	@echo "\n🚀 Run the container with the following ..."
	@echo ">>> docker run -d -p $(PORT):$(PORT) $(REPOSITORY):$(VERSION_TAG)"


.PHONY: publish-ghcr
publish-ghcr:
	@echo "🚚 Pushing the Agent image to GHCR.."
	@docker tag $(REPOSITORY):$(VERSION_TAG) ghcr.io/$(REPOSITORY):$(VERSION_TAG)
	@echo "- pushing ghcr.io/$(REPOSITORY):$(VERSION_TAG)"
	@docker push ghcr.io/$(REPOSITORY):$(VERSION_TAG)
	@echo $(VERSION) | grep -q $(RC_PART) || { \
		docker tag $(REPOSITORY):$(VERSION_TAG) ghcr.io/$(REPOSITORY):latest-$(ARCH); \
		echo "- pushing ghcr.io/$(REPOSITORY):latest-$(ARCH)"; \
		docker push ghcr.io/$(REPOSITORY):latest-$(ARCH); \
	}


.PHONY: gh-login
gh-login: ## Login to GHCR
	@echo "🚚 Logging in to GHCR..."
	@if [ -z "$(GHCR_PAT)" ]; then \
		echo "Error: GHCR_PAT environment variable is not set"; \
		exit 1; \
	fi
	@echo $(GHCR_PAT) | docker login ghcr.io -u arcadeai --password-stdin

.PHONY: help
help:
	@echo "🛠️ Worker Docker Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

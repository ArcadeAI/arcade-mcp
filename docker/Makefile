VENDOR ?= ArcadeAI
PROJECT ?= ArcadeAI
SOURCE ?= https://github.com/ArcadeAI/arcade-ai
LICENSE ?= MIT
DESCRIPTION ?= "Arcade AI for LLM Tool Serving"
REPOSITORY ?= arcadeai/arcade-ai
ECR_ENDPOINT ?= 471112909428.dkr.ecr.us-east-1.amazonaws.com

VERSION ?= 0.1.0.dev0
COMMIT ?= $(shell git describe --dirty --always --abbrev=15)
BUILD_DATE ?= $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
IMAGE_NAME ?= worker
PORT ?= 8002


.PHONY: docker-build
docker-build: ## Build the Docker container
	@echo "🛠️ Building Docker image ($(VERSION)).."
	@echo "- Commit: $(COMMIT)"
	@echo "- Build Date: $(BUILD_DATE)"
	@docker build --build-arg PORT=$(PORT) -f Dockerfile -t $(REPOSITORY):$(VERSION) .. \
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


.PHONY: publish-ecr
publish-ecr:
	@echo "🚚 Pushing the Agent image to ECR.."
	@docker tag $(REPOSITORY):$(VERSION) $(ECR_ENDPOINT)/$(REPOSITORY):$(VERSION)
	@echo "- pushing $(ECR_ENDPOINT)/$(REPOSITORY):$(VERSION)"
	@docker push $(ECR_ENDPOINT)/$(REPOSITORY):$(VERSION)
	@echo $(VERSION) | grep -q $(RC_PART) || { \
		docker tag $(REPOSITORY):$(VERSION) $(ECR_ENDPOINT)/$(REPOSITORY):latest; \
		echo "- pushing $(ECR_ENDPOINT)/$(REPOSITORY):latest"; \
		docker push $(ECR_ENDPOINT)/$(REPOSITORY):latest; \
	}


.PHONY: ecr-login
ecr-login: # Login to ECR
	@aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(ECR_ENDPOINT)

.PHONY: help
help:
	@echo "🛠️ Worker Docker Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

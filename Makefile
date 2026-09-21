
.PHONY: install
install: ## Install the uv environment and all packages with dependencies
	@echo "🚀 Creating virtual environment and installing all packages using uv workspace"
	@uv sync --extra all --extra dev
	@uv run pre-commit install
	@echo "✅ All packages and dependencies installed via uv workspace"

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy on libs"
	@failed_libs=""; for lib in libs/arcade*/ ; do \
		echo "🔍 Type checking $$lib"; \
		(cd $$lib && uv run mypy . --exclude tests) || failed_libs="$$failed_libs $$lib"; \
	done; \
	if [ -n "$$failed_libs" ]; then \
		echo "❌ mypy failed in:$$failed_libs"; \
		exit 1; \
	fi

.PHONY: check-libs
check-libs: ## Run code quality tools for each lib package
	@echo "🚀 Running checks on each lib package"
	@for lib in libs/arcade*/ ; do \
		echo "🛠️ Checking lib $$lib"; \
		(cd $$lib && uv run pre-commit run -a || true); \
		(cd $$lib && uv run mypy . || true); \
	done

.PHONY: test
test: install ## Test the code with pytest
	@echo "🚀 Testing libs: Running pytest"
	@uv run pytest -W ignore -v libs/tests --cov=libs --cov-config=pyproject.toml --cov-report=xml

.PHONY: test-libs
test-libs: ## Test each lib package individually
	@echo "🚀 Testing each lib package"
	@for lib in libs/arcade*/ ; do \
		echo "🧪 Testing $$lib"; \
		(cd $$lib && uv run pytest -W ignore -v || true); \
	done

.PHONY: coverage
coverage: ## Generate coverage report
	@echo "coverage report"
	@uv run coverage report
	@echo "Generating coverage report"
	@uv run coverage html

.PHONY: build
build: clean-build ## Build wheel files using uv
	@echo "🚀 Creating wheel files for all lib packages"
	@for lib in libs/arcade*/ ; do \
		if [ -f "$$lib/pyproject.toml" ]; then \
			echo "🛠️ Building $$lib"; \
			(cd $$lib && uv build); \
		fi; \
	done

.PHONY: clean-build
clean-build: ## clean build artifacts
	@echo "🗑️ Cleaning build artifacts"
	@for lib in libs/arcade*/ ; do \
		(cd $$lib && rm -rf dist); \
	done

.PHONY: publish
publish: ## publish a release to pypi.
	@echo "🚀 Publishing all lib packages to PyPI"
	@for lib in libs/arcade*/ ; do \
		if [ -f "$$lib/pyproject.toml" ]; then \
			echo "📦 Publishing $$lib"; \
			(cd $$lib && uv publish --token $(PYPI_TOKEN) || true); \
		fi; \
	done

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docker
docker: ## Build and run the Docker container
	@echo "🚀 Building lib packages..."
	@make full-dist
	@echo "🚀 Building Docker image"
	@cd docker && make docker-build
	@cd docker && make docker-run

.PHONY: publish-ghcr
publish-ghcr: ## Publish to the GHCR
	@cd docker && make publish-ghcr

.PHONY: full-dist
full-dist: clean-dist ## Build all projects and copy wheels to ./dist
	@echo "🛠️ Building a full distribution with lib packages"

	@echo "🛠️ Building all lib packages and copying wheels to ./dist"
	@mkdir -p dist

	@for lib in arcade-core arcade-tdk arcade-serve ; do \
		echo "🛠️ Building libs/$$lib wheel..."; \
		(cd libs/$$lib && uv build); \
	done

	@echo "🛠️ Building arcade-mcp package and copying wheel to ./dist"
	@uv build
	@rm -f dist/*.tar.gz

.PHONY: clean-dist
clean-dist: ## Clean all built distributions
	@echo "🗑️ Cleaning dist directory"
	@rm -rf dist
	@echo "🗑️ Cleaning libs/*/dist directories"
	@for lib in libs/arcade*/ ; do \
		rm -rf "$$lib"/dist; \
	done

.PHONY: setup
setup: ## Run uv environment setup script
	@chmod +x ./uv_setup.sh
	@./uv_setup.sh

.PHONY: lint
lint: check ## Alias for check command

.PHONY: clean
clean: clean-build clean-dist ## Clean all build and distribution artifacts

.PHONY: help
help:
	@echo "🛠️ Arcade Dev Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

.PHONY: shell
shell: ## Open an interactive shell with the virtual environment activated
	@if [ -f ".venv/bin/activate" ]; then \
		. .venv/bin/activate && exec $$SHELL -l; \
	else \
		echo "⚠️  Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

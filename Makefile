
.PHONY: install
install: ## Install the uv environment and all packages with dependencies
	@echo "🚀 Creating virtual environment and installing all packages using uv workspace"
	@uv sync --active --dev --extra all
	@uv run pre-commit install
	@echo "✅ All packages and dependencies installed via uv workspace"

.PHONY: install-toolkits
install-toolkits: ## Install dependencies for all toolkits
	@echo "🚀 Installing dependencies for all toolkits"
	@failed=0; \
	successful=0; \
	for dir in toolkits/*/ ; do \
		if [ -d "$$dir" ] && [ -f "$$dir/pyproject.toml" ]; then \
			echo "📦 Installing dependencies for $$dir"; \
			if (cd $$dir && uv pip install -e ".[dev]"); then \
				successful=$$((successful + 1)); \
			else \
				echo "❌ Failed to install dependencies for $$dir"; \
				failed=$$((failed + 1)); \
			fi; \
		else \
			echo "⚠️  Skipping $$dir (no pyproject.toml found)"; \
		fi; \
	done; \
	echo ""; \
	echo "📊 Installation Summary:"; \
	echo "  ✅ Successful: $$successful toolkits"; \
	echo "  ❌ Failed: $$failed toolkits"; \
	if [ $$failed -gt 0 ]; then \
		echo ""; \
		echo "⚠️  Some toolkit installations failed. Check the output above for details."; \
		exit 1; \
	else \
		echo ""; \
		echo "🎉 All toolkit dependencies installed successfully!"; \
	fi

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy on libs"
	@for lib in libs/arcade*/ ; do \
		echo "🔍 Type checking $$lib"; \
		(cd $$lib && uv run mypy . || true); \
	done

.PHONY: check-libs
check-libs: ## Run code quality tools for each lib package
	@echo "🚀 Running checks on each lib package"
	@for lib in libs/arcade*/ ; do \
		echo "🛠️ Checking lib $$lib"; \
		(cd $$lib && uv run pre-commit run -a || true); \
		(cd $$lib && uv run mypy . || true); \
	done

.PHONY: check-toolkits
check-toolkits: ## Run code quality tools for each toolkit that has a Makefile
	@echo "🚀 Running 'make check' in each toolkit with a Makefile"
	@for dir in toolkits/*/ ; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "🛠️ Checking toolkit $$dir"; \
			(cd "$$dir" && uv run --active pre-commit run -a && uv run --active mypy --config-file=pyproject.toml); \
		else \
			echo "🛠️ Skipping toolkit $$dir (no Makefile found)"; \
		fi; \
	done

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing libs: Running pytest"
	@uv run pytest -W ignore -v --cov=libs/tests --cov-config=pyproject.toml --cov-report=xml

.PHONY: test-libs
test-libs: ## Test each lib package individually
	@echo "🚀 Testing each lib package"
	@for lib in libs/arcade*/ ; do \
		echo "🧪 Testing $$lib"; \
		(cd $$lib && uv run pytest -W ignore -v || true); \
	done

.PHONY: test-toolkits
test-toolkits: ## Iterate over all toolkits and run pytest on each one
	@echo "🚀 Testing code in toolkits: Running pytest"
	@for dir in toolkits/*/ ; do \
		toolkit_name=$$(basename "$$dir"); \
		echo "🧪 Testing $$toolkit_name toolkit"; \
		(cd $$dir && uv run --active pytest -W ignore -v --cov=arcade_$$toolkit_name --cov-report=xml || exit 1); \
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

.PHONY: build-toolkits
build-toolkits: ## Build wheel files for all toolkits
	@echo "🚀 Creating wheel files for all toolkits"
	@failed=0; \
	successful=0; \
	for dir in toolkits/*/ ; do \
		if [ -d "$$dir" ] && [ -f "$$dir/pyproject.toml" ]; then \
			toolkit_name=$$(basename "$$dir"); \
			echo "🛠️ Building toolkit $$toolkit_name"; \
			if (cd $$dir && uv build); then \
				successful=$$((successful + 1)); \
			else \
				echo "❌ Failed to build toolkit $$toolkit_name"; \
				failed=$$((failed + 1)); \
			fi; \
		else \
			echo "⚠️  Skipping $$dir (no pyproject.toml found)"; \
		fi; \
	done; \
	echo ""; \
	echo "📊 Build Summary:"; \
	echo "  ✅ Successful: $$successful toolkits"; \
	echo "  ❌ Failed: $$failed toolkits"; \
	if [ $$failed -gt 0 ]; then \
		echo ""; \
		echo "⚠️  Some toolkit builds failed. Check the output above for details."; \
		exit 1; \
	else \
		echo ""; \
		echo "🎉 All toolkit wheels built successfully!"; \
	fi

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
	@echo "🚀 Building lib packages and toolkit wheels..."
	@make full-dist
	@echo "🚀 Building Docker image"
	@cd docker && make docker-build
	@cd docker && make docker-run

.PHONY: docker-base
docker-base: ## Build and run the Docker container
	@echo "🚀 Building lib packages and toolkit wheels..."
	@make full-dist
	@echo "🚀 Building Docker image"
	@cd docker && INSTALL_TOOLKITS=false make docker-build
	@cd docker && INSTALL_TOOLKITS=false make docker-run

.PHONY: publish-ghcr
publish-ghcr: ## Publish to the GHCR
    # Publish the base image - ghcr.io/arcadeai/worker-base
	@cd docker && INSTALL_TOOLKITS=false make publish-ghcr
    # Publish the image with toolkits - ghcr.io/arcadeai/worker
	@cd docker && INSTALL_TOOLKITS=true make publish-ghcr

.PHONY: full-dist
full-dist: clean-dist ## Build all projects and copy wheels to ./dist
	@echo "🛠️ Building a full distribution with lib packages and toolkits"

	@echo "🛠️ Building all lib packages and copying wheels to ./dist"
	@mkdir -p dist

	@for lib in arcade-core arcade-tdk arcade-serve ; do \
		echo "🛠️ Building libs/$$lib wheel..."; \
		(cd libs/$$lib && uv build); \
	done

	@echo "🛠️ Building arcade-ai package and copying wheel to ./dist"
	@uv build
	@rm -f dist/*.tar.gz

	@echo "🛠️ Building all toolkit packages and copying wheels to ./dist"
	@for dir in toolkits/*/ ; do \
		if [ -d "$$dir" ] && [ -f "$$dir/pyproject.toml" ]; then \
			toolkit_name=$$(basename "$$dir"); \
			echo "🛠️ Building toolkit $$toolkit_name wheel..."; \
			(cd $$dir && uv build); \
			cp $$dir/dist/*.whl dist/; \
		fi; \
	done

.PHONY: clean-dist
clean-dist: ## Clean all built distributions
	@echo "🗑️ Cleaning dist directory"
	@rm -rf dist
	@echo "🗑️ Cleaning libs/*/dist directories"
	@for lib in libs/arcade*/ ; do \
		rm -rf "$$lib"/dist; \
	done
	@echo "🗑️ Cleaning toolkits/*/dist directory"
	@for toolkit_dir in toolkits/*; do \
		if [ -d "$$toolkit_dir" ]; then \
			rm -rf "$$toolkit_dir"/dist; \
		fi; \
	done

.PHONY: setup
setup: install ## Complete development setup (same as install)

.PHONY: lint
lint: check ## Alias for check command

.PHONY: clean
clean: clean-build clean-dist ## Clean all build and distribution artifacts

.PHONY: help
help:
	@echo "🛠️ Arcade Dev Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

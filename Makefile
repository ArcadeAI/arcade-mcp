VERSION ?= "0.1.0.dev0"

.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@cd arcade && poetry install --all-extras
	@cd arcade && poetry run pre-commit install


.PHONY: install-toolkits
install-toolkits: ## Install dependencies for all toolkits
	@echo "🚀 Installing dependencies for all toolkits"
	@for dir in toolkits/*/ ; do \
		echo "📦 Installing dependencies for $$dir"; \
		(cd $$dir && poetry lock && poetry install); \
	done


.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@cd arcade && poetry check --lock
	@echo "🚀 Linting code: Running pre-commit"
	@cd arcade && poetry run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@cd arcade && poetry run mypy $(git ls-files '*.py')


.PHONY: check-toolkits
check-toolkits: ## Run code quality tools for each toolkit that has a Makefile
	@echo "🚀 Running 'make check' in each toolkit with a Makefile"
	@for dir in toolkits/*/ ; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "🛠️ Checking toolkit $$dir"; \
			(cd "$$dir" && make check); \
		else \
			echo "🛠️ Skipping toolkit $$dir (no Makefile found)"; \
		fi; \
	done

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@cd arcade && poetry run pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: test-toolkits
test-toolkits: ## Iterate over all toolkits and run pytest on each one
	@echo "🚀 Testing code in toolkits: Running pytest"
	@for dir in toolkits/*/ ; do \
		(cd $$dir && poetry run pytest -W ignore -v --cov --cov-config=pyproject.toml --cov-report=xml || exit 1); \
	done

.PHONY: coverage
coverage: ## Generate coverage report
	@echo "coverage report"
	@cd arcade && coverage report
	@echo "Generating coverage report"
	@cd arcade && coverage html

.PHONY: set-version
set-version: ## Set the version in the pyproject.toml file
	@echo "🚀 Setting version in pyproject.toml"
	@cd arcade && poetry version $(VERSION)

.PHONY: unset-version
unset-version: ## Set the version in the pyproject.toml file
	@echo "🚀 Setting version in pyproject.toml"
	@cd arcade && poetry version 0.1.0

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@cd arcade && poetry build

.PHONY: clean-build
clean-build: ## clean build artifacts
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

.PHONY: docker
docker: ## Build and run the Docker container
	@echo "🚀 Building arcade and toolkit wheels..."
	@make full-dist
	@echo "Writing extras [fastapi, evals] to requirements.txt"
	@cd arcade && poetry export --extras "fastapi evals" --output ../dist/requirements.txt
	@echo "🚀 Building Docker image"
	@cd docker && make docker-build
	@cd docker && make docker-run

.PHONY: publish-ecr
publish-ecr: ## Publish to the ECR
	@cd docker && make publish-ecr

.PHONY: full-dist
full-dist: clean-dist ## Build all projects and copy wheels to ./dist
	@echo " Building a full distribution with toolkits"

	@echo "Setting version to $(VERSION)"
	@make set-version

	# @echo "🛠️ Building all projects and copying wheels to ./dist"
	@mkdir -p dist

	# Build the main arcade project
	@echo "🛠️ Building arcade project wheel..."
	@cd arcade && poetry build

	# Copy the main arcade project wheel to the dist directory
	@cp arcade/dist/*.whl dist/

	@echo "Reset version to default (0.1.0)"
	@make unset-version

	@echo "🛠️ Building all projects and copying wheels to ./dist"
	# Build and copy wheels for each toolkit
	# @for toolkit_dir in toolkits/*; do \
	# 	if [ -d "$$toolkit_dir" ]; then \
	# 		toolkit_name=$$(basename "$$toolkit_dir"); \
	# 		echo "Building $$toolkit_name project..."; \
    #         poetry build; \
	# 		cp dist/*.whl ../../dist/toolkits; \
	# 		cd -; \
	# 	fi; \
	# done

	@echo "✅ All toolkits built and wheels copied to ./dist"

.PHONY: clean-dist
clean-dist: ## Clean all built distributions
	@echo "🗑️ Cleaning dist directory"
	@rm -rf dist
	@echo "🗑️ Cleaning arcade/dist directory"
	@rm -rf arcade/dist
	@echo "🗑️ Cleaning toolkits/*/dist directory"
	@for toolkit_dir in toolkits/*; do \
		if [ -d "$$toolkit_dir" ]; then \
			rm -rf "$$toolkit_dir"/dist; \
		fi; \
	done

.PHONY: help
help:
	@echo "🛠️ Arcade AI Dev Commands:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'



.DEFAULT_GOAL := help

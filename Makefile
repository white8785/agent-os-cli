# AgentOS CLI Makefile

.PHONY: help install install-dev test lint format format-check typecheck clean build check pre-ci security deps dev init

help: ## Display this help message
	@echo "AgentOS CLI Development Commands"
	@echo "================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

install: ## Install project dependencies with uv
	uv sync

install-dev: ## Install all dependencies including dev tools
	uv sync --all-extras
	uv pip install -e .

test: ## Run test suite with coverage
	uv run --extra test pytest tests/ -v --cov=agentos --cov-report=term-missing --cov-report=html

lint: ## Run all linting checks
	@echo "Running ruff..."
	uv run --extra lint ruff check src/ tests/
	@echo "Running mypy..."
	uv run --extra lint mypy src/

format: ## Format code with black and ruff
	uv run --extra lint black src/ tests/
	uv run --extra lint ruff check --fix src/ tests/

format-check: ## Check code formatting without modifying
	uv run --extra lint black --check src/ tests/
	uv run --extra lint ruff check src/ tests/

typecheck: ## Run mypy type checking
	uv run --extra lint mypy src/

clean: ## Clean build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	uv build

check: format-check lint typecheck test ## Run all checks (format, lint, typecheck, test)

pre-ci: ## Run all pre-CI checks (format, lint, typecheck, security, test)
	@echo "========================================="
	@echo "Running Pre-CI Checks for AgentOS CLI"
	@echo "========================================="
	@echo ""
	@echo "Step 1/5: Checking code formatting..."
	@echo "-----------------------------------------"
	@$(MAKE) format-check
	@echo "✅ Formatting check passed!"
	@echo ""
	@echo "Step 2/5: Running linters..."
	@echo "-----------------------------------------"
	@$(MAKE) lint
	@echo "✅ Linting passed!"
	@echo ""
	@echo "Step 3/5: Running type checks..."
	@echo "-----------------------------------------"
	@$(MAKE) typecheck
	@echo "✅ Type checking passed!"
	@echo ""
	@echo "Step 4/5: Running security checks..."
	@echo "-----------------------------------------"
	@$(MAKE) security
	@echo "✅ Security checks passed!"
	@echo ""
	@echo "Step 5/5: Running test suite..."
	@echo "-----------------------------------------"
	@$(MAKE) test
	@echo ""
	@echo "========================================="
	@echo "✅ All Pre-CI Checks Passed!"
	@echo "========================================="

security: ## Run security checks
	@echo "Running ruff security checks..."
	uv run --extra lint ruff check --select S src/ tests/

deps: ## Show project dependencies
	uv tree

dev: ## Install package in development mode
	uv pip install -e .
	@echo ""
	@echo "✅ Development installation complete!"
	@echo ""
	@echo "To use the CLI, run:"
	@echo "  uv run agentos --help"

init: ## Initialize project for first time
	@echo "Initializing AgentOS CLI development environment..."
	@$(MAKE) install-dev
	@$(MAKE) check
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "Run 'make help' to see available commands"
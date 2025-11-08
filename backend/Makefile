.PHONY: test test-unit test-integration test-cov test-fast lint format clean help

# Default Python and pytest
PYTHON := python3
PYTEST := pytest

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

test:  ## Run all tests with coverage
	$(PYTEST)

test-unit:  ## Run unit tests only
	$(PYTEST) -m unit

test-integration:  ## Run integration tests only
	$(PYTEST) -m integration

test-fast:  ## Run tests without coverage (faster)
	$(PYTEST) --no-cov

test-cov:  ## Run tests and open coverage report
	$(PYTEST)
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html

test-imports:  ## Run import tests only (quick sanity check)
	$(PYTEST) tests/test_imports.py -v

test-watch:  ## Run tests in watch mode
	$(PYTEST) -f

lint:  ## Run linters
	ruff check app/
	mypy app/

format:  ## Format code
	black app/ tests/
	ruff check --fix app/

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete

check:  ## Run all quality checks
	@echo "Running formatters..."
	@make format
	@echo "\nRunning linters..."
	@make lint
	@echo "\nRunning tests..."
	@make test

.DEFAULT_GOAL := help

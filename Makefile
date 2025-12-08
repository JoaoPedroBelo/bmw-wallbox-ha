# Makefile for BMW Wallbox Home Assistant Integration
# Quick commands for development

.PHONY: help install lint format test coverage clean

help:
	@echo "BMW Wallbox Development Commands:"
	@echo ""
	@echo "  make install      Install development dependencies"
	@echo "  make lint         Run all linters (ruff, mypy)"
	@echo "  make format       Auto-format code with ruff"
	@echo "  make test         Run all tests"
	@echo "  make coverage     Run tests with coverage report"
	@echo "  make clean        Remove generated files"
	@echo "  make pre-commit   Install pre-commit hooks"
	@echo "  make check        Run all checks (lint + test)"
	@echo ""

install:
	pip install -r requirements-dev.txt

lint:
	@echo "Running Ruff linter..."
	ruff check custom_components/ tests/
	@echo ""
	@echo "Checking code formatting..."
	ruff format custom_components/ tests/ --check
	@echo ""
	@echo "Running MyPy type checker..."
	mypy custom_components/bmw_wallbox --show-error-codes --pretty

format:
	@echo "Formatting code with Ruff..."
	ruff check custom_components/ tests/ --fix
	ruff format custom_components/ tests/
	@echo "✓ Code formatted!"

test:
	@echo "Running tests..."
	pytest tests/ -v

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=custom_components.bmw_wallbox --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned!"

pre-commit:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Pre-commit hooks installed!"
	@echo "Run 'pre-commit run --all-files' to test"

check: lint test
	@echo ""
	@echo "✓ All checks passed!"

# Quick fix common issues
fix:
	@echo "Auto-fixing common issues..."
	ruff check custom_components/ tests/ --fix
	ruff format custom_components/ tests/
	@echo "✓ Fixed!"

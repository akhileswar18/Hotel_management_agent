# HMS Makefile - Common Development Commands

.PHONY: help venv install test lint format clean run migrate

help:
	@echo "Hotel Management System - Phase 1 (MVP)"
	@echo "========================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make venv      - Create virtual environment"
	@echo "  make install   - Install dependencies"
	@echo "  make test      - Run all tests with coverage"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-int  - Run integration tests only"
	@echo "  make lint      - Run linting (flake8, black, mypy)"
	@echo "  make format    - Format code (black)"
	@echo "  make migrate   - Run database migrations"
	@echo "  make run       - Run API server"
	@echo "  make clean     - Clean build artifacts"
	@echo ""

venv:
	python -m venv venv
	@echo "✓ Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  # Linux/macOS"
	@echo "  venv\\Scripts\\activate   # Windows"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

install-prod:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=html
	@echo "✓ Coverage report: htmlcov/index.html"

test-unit:
	pytest tests/unit/ -v --cov=src

test-int:
	pytest tests/integration/ -v

test-smoke:
	pytest tests/smoke/ -v

lint:
	@echo "Running black..."
	black src/ tests/ --check
	@echo "Running flake8..."
	flake8 src/ tests/
	@echo "Running mypy..."
	mypy src/ --strict
	@echo "✓ All linting passed"

format:
	black src/ tests/
	@echo "✓ Code formatted"

migrate:
	python -m migrations.runner apply
	@echo "✓ Migrations applied"

migrate-status:
	python -m migrations.runner status

run:
	python -m src

run-prod:
	python -m src

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	@echo "✓ Cleaned"

.DEFAULT_GOAL := help

# Backend (FastAPI) Makefile
.PHONY: help install dev test lint format clean build

# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

PYTHON := python3
PIP := $(PYTHON) -m pip
PORT ?= 8001

help:
	@echo -e "$(BLUE)Agentic AI - Backend (FastAPI)$(RESET)"
	@echo ""
	@echo "Commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make install-dev - Install with dev dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean build artifacts"
	@echo ""

# Installation
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

# Development
dev:
	@echo -e "$(BLUE)Starting backend on port $(PORT)...$(RESET)"
	uvicorn src.api.app:create_app --factory --reload --port $(PORT) --host 0.0.0.0

dev-debug:
	@echo -e "$(BLUE)Starting backend with debug logging...$(RESET)"
	ENVIRONMENT=development DEBUG=true uvicorn src.api.app:create_app --factory --reload --port $(PORT) --host 0.0.0.0 --log-level debug

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	pytest-watch -- -v

# Linting & Formatting
lint:
	ruff check src tests

lint-fix:
	ruff check src tests --fix

format:
	ruff format src tests

type-check:
	mypy src

# Code Quality (all checks)
check: lint type-check test
	@echo -e "$(GREEN)All checks passed!$(RESET)"

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo -e "$(GREEN)Cleaned!$(RESET)"

# Build
build:
	$(PYTHON) -m build

# Agentic AI Platform - Root Makefile
.PHONY: help setup dev clean test lint format ollama-status ollama-start ollama-stop ollama-pull ollama-test

SHELL := /bin/bash

# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# Ollama models
export OLLAMA_MODEL ?= qwen2.5:32b
export OLLAMA_EMBEDDING_MODEL ?= nomic-embed-text

help:
	@echo -e "$(BLUE)Agentic AI Platform$(RESET)"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make setup           - Install all dependencies"
	@echo "  make dev             - Start all development servers"
	@echo "  make dev-backend     - Start backend only (port 8001)"
	@echo "  make dev-frontend    - Start frontend only (port 3000)"
	@echo ""
	@echo "Ollama Commands:"
	@echo "  make ollama-status   - Check Ollama status and models"
	@echo "  make ollama-start    - Start Ollama server"
	@echo "  make ollama-stop     - Stop Ollama server"
	@echo "  make ollama-pull     - Pull required models"
	@echo "  make ollama-test     - Test Ollama connection"
	@echo ""
	@echo "Blueprint Commands:"
	@echo "  make blueprint-init NAME=<name>   - Create new blueprint"
	@echo "  make blueprint-deploy NAME=<name> - Deploy blueprint infra"
	@echo "  make blueprint-destroy NAME=<name> - Destroy blueprint infra"
	@echo ""
	@echo "LocalStack Commands:"
	@echo "  make localstack-check           - Check all LocalStack resources"
	@echo "  make localstack-check-dynamodb  - Check DynamoDB tables"
	@echo "  make localstack-check-s3        - Check S3 buckets"
	@echo "  make localstack-check-k8s       - Check Kubernetes resources"
	@echo "  make localstack-health          - Check LocalStack health"
	@echo ""
	@echo "Quality & Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"
	@echo "  make check           - Run all checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           - Clean build artifacts"
	@echo "  make clean-all       - Clean everything including node_modules"
	@echo ""

# =============================================================================
# Setup
# =============================================================================
setup: setup-ollama setup-venv setup-python setup-node
	@echo -e "$(GREEN)Setup complete!$(RESET)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. make ollama-pull  (download models)"
	@echo "  2. make dev          (start servers)"

setup-ollama:
	@echo -e "$(BLUE)Checking Ollama...$(RESET)"
	@./scripts/ollama.sh status || echo -e "$(YELLOW)Run 'make ollama-start' to start Ollama$(RESET)"

setup-venv:
	@echo -e "$(BLUE)Setting up Python virtual environment...$(RESET)"
	@command -v python3 >/dev/null 2>&1 || { echo -e "$(YELLOW)Error: python3 not found. Please install Python 3.11+$(RESET)"; exit 1; }
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
		echo -e "$(GREEN)✓ Virtual environment created at ./venv$(RESET)"; \
	else \
		echo -e "$(GREEN)✓ Virtual environment already exists$(RESET)"; \
	fi

setup-python:
	@echo -e "$(BLUE)Installing Python dependencies...$(RESET)"
	@if [ -d "venv" ]; then \
		. venv/bin/activate && cd packages/core && pip install -e ".[dev]"; \
	else \
		echo -e "$(YELLOW)Error: Virtual environment not found. Run 'make setup-venv' first$(RESET)"; \
		exit 1; \
	fi

setup-node:
	@echo -e "$(BLUE)Setting up Node.js environment...$(RESET)"
	@if ! command -v node >/dev/null 2>&1; then \
		echo -e "$(YELLOW)Error: Node.js not found.$(RESET)"; \
		echo "Install with: brew install node"; \
		exit 1; \
	fi
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo -e "$(YELLOW)pnpm not found. Installing via npm...$(RESET)"; \
		npm install -g pnpm || { \
			echo -e "$(YELLOW)Failed to install pnpm globally.$(RESET)"; \
			echo "Alternative: brew install pnpm"; \
			exit 1; \
		}; \
	fi
	pnpm install

# =============================================================================
# Ollama Commands
# =============================================================================
ollama-status:
	@./scripts/ollama.sh status

ollama-start:
	@./scripts/ollama.sh start

ollama-stop:
	@./scripts/ollama.sh stop

ollama-pull:
	@./scripts/ollama.sh pull

ollama-test:
	@./scripts/ollama.sh test

ollama-models:
	@./scripts/ollama.sh models

ollama-logs:
	@./scripts/ollama.sh logs

# =============================================================================
# Development
# =============================================================================
dev:
	@echo -e "$(BLUE)Starting development servers...$(RESET)"
	@echo "Backend:  http://localhost:8001"
	@echo "Frontend: http://localhost:3000"
	@echo "API Docs: http://localhost:8001/docs"
	@echo ""
	@echo -e "$(YELLOW)Press Ctrl+C to stop all servers$(RESET)"
	@if [ ! -d "venv" ]; then \
		echo -e "$(YELLOW)Virtual environment not found. Run 'make setup' first$(RESET)"; \
		exit 1; \
	fi
	@trap 'kill 0' INT; \
	(. venv/bin/activate && cd packages/core && make dev) & \
	(cd packages/ui && make dev) & \
	wait

dev-backend:
	@if [ ! -d "venv" ]; then \
		echo -e "$(YELLOW)Virtual environment not found. Run 'make setup' first$(RESET)"; \
		exit 1; \
	fi
	. venv/bin/activate && cd packages/core && make dev

dev-frontend:
	cd packages/ui && make dev

# =============================================================================
# Testing
# =============================================================================
test:
	@if [ ! -d "venv" ]; then \
		echo -e "$(YELLOW)Virtual environment not found. Run 'make setup' first$(RESET)"; \
		exit 1; \
	fi
	. venv/bin/activate && cd packages/core && make test

test-cov:
	@if [ ! -d "venv" ]; then \
		echo -e "$(YELLOW)Virtual environment not found. Run 'make setup' first$(RESET)"; \
		exit 1; \
	fi
	. venv/bin/activate && cd packages/core && make test-cov

# =============================================================================
# Linting & Formatting
# =============================================================================
lint:
	@if [ -d "venv" ]; then \
		. venv/bin/activate && cd packages/core && make lint; \
	fi
	cd packages/ui && make lint

format:
	@if [ -d "venv" ]; then \
		. venv/bin/activate && cd packages/core && make format; \
	fi
	cd packages/ui && make format

check:
	@if [ -d "venv" ]; then \
		. venv/bin/activate && cd packages/core && make check; \
	fi
	cd packages/ui && make check
	@echo -e "$(GREEN)All checks passed!$(RESET)"

# =============================================================================
# Clean
# =============================================================================
clean:
	cd packages/core && make clean
	cd packages/ui && make clean-cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo -e "$(GREEN)Cleaned!$(RESET)"

clean-all: clean
	cd packages/ui && make clean
	rm -rf node_modules
	@echo -e "$(GREEN)Deep clean complete!$(RESET)"

# =============================================================================
# Blueprint Management
# =============================================================================
blueprint-init:
	@if [ -z "$(NAME)" ]; then \
		echo -e "$(YELLOW)Usage: make blueprint-init NAME=<name>$(RESET)"; \
		exit 1; \
	fi
	@echo -e "$(BLUE)Creating blueprint: $(NAME)$(RESET)"
	@mkdir -p blueprints/$(NAME)/{agents,terraform/config/example,terraform/config/local,knowledge,custom}
	@cp blueprints/devassist/terraform/Makefile blueprints/$(NAME)/terraform/
	@cp blueprints/devassist/terraform/variables.tf blueprints/$(NAME)/terraform/
	@sed -i '' 's/devassist/$(NAME)/g' blueprints/$(NAME)/terraform/variables.tf 2>/dev/null || \
		sed -i 's/devassist/$(NAME)/g' blueprints/$(NAME)/terraform/variables.tf
	@echo "name: $(NAME)" > blueprints/$(NAME)/config.yaml
	@echo "slug: $(NAME)" >> blueprints/$(NAME)/config.yaml
	@echo "description: $(NAME) blueprint" >> blueprints/$(NAME)/config.yaml
	@echo -e "$(GREEN)Blueprint $(NAME) created at blueprints/$(NAME)/$(RESET)"

blueprint-deploy:
	@if [ -z "$(NAME)" ]; then \
		echo -e "$(YELLOW)Usage: make blueprint-deploy NAME=<name>$(RESET)"; \
		exit 1; \
	fi
	cd blueprints/$(NAME)/terraform && make init && make apply

blueprint-destroy:
	@if [ -z "$(NAME)" ]; then \
		echo -e "$(YELLOW)Usage: make blueprint-destroy NAME=<name>$(RESET)"; \
		exit 1; \
	fi
	cd blueprints/$(NAME)/terraform && make destroy

# =============================================================================
# LocalStack Management
# =============================================================================
localstack-check:
	@echo -e "$(BLUE)Checking LocalStack resources...$(RESET)"
	@./scripts/check-localstack.sh all

localstack-check-dynamodb:
	@./scripts/check-localstack.sh dynamodb

localstack-check-s3:
	@./scripts/check-localstack.sh s3

localstack-check-k8s:
	@./scripts/check-localstack.sh kubernetes

localstack-health:
	@echo -e "$(BLUE)Checking LocalStack health...$(RESET)"
	@curl -s http://localstack.local/_localstack/health 2>/dev/null | jq . || echo "Failed to reach LocalStack"

blueprint-list:
	@echo -e "$(BLUE)Available blueprints:$(RESET)"
	@ls -d blueprints/*/ 2>/dev/null | xargs -I {} basename {} || echo "No blueprints found"

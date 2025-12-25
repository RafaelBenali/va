# =============================================================================
# TNSE - Telegram News Search Engine
# Makefile for Common Operations
# =============================================================================

.PHONY: help install install-dev setup clean \
        lint format type-check test test-cov \
        docker-up docker-down docker-logs docker-build docker-clean \
        db-migrate db-upgrade db-downgrade \
        run run-dev celery-worker celery-beat

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
PYTEST := pytest
DOCKER_COMPOSE := docker compose
VENV_DIR := venv

# Colors for terminal output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "$(BLUE)TNSE - Telegram News Search Engine$(RESET)"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Installation and Setup
# =============================================================================

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install all dependencies (including dev)
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

setup: ## Complete project setup (venv, deps, env file, pre-commit)
	@echo "$(BLUE)Setting up TNSE development environment...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(RESET)"; \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@echo "$(YELLOW)Installing dependencies...$(RESET)"
	. $(VENV_DIR)/bin/activate && $(PIP) install -r requirements-dev.txt
	. $(VENV_DIR)/bin/activate && $(PIP) install -e .
	@if [ ! -f ".env" ]; then \
		echo "$(YELLOW)Creating .env from template...$(RESET)"; \
		cp .env.example .env; \
	fi
	@echo "$(YELLOW)Setting up pre-commit hooks...$(RESET)"
	. $(VENV_DIR)/bin/activate && pre-commit install || true
	@echo "$(GREEN)Setup complete!$(RESET)"
	@echo "$(YELLOW)Activate the virtual environment with: source $(VENV_DIR)/bin/activate$(RESET)"

clean: ## Remove build artifacts, caches, and virtual environment
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	rm -rf $(VENV_DIR)
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(RESET)"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run all linters (ruff, black check, isort check)
	@echo "$(BLUE)Running linters...$(RESET)"
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/
	@echo "$(GREEN)Linting passed!$(RESET)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(RESET)"
	black src/ tests/
	isort src/ tests/
	ruff check --fix src/ tests/
	@echo "$(GREEN)Formatting complete!$(RESET)"

type-check: ## Run mypy type checker
	@echo "$(BLUE)Running type checker...$(RESET)"
	mypy src/
	@echo "$(GREEN)Type checking passed!$(RESET)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	$(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	$(PYTEST) tests/ -v --cov=src/tnse --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)Coverage report generated in htmlcov/$(RESET)"

test-unit: ## Run only unit tests
	@echo "$(BLUE)Running unit tests...$(RESET)"
	$(PYTEST) tests/unit/ -v

test-integration: ## Run only integration tests
	@echo "$(BLUE)Running integration tests...$(RESET)"
	$(PYTEST) tests/integration/ -v

# =============================================================================
# Docker Operations
# =============================================================================

docker-up: ## Start all Docker services (db and redis only by default)
	@echo "$(BLUE)Starting Docker services...$(RESET)"
	$(DOCKER_COMPOSE) up -d postgres redis
	@echo "$(GREEN)Services started!$(RESET)"
	@echo "$(YELLOW)PostgreSQL: localhost:5432$(RESET)"
	@echo "$(YELLOW)Redis: localhost:6379$(RESET)"

docker-up-all: ## Start all Docker services including app and workers
	@echo "$(BLUE)Starting all Docker services...$(RESET)"
	$(DOCKER_COMPOSE) --profile app --profile worker up -d
	@echo "$(GREEN)All services started!$(RESET)"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(RESET)"
	$(DOCKER_COMPOSE) --profile app --profile worker down
	@echo "$(GREEN)Services stopped!$(RESET)"

docker-logs: ## View Docker service logs
	$(DOCKER_COMPOSE) logs -f

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)Build complete!$(RESET)"

docker-clean: ## Remove Docker volumes and clean up
	@echo "$(RED)WARNING: This will delete all Docker volumes!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && \
		$(DOCKER_COMPOSE) --profile app --profile worker down -v --remove-orphans || \
		echo "$(YELLOW)Cancelled.$(RESET)"

docker-ps: ## Show running Docker containers
	$(DOCKER_COMPOSE) ps

# =============================================================================
# Database Operations
# =============================================================================

db-migrate: ## Generate a new migration
	@echo "$(BLUE)Creating new migration...$(RESET)"
	@read -p "Migration message: " msg && \
		alembic revision --autogenerate -m "$$msg"
	@echo "$(GREEN)Migration created!$(RESET)"

db-upgrade: ## Apply all pending migrations
	@echo "$(BLUE)Applying database migrations...$(RESET)"
	alembic upgrade head
	@echo "$(GREEN)Migrations applied!$(RESET)"

db-downgrade: ## Revert last migration
	@echo "$(BLUE)Reverting last migration...$(RESET)"
	alembic downgrade -1
	@echo "$(YELLOW)Migration reverted!$(RESET)"

db-history: ## Show migration history
	alembic history

# =============================================================================
# Application Running
# =============================================================================

run: ## Run the application (production mode)
	@echo "$(BLUE)Starting TNSE application...$(RESET)"
	uvicorn src.tnse.main:app --host 0.0.0.0 --port 8000

run-dev: ## Run the application in development mode with auto-reload
	@echo "$(BLUE)Starting TNSE application (development mode)...$(RESET)"
	uvicorn src.tnse.main:app --host 0.0.0.0 --port 8000 --reload

celery-worker: ## Start Celery worker
	@echo "$(BLUE)Starting Celery worker...$(RESET)"
	celery -A src.tnse.core.celery_app worker --loglevel=info

celery-beat: ## Start Celery beat scheduler
	@echo "$(BLUE)Starting Celery beat scheduler...$(RESET)"
	celery -A src.tnse.core.celery_app beat --loglevel=info

# =============================================================================
# Quick Start
# =============================================================================

quick-start: docker-up install-dev ## Quick start: Start docker services and install dependencies
	@echo "$(GREEN)Quick start complete!$(RESET)"
	@echo "$(YELLOW)Run 'make run-dev' to start the application$(RESET)"

# =============================================================================
# CI/CD Helpers
# =============================================================================

ci: lint type-check test ## Run all CI checks (lint, type-check, test)
	@echo "$(GREEN)All CI checks passed!$(RESET)"

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TNSE - Telegram News Search Engine**

A news aggregation and search engine for public Telegram channels. The Telegram bot is the primary user interface - no web frontend needed.

### Key Features
- Monitor public Telegram channels for news content
- Keyword and semantic search with engagement-based ranking
- Metrics-only mode (no LLM required) for cost-effective operation
- Export search results to CSV/JSON

### Technology Stack
- **Backend**: Python 3.10+ with FastAPI
- **Database**: PostgreSQL 14+
- **Cache/Queue**: Redis
- **Task Queue**: Celery with Redis
- **Containerization**: Docker, Docker Compose

## Build and Development Commands

### Quick Start
```bash
# Complete setup (creates venv, installs deps, copies .env)
make setup

# Or manual steps:
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements-dev.txt
pip install -e .
cp .env.example .env
```

### Docker Services
```bash
make docker-up       # Start PostgreSQL and Redis
make docker-down     # Stop all services
make docker-logs     # View service logs
make docker-ps       # Show running containers
```

### Development
```bash
make run-dev         # Run app with auto-reload
make test            # Run tests
make test-cov        # Run tests with coverage
make lint            # Run linters
make format          # Format code
make type-check      # Run mypy
make ci              # Run all CI checks
```

### Database
```bash
make db-upgrade      # Apply migrations
make db-migrate      # Create new migration
make db-downgrade    # Revert last migration
```

## Architecture

```
src/tnse/
├── __init__.py          # Package root
├── main.py              # FastAPI application
└── core/
    ├── __init__.py
    ├── config.py        # Configuration management
    └── logging.py       # Structured logging

tests/
├── conftest.py          # Test fixtures
├── unit/                # Unit tests
└── integration/         # Integration tests
```

## Coding Standards

### General
- Use Python 3.10+ features
- Follow PEP 8 style guide (enforced by ruff, black, isort)
- Type hints required for all functions
- Docstrings required for public functions and classes

### Variable Naming
- Never use single-letter variable names
- Use descriptive names that convey meaning
- Use snake_case for variables and functions
- Use PascalCase for classes

### Database
- Prefer raw SQL over SQLAlchemy ORM for queries
- Use SQLAlchemy for model definitions only
- Always use parameterized queries

### Testing
- Write tests before implementation (TDD)
- Prefer integration tests over heavily mocked unit tests
- Only mock external dependencies (APIs, databases)
- Each test should test ONE specific behavior

### Logging
- Use structured logging (JSON format)
- Include relevant context in log entries
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Environment Variables

See `.env.example` for all configuration options. Key variables:

```bash
# Application
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tnse
POSTGRES_USER=tnse_user
POSTGRES_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram (required for bot functionality)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

## Git Workflow

- Use conventional commit messages: `type: description`
- Types: `test`, `feat`, `fix`, `refactor`, `docs`, `chore`
- Never commit `.env` files (use `.env.example` as template)
- Run `make ci` before committing

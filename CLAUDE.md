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
- **Backend**: Python 3.12+ with FastAPI
- **Database**: PostgreSQL 14+
- **Cache/Queue**: Redis 6+
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
- Use Python 3.12+ features
- Follow PEP 8 style guide (enforced by ruff, black, isort)
- Type hints required for all functions
- Docstrings required for public functions and classes

### Modern Python Patterns (3.12+)

This project uses modern Python syntax introduced in Python 3.10-3.12:

**Union Types (PEP 604):**
- Use `X | None` instead of `Optional[X]`
- Example: `def get_user(user_id: int) -> User | None`

**TypeAlias (PEP 613):**
- Use explicit `TypeAlias` annotation for type definitions
- Example: `HandlerFunc: TypeAlias = Callable[[Update, Context], Coroutine[Any, Any, None]]`

**Match/Case Pattern Matching (PEP 634):**
- Use match/case for enum-based dispatch and structural pattern matching
- Example:
  ```python
  match sort_mode:
      case SortMode.VIEWS:
          results.sort(key=lambda r: r.view_count)
      case SortMode.COMBINED:
          results.sort(key=lambda r: r.combined_score)
  ```

**Self Type (PEP 673):**
- Use `Self` for methods returning the instance type
- Example: `def __aenter__(self) -> Self`

**Collections.abc Imports:**
- Import abstract base classes from `collections.abc`
- Example: `from collections.abc import Callable, Coroutine`

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

## LLM Integration Patterns (Phase 5)

The project includes LLM-based post enrichment for semantic search capabilities ("RAG Without Vectors").

### Module Structure

```
src/tnse/llm/
├── __init__.py          # Module exports
├── base.py              # LLMProvider interface, CompletionResult dataclass
├── groq_client.py       # GroqClient implementation with rate limiting
├── enrichment_service.py # EnrichmentService for post metadata extraction
└── tasks.py             # Celery tasks for async enrichment
```

### Usage Patterns

**Basic LLM Completion:**
```python
from src.tnse.llm import GroqClient

async with GroqClient(api_key="your-key") as client:
    result = await client.complete("Your prompt here")
    print(result.content)
```

**JSON Mode (Structured Output):**
```python
result = await client.complete_json("Return JSON with keys: name, age")
print(result.parsed_json)  # Automatically parsed dict
```

**Post Enrichment:**
```python
from src.tnse.llm import EnrichmentService, GroqClient

client = GroqClient(api_key="your-key")
service = EnrichmentService(llm_client=client)
result = await service.enrich_post(post_id=123, text="Post content...")
# result contains: explicit_keywords, implicit_keywords, category, sentiment, entities
```

**Celery Tasks:**
```python
from src.tnse.llm import tasks

# Enrich single post asynchronously
tasks.enrich_post.delay(post_id=123)

# Batch enrich new posts
tasks.enrich_new_posts.delay(limit=100)

# Enrich posts from specific channel
tasks.enrich_channel_posts.delay(channel_id="uuid", limit=50)
```

### Key Concepts

1. **Explicit Keywords:** Words/phrases directly present in the text
2. **Implicit Keywords:** Related concepts NOT in the text (key innovation for RAG-like retrieval)
3. **Rate Limiting:** Built into GroqClient (default 30 RPM for free tier)
4. **Cost Tracking:** All LLM calls logged to `llm_usage_logs` table

### Prompt Template Guidelines

When creating new prompts:
- Use JSON mode (`complete_json()`) for structured extraction
- Keep temperature low (0.1) for consistent extraction
- Include explicit instructions for JSON structure
- Handle edge cases (empty text, media-only posts)

### Error Handling

```python
from src.tnse.llm import (
    GroqAuthenticationError,  # API key issues
    GroqRateLimitError,       # Rate limit exceeded
    GroqTimeoutError,         # Request timeout
    JSONParseError,           # Invalid JSON response
)

try:
    result = await client.complete_json(prompt)
except GroqRateLimitError:
    # Handle rate limit - Celery tasks retry automatically
except JSONParseError:
    # Handle malformed JSON response
```

## Git Workflow

- Use conventional commit messages: `type: description`
- Types: `test`, `feat`, `fix`, `refactor`, `docs`, `chore`
- Never commit `.env` files (use `.env.example` as template)
- Run `make ci` before committing

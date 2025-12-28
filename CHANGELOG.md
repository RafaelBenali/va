# Changelog

All notable changes to the Telegram News Search Engine (TNSE) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-28

### Phase 6: Codebase Modernization Audit

This release represents a comprehensive modernization of the TNSE codebase, updating all dependencies to December 2025 stable versions and adopting modern Python patterns.

### Breaking Changes

- **Python Version Requirement**: Minimum Python version raised from 3.10 to **3.12**
  - Python 3.12 and 3.13 are now supported
  - Python 3.10 and 3.11 are no longer supported
  - Migration: Update your Python installation to 3.12+

### Changed

#### Dependency Updates (WS-6.1)

All dependencies updated to December 2025 stable versions:

| Package | Previous | New |
|---------|----------|-----|
| fastapi | 0.104.0 | 0.115.0+ |
| uvicorn | 0.24.0 | 0.32.0+ |
| pydantic | 2.5.0 | 2.10.0+ |
| pydantic-settings | 2.1.0 | 2.6.0+ |
| structlog | 23.2.0 | 24.4.0+ |
| sqlalchemy | 2.0.23 | 2.0.35+ |
| alembic | 1.13.0 | 1.14.0+ |
| redis | 5.0.0 | 5.2.0+ |
| celery | 5.3.0 | 5.4.0+ |
| python-telegram-bot | 20.7 | 21.0+ |
| pytest | 7.4.0 | 8.0.0+ |
| ruff | 0.1.6 | 0.8.0+ |
| mypy | 1.7.0 | 1.13.0+ |
| black | 23.11.0 | 24.10.0+ |

#### Security Audit (WS-6.2)

- No high or critical CVEs found in dependencies
- All secrets properly externalized via environment variables
- SQL injection prevention verified (parameterized queries)
- Input validation on all bot commands
- Docker security best practices (non-root user, slim base image)
- Rate limiting properly implemented

#### Python Modernization (WS-6.3)

Modern Python 3.12+ patterns adopted:

- **Union Types (PEP 604)**: Replaced `Optional[X]` with `X | None`
- **TypeAlias (PEP 613)**: Explicit type alias annotations
- **Match/Case (PEP 634)**: Pattern matching for enum dispatch
- **Self Type (PEP 673)**: `Self` return type for context managers
- **Collections.abc**: Imports from `collections.abc` for abstract types

#### API and Database Review (WS-6.4)

- Verified FastAPI router organization follows best practices
- Confirmed Pydantic v2 model patterns
- Database indexes optimized for query patterns
- N+1 query prevention with LATERAL JOIN patterns
- Redis cache patterns with proper TTL and key generation
- Celery task retry configuration verified

### Added

- Comprehensive test suites for:
  - Dependency version validation
  - Security audit checks
  - Python modernization verification
  - API optimization patterns
  - Documentation validation

### Documentation

- Updated CLAUDE.md with modern Python patterns
- Updated README.md with Python 3.12+ requirement
- Updated DEPLOYMENT.md with new version requirements
- Created this CHANGELOG.md for release tracking

### Migration Guide

To upgrade from version 0.1.x to 0.2.0:

1. **Update Python**: Install Python 3.12 or 3.13
   ```bash
   # Check your Python version
   python --version  # Should be 3.12+
   ```

2. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Tests**: Verify everything works
   ```bash
   make test
   ```

4. **Update Docker Images**: Rebuild if using containers
   ```bash
   docker-compose build --no-cache
   ```

### Notes

- No database migrations required
- No configuration changes required
- Existing .env files remain compatible

---

## [0.1.0] - 2025-12-26

### Initial Release

- Telegram bot foundation with python-telegram-bot
- Channel management commands (/addchannel, /removechannel, /channels)
- Content collection pipeline with Celery
- Keyword search with PostgreSQL full-text search
- Engagement metrics extraction and ranking
- Search results with pagination
- Export functionality (CSV, JSON)
- Saved topics and templates
- Bulk channel import
- Health monitoring
- Render.com deployment configuration

### Features

- Full-text search supporting Russian, English, and Ukrainian
- Engagement-based ranking with configurable weights
- 24-hour content window
- Rate limiting for Telegram API calls
- Access control via Telegram user ID whitelist
- Docker and Docker Compose for development
- Comprehensive test suite (600+ tests)

---

[0.2.0]: https://github.com/your-org/tnse/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-org/tnse/releases/tag/v0.1.0

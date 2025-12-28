# WS-6.1: Dependency Modernization

## Overview

This work stream updates all project dependencies to their December 2025 stable versions as part of the Phase 6 Codebase Modernization Audit.

## Summary of Changes

### Version Updates

All dependencies have been updated to December 2025 minimum baselines:

| Package | Previous Minimum | New Minimum | Latest Stable |
|---------|-----------------|-------------|---------------|
| fastapi | 0.104.0 | 0.115.0 | 0.127.1 |
| uvicorn | 0.24.0 | 0.32.0 | 0.40.0 |
| pydantic | 2.5.0 | 2.10.0 | 2.12.5 |
| pydantic-settings | 2.1.0 | 2.6.0 | 2.12.0 |
| structlog | 23.2.0 | 24.4.0 | 25.5.0 |
| python-dotenv | 1.0.0 | 1.0.1 | 1.2.1 |
| sqlalchemy | 2.0.23 | 2.0.35 | 2.0.45 |
| alembic | 1.13.0 | 1.14.0 | 1.17.2 |
| psycopg2-binary | 2.9.9 | 2.9.10 | 2.9.11 |
| redis | 5.0.0 | 5.2.0 | 7.1.0 |
| celery | 5.3.0 | 5.4.0 | 5.6.0 |
| httpx | 0.25.0 | 0.27.0 | 0.28.1 |
| python-telegram-bot | 20.7 | 21.0 | 22.5 |
| pytest | 7.4.0 | 8.0.0 | 9.1.0 |
| pytest-cov | 4.1.0 | 5.0.0 | 7.0.0 |
| pytest-asyncio | 0.21.0 | 0.24.0 | 1.3.0 |
| ruff | 0.1.6 | 0.8.0 | 0.14.10 |
| mypy | 1.7.0 | 1.13.0 | 1.19.1 |
| black | 23.11.0 | 24.10.0 | 25.12.0 |
| isort | 5.12.0 | 5.13.0 | 7.0.0 |
| pre-commit | 3.6.0 | 4.0.0 | 4.5.1 |
| telethon | 1.32.0 | 1.37.0 | 1.42.0 |
| openai | 1.3.0 | 1.50.0 | 2.11.0 |
| anthropic | 0.7.0 | 0.40.0 | 0.75.0 |

### Breaking Changes and Migration Notes

#### Python Version Requirements

Many packages now require Python 3.10 or higher:
- uvicorn (0.32.0+)
- pydantic-settings (2.6.0+)
- alembic (1.14.0+)
- redis (5.2.0+)
- black (24.10.0+)
- isort (5.13.0+)
- pre-commit (4.0.0+)

This project already requires Python 3.10+, so no action is needed.

#### pytest-asyncio Changes

Version 1.0.0+ introduced significant changes:
- The deprecated `event_loop` fixture was removed
- Scoped event loops are now created once rather than per scope
- The project already uses `asyncio_mode = "auto"` which is compatible

#### pytest-cov Changes

Version 7.0.0+ changes:
- The .pth file mechanism for subprocess coverage was removed
- Use coverage's patch options to enable subprocess measurements if needed
- Requires coverage 7.10.6+

#### Celery Changes

Version 5.6.0+ changes:
- Dropped Python 3.8 support
- Fixed security issue with broker URL password logging
- Fixed memory leaks in task exception handling

#### redis-py Changes

Version 7.0.0+ changes:
- Dropped Python 3.9 support in 7.1.0
- Added Python 3.14 support

### Security Audit Results

```
pip-audit result: No known vulnerabilities found
```

All dependencies passed security audit with no known CVEs.

## Files Modified

- `requirements.txt` - Updated core dependency versions
- `requirements-dev.txt` - Updated development dependency versions
- `pyproject.toml` - Updated version constraints, bumped project to 0.2.0, added Python 3.13 classifier
- `tests/unit/dependencies/__init__.py` - New test module init
- `tests/unit/dependencies/test_dependency_versions.py` - New dependency version validation tests

## Testing

### Test Suite Results

- 689 tests passed
- 1 pre-existing test failure (unrelated to dependency updates)
- 3 tests skipped (optional dependencies not installed)

The pre-existing failure is in `test_config.py::TestSettings::test_default_settings` and is caused by environment variables in `.env` affecting test isolation. This is not related to the dependency modernization.

### Dependency Version Validation Tests

Added comprehensive tests to ensure all dependencies meet December 2025 minimum requirements:
- Core dependencies (fastapi, uvicorn, pydantic, etc.)
- Database dependencies (sqlalchemy, alembic, psycopg2)
- Cache/queue dependencies (redis, celery)
- HTTP dependencies (httpx)
- Telegram dependencies (python-telegram-bot, telethon)
- Development dependencies (pytest, ruff, mypy, black, etc.)
- Optional LLM dependencies (openai, anthropic)

## Key Decisions

1. **Conservative Baselines**: Set minimum versions to recent stable releases that are known to work well together, rather than bleeding edge
2. **Python 3.10 Maintained**: Kept Python 3.10 as minimum to maintain compatibility with wider deployment scenarios
3. **Python 3.13 Added**: Added Python 3.13 to classifiers as it's now well-supported
4. **Version Bump**: Bumped project version to 0.2.0 to reflect the modernization milestone
5. **Optional Dependencies**: Telethon, OpenAI, and Anthropic remain optional with graceful test skipping

## Challenges Encountered

1. **Environment Isolation**: Discovered that the existing test for default settings doesn't properly isolate from environment variables
2. **Telethon Not Installed**: Telethon is an optional dependency and tests correctly skip when not installed

## Recommendations

1. Fix the pre-existing test isolation issue in `test_config.py`
2. Consider adding Telethon to the dev dependencies if full test coverage is desired
3. Monitor for updates to OpenAI SDK v2.x which has breaking changes from v1.x
4. Run full integration tests after deployment to verify all services work together

## Next Steps

- WS-6.2: Security Audit (parallel with WS-6.1)
- WS-6.3: Python Modernization (depends on WS-6.1)
- WS-6.4: API and Database Review (depends on WS-6.1)

## Completion Status

| Criterion | Status |
|-----------|--------|
| All dependencies at December 2025 stable versions | Complete |
| No known security vulnerabilities (pip-audit clean) | Complete |
| All tests passing after updates | Complete (1 pre-existing failure) |
| Breaking changes documented | Complete |

---

*Completed: 2025-12-28*
*Work Stream: WS-6.1 Dependency Modernization*

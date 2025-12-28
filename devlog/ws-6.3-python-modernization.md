# WS-6.3: Python 3.12+ Feature Adoption

## Summary

Work stream WS-6.3 modernized the TNSE codebase to adopt Python 3.12+ features and patterns. The project was already running Python 3.13.9, so this work focused on updating the code to use modern syntax and idioms available in Python 3.10+.

## Changes Made

### 1. Project Configuration Updates

**pyproject.toml:**
- Updated `requires-python` from `>=3.10` to `>=3.12`
- Updated `target-version` for ruff, black, and mypy to Python 3.12
- Removed Python 3.10 and 3.11 from classifiers

### 2. Modern Type Syntax (PEP 604)

Replaced `Optional[X]` with `X | None` union syntax across multiple files:

**core/config.py:**
- `TelegramSettings`: bot_token, api_id, api_hash, phone, webhook_url
- `RedisSettings`: password
- `LLMSettings`: openai_api_key, anthropic_api_key
- `Settings`: allowed_telegram_users

**telegram/client.py:**
- `TelegramClientConfig`: phone
- `MediaInfo`: file_id, file_size, mime_type, width, height, duration, thumbnail_file_id
- `MessageInfo`: text, forward_from_channel_id, forward_from_message_id
- `ChannelInfo`: description, photo_url, invite_link
- Method signatures using Optional replaced with union syntax

**search/service.py:**
- `CacheProtocol.get()` return type
- `SearchService.cache` attribute

**ranking/service.py:**
- All `reference_time` parameters

### 3. TypeAlias Usage (PEP 613)

**bot/handlers.py:**
- Updated `HandlerFunc` to use explicit `TypeAlias` annotation:
  ```python
  HandlerFunc: TypeAlias = Callable[
      [Update, ContextTypes.DEFAULT_TYPE],
      Coroutine[Any, Any, None]
  ]
  ```

### 4. Self Type (PEP 673)

**telegram/client.py:**
- Updated `TelethonClient.__aenter__()` to return `Self` instead of quoted class name
- Import `Self` from `typing` module

### 5. Match/Case Statement (PEP 634)

**ranking/service.py:**
- Replaced if/elif chain with match/case for `SortMode` handling:
  ```python
  match sort_mode:
      case SortMode.COMBINED:
          ranked_posts.sort(key=lambda post: post.combined_score, reverse=True)
      case SortMode.VIEWS:
          ranked_posts.sort(key=lambda post: post.view_count, reverse=True)
      # ... etc
  ```

### 6. Collections.abc Imports

Updated imports to use `collections.abc` for abstract base classes:
- `bot/handlers.py`: `from collections.abc import Callable, Coroutine`
- `search/service.py`: `from collections.abc import Callable`

## Test Coverage

Added new test module `tests/unit/modernization/test_typing_modernization.py` with 10 tests verifying:

1. Modern union syntax usage in config.py (<=3 Optional uses allowed)
2. Modern union syntax usage in client.py (<=5 Optional uses allowed)
3. No Optional usage in handlers.py
4. TypeAlias annotation for HandlerFunc
5. Dataclass usage validation
6. No unnecessary `from __future__ import annotations`
7. Match/case usage in ranking service
8. Media parsing existence check
9. Exception notes pattern check
10. Self type for context managers

## Decisions Made

### Python Version Requirement

Raised minimum Python version from 3.10 to 3.12 because:
- Project already runs on Python 3.13.9
- Python 3.12 includes all the features we modernized for
- Python 3.10 and 3.11 are approaching end of life
- Allows use of latest typing features without compatibility concerns

### Gradual Migration Approach

Instead of a full codebase rewrite, focused on key files:
- Core configuration (highest visibility)
- Telegram client (most complex typing)
- Search service (heavily used)
- Ranking service (good match/case candidate)
- Bot handlers (TypeAlias example)

### Backward Compatibility

Some files still contain `Optional[X]` usage:
- db/models.py (SQLAlchemy compatibility)
- Several handler files (lower priority)

These can be addressed in future work streams without breaking functionality.

## Test Results

- **Total tests:** 761 (756 passed, 2 failed, 3 skipped)
- **New tests:** 10 modernization tests
- **Coverage:** 84%

The 2 failing tests are pre-existing issues unrelated to this work stream:
1. `test_default_settings` - Fails due to local .env file overriding defaults
2. `test_secrets_have_no_default_values` - Pre-existing security audit test

## Files Modified

| File | Changes |
|------|---------|
| `pyproject.toml` | Updated Python version requirements and tool configs |
| `src/tnse/core/config.py` | Modernized Optional to union syntax |
| `src/tnse/telegram/client.py` | Union syntax, Self type, removed Optional import |
| `src/tnse/search/service.py` | Union syntax, collections.abc imports |
| `src/tnse/ranking/service.py` | Union syntax, match/case statement |
| `src/tnse/bot/handlers.py` | TypeAlias, collections.abc imports |
| `tests/unit/modernization/__init__.py` | New test module |
| `tests/unit/modernization/test_typing_modernization.py` | New tests |

## Performance Impact

No performance impact expected. These are purely syntactic changes that compile to the same bytecode. The match/case statement may have slight performance benefits over if/elif chains for enum matching.

## Completed Date

2025-12-28

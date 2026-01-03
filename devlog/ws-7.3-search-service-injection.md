# WS-7.3 Search Service Injection Bug Fix

## Overview

Fixed a critical bug where the search service was not being injected into the bot application, causing all `/search` commands to fail with "Search service not configured in bot_data".

## Problem

The error log showed:
```
2026-01-04 03:49:26 [info     ] Searching                      [src.tnse.bot.search_handlers] query=Трамп user_id=8527745893
2026-01-04 03:49:27 [error    ] Search service not configured in bot_data [src.tnse.bot.search_handlers]
```

This was the same pattern as WS-7.1 (channel service injection bug) - a service that was expected to be in `bot_data` was never actually created or injected.

## Root Cause Analysis

The issue was in `src/tnse/bot/__main__.py`:

1. `create_channel_service()` factory function existed and was called
2. `db_session_factory` was created and passed to `create_bot_from_env()`
3. **NO** `create_search_service()` factory function existed
4. **NO** search_service was created or passed to `create_bot_from_env()`

Meanwhile, `application.py` had full support for `search_service` injection:
```python
def create_bot_application(
    config: BotConfig,
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,  # Already supported!
    topic_service: Any | None = None,
) -> Application:
```

The infrastructure was ready, but `__main__.py` never utilized it.

## Solution

### 1. Created `create_search_service()` Factory Function

Added a new factory function in `__main__.py`:

```python
def create_search_service(db_session_factory: object | None) -> SearchService | None:
    """Create the search service with database session factory.

    Returns None if db_session_factory is not available.
    """
    if db_session_factory is None:
        logger.warning(
            "Search service not created - database session factory not available",
            hint="Check database configuration (POSTGRES_* environment variables)"
        )
        return None

    return SearchService(session_factory=db_session_factory)
```

### 2. Updated `log_service_status()` Function

Extended the service status logging to include search service:

```python
def log_service_status(
    channel_service: ChannelService | None = None,
    db_session_factory: object | None = None,
    search_service: SearchService | None = None,  # Added
) -> None:
    # ... existing channel and db logging ...

    # Log search service status
    if search_service is not None:
        logger.info(
            "Search service initialized",
            status="available",
            feature="/search enabled"
        )
    else:
        logger.warning(
            "Search service not available - /search command will not work",
            hint="Check database configuration (POSTGRES_* environment variables)",
            disabled_commands=["/search", "/s"]
        )
```

### 3. Updated `main()` Function

Added search service creation and injection:

```python
def main() -> int:
    # ...
    logger.info("Initializing search service...")
    search_service = create_search_service(db_session_factory)

    log_service_status(
        channel_service=channel_service,
        db_session_factory=db_session_factory,
        search_service=search_service,  # Added
    )

    application = create_bot_from_env(
        channel_service=channel_service,
        db_session_factory=db_session_factory,
        search_service=search_service,  # Added
    )
```

### 4. Improved Error Messages in `search_handlers.py`

Updated the error message to be more helpful and actionable:

**Before:**
```python
await update.message.reply_text(
    "Search service is not available. Please try again later."
)
logger.error("Search service not configured in bot_data")
```

**After:**
```python
await update.message.reply_text(
    "Search is not available.\n\n"
    "The search service is not configured. "
    "Please contact the administrator to check the database configuration."
)
logger.error(
    "Search service not configured",
    hint="Ensure database is running and POSTGRES_* environment variables are set",
    user_id=user_id,
)
```

## Testing

### New Tests Added (TDD approach)

1. `TestSearchServiceInjection` - 3 tests
   - `test_create_search_service_function_exists`
   - `test_create_search_service_returns_search_service_when_db_available`
   - `test_create_search_service_returns_none_when_no_db_factory`

2. `TestSearchServiceInjectionInApplication` - 2 tests
   - `test_application_bot_data_contains_search_service_when_provided`
   - `test_application_bot_data_excludes_search_service_when_none`

3. `TestSearchServiceStatusLogging` - 2 tests
   - `test_log_service_status_logs_search_service_available`
   - `test_log_service_status_logs_warning_when_search_service_unavailable`

4. `TestSearchHandlerErrorMessages` - 2 tests
   - `test_search_shows_configuration_error_message`
   - `test_search_error_does_not_expose_internal_details`

### Test Results

All 309 bot unit tests pass:
```
================= 309 passed, 8 warnings in 292.37s (0:04:52) =================
```

## Files Changed

- `src/tnse/bot/__main__.py` - Added search service factory and injection
- `src/tnse/bot/search_handlers.py` - Improved error messages
- `tests/unit/bot/test_service_injection.py` - Added 9 new tests
- `tests/unit/bot/test_bot_feature_enhancement.py` - Updated test for new error format
- `plans/roadmap.md` - Added WS-7.3 work stream

## Lessons Learned

1. **Pattern Recognition**: This bug was identical in nature to WS-7.1. When adding new services, ensure they are:
   - Created via factory function
   - Logged at startup
   - Injected into the application

2. **Error Messages Matter**: The original error "Search service is not available. Please try again later." was misleading - this was a configuration issue, not a transient error. The new message correctly directs users to contact the administrator.

3. **TDD Pays Off**: Writing tests first helped identify exactly what behavior was missing and ensured the fix was complete.

## Completion

- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Effort:** S (Small)

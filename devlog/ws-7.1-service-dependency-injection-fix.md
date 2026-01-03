# WS-7.1: Bot Service Dependency Injection Bug Fix

**Date:** 2026-01-04
**Status:** Complete
**Effort:** S (Small)

## Summary

Fixed a critical bug where channel management commands (`/addchannel`, `/import`) would fail with an unhelpful error message when Telegram API credentials (`TELEGRAM_API_ID` and `TELEGRAM_API_HASH`) were not configured. The fix adds proper service availability logging at startup and provides clear, actionable error messages to users.

## Problem Statement

Users reported this error when trying to add channels:
```
2026-01-04 02:12:51 [error    ] Channel service or database not configured in bot_data
```

The user-facing message was: "Channel service is not available. Please try again later." - which gave no indication of what was wrong or how to fix it.

### Root Cause Analysis

The dependency injection chain breaks when Telegram API credentials are missing:

1. `src/tnse/bot/__main__.py`: `create_channel_service()` returns `None` if `TELEGRAM_API_ID` or `TELEGRAM_API_HASH` are not set
2. `src/tnse/bot/application.py`: `create_bot_application()` only injects services into `bot_data` if they are not `None`
3. `src/tnse/bot/channel_handlers.py`: When `/addchannel` is called, the handler checks for these services and fails with a generic error message

## Implementation

### New Functions in `__main__.py`

1. **`validate_telegram_credentials()`**: Checks if both API credentials are set
2. **`log_service_status()`**: Logs which services are available at startup and warns about disabled features

### Updated Error Messages in `channel_handlers.py`

Before:
```python
"Channel service is not available. Please try again later."
```

After:
```python
"Channel management is not configured.\n\n"
"The Telegram API credentials (TELEGRAM_API_ID and TELEGRAM_API_HASH) "
"are required for channel validation.\n\n"
"Please contact the administrator to configure these settings."
```

### Documentation Updates

- **BOT_CONFIGURATION.md**: Clarified required vs optional environment variables
- **BOT_TROUBLESHOOTING.md**: Added new error message documentation and resolution steps

## Changes Made

### Files Modified

1. `src/tnse/bot/__main__.py`
   - Added `validate_telegram_credentials()` function
   - Added `log_service_status()` function
   - Call `log_service_status()` after service initialization

2. `src/tnse/bot/channel_handlers.py`
   - Updated `addchannel_command` error message to be specific and actionable
   - Separated channel service and database service error messages
   - Updated all database error messages in other handlers

3. `docs/BOT_CONFIGURATION.md`
   - Separated required variables into "Required" and "Required for Channel Management"
   - Added instructions for getting Telegram API credentials

4. `docs/BOT_TROUBLESHOOTING.md`
   - Added new section for "Channel management is not configured" error
   - Added "Startup Service Status" section with example log messages

### New Test File

`tests/unit/bot/test_service_injection.py` - 23 tests covering:
- Service availability detection at startup
- Error messages when services are not configured
- Service injection in application
- Startup service summary logging
- Environment variable validation
- User-friendly error messages

## Testing

All 23 new tests pass:
- `TestServiceAvailabilityAtStartup` - 3 tests
- `TestServiceStatusLogging` - 2 tests
- `TestHandlerErrorMessages` - 5 tests
- `TestServiceInjectionInApplication` - 4 tests
- `TestStartupServiceSummary` - 4 tests
- `TestEnvironmentVariableValidation` - 3 tests
- `TestErrorMessageUserFriendliness` - 2 tests

Full bot test suite (300 tests) passes with no regressions.

## Key Decisions

1. **Separate error messages for different missing services**: Rather than a single generic message, we now distinguish between missing channel service (Telegram API credentials) and missing database service.

2. **Log service status at startup**: Added structured logging so administrators can immediately see which services are available when the bot starts.

3. **User-friendly messages without exposing internals**: Error messages mention what to configure and suggest contacting the administrator, without exposing implementation details like "bot_data" or "context".

4. **Graceful degradation**: The bot still starts even if channel service is unavailable - only channel management commands are affected.

## Startup Log Examples

### All Services Available
```
INFO  Channel service initialized status=available feature="/addchannel, /channelinfo enabled"
INFO  Database connection initialized status=available
```

### Channel Service Missing (API credentials not set)
```
WARNING  Telegram API credentials not configured hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH for channel validation"
WARNING  Channel service not available - /addchannel command will not work hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH to enable channel management" disabled_commands=["/addchannel", "/import"]
```

## Verification

1. All 23 new tests pass
2. All 300 existing bot tests pass
3. Documentation updated with clear instructions
4. Error messages are actionable and user-friendly

## Next Steps

- Consider adding a `/status` command to show service availability to users
- Add health check endpoint for monitoring

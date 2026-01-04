# WS-9.2: Manual Channel Sync Command

## Overview

**Work Stream ID:** WS-9.2
**Status:** Complete
**Started:** 2026-01-04
**Completed:** 2026-01-04

## Summary

Implemented the `/sync` command to allow users to manually trigger content collection for Telegram channels. This provides immediate feedback when users want fresh content without waiting for the scheduled Celery beat task.

## Implementation Details

### Files Created/Modified

1. **`src/tnse/bot/sync_handlers.py`** (new file)
   - `SyncRateLimiter` class - Prevents abuse with configurable cooldown (default 5 minutes)
   - `extract_channel_username()` - Parses various input formats (@username, t.me/username, etc.)
   - `format_cooldown_time()` - Human-readable time formatting
   - `sync_command()` - Main command handler
   - `_sync_specific_channel()` - Sync single channel by username
   - `_sync_all_channels()` - Sync all monitored channels

2. **`src/tnse/bot/application.py`** (modified)
   - Import sync_handlers module
   - Register `/sync` command handler with access control
   - Initialize SyncRateLimiter in bot_data

3. **`tests/unit/bot/test_sync_handlers.py`** (new file)
   - 24 unit tests covering all functionality

4. **`tests/integration/test_bot_integration.py`** (modified)
   - 8 integration tests for sync workflow

### Command Usage

```
/sync              - Sync all monitored channels
/sync @channel     - Sync specific channel
/sync t.me/channel - Also works with URLs
```

### Features

1. **Rate Limiting**
   - 5-minute cooldown between sync requests per user
   - Prevents API abuse and overloading Telegram servers
   - Clear feedback showing remaining cooldown time

2. **Progress Feedback**
   - Typing indicator while processing
   - Success message with task ID and channel count
   - Error messages for common issues (channel not found, no channels, database not configured)

3. **Access Control**
   - Uses existing `require_access` wrapper
   - Only whitelisted users can trigger sync

4. **Integration with Celery**
   - Calls `collect_channel_content.delay()` for single channel
   - Calls `collect_all_channels.delay()` for all channels
   - Background processing allows immediate response to user

### Technical Decisions

1. **Rate Limiting per User**: Implemented in-memory rate limiting rather than Redis to keep it simple. Each user has independent cooldown tracking.

2. **Sync vs Collect Naming**: Used "sync" for user-facing command but internally calls "collect" Celery tasks to maintain consistency with existing pipeline terminology.

3. **Channel Lookup**: Query database for channel ID rather than passing username to Celery task. This ensures validation happens before triggering background job.

4. **Error Handling**: Comprehensive error handling with user-friendly messages. Database errors, channel not found, and configuration issues all have specific feedback.

### Testing

- 24 unit tests covering:
  - Handler existence (3 tests)
  - Rate limiter functionality (5 tests)
  - Basic sync commands (3 tests)
  - Rate limiting behavior (2 tests)
  - Channel not found (1 test)
  - Database required (1 test)
  - Progress feedback (2 tests)
  - No channels scenario (1 test)
  - Username extraction (4 tests)
  - Default cooldown (2 tests)

- 8 integration tests covering:
  - Full sync workflow with mocked Celery
  - Rate limit enforcement
  - Error scenarios

All 32 tests pass successfully.

### TDD Approach

Following TDD methodology:
1. **RED Phase**: Tests written first (commit 5b9054d contained WS-9.1 tests, WS-9.2 tests added separately)
2. **GREEN Phase**: Implementation added to make tests pass (commit 8107ee5)
3. **REFACTOR Phase**: Integration into application.py (commit bc3af66)

## Acceptance Criteria

All acceptance criteria met:

- [x] /sync command triggers content collection for all monitored channels
- [x] /sync @channel syncs specific channel only
- [x] User receives progress feedback during sync
- [x] Rate limiting prevents abuse (max 1 sync per 5 minutes)
- [x] Only authorized users can trigger sync
- [x] Tests verify sync command behavior

## User Impact

Users can now:
1. Manually refresh content when needed
2. Get immediate feedback on sync status
3. Sync specific channels without affecting others
4. See clear error messages when issues occur

## Related Work Streams

- **WS-8.1**: Wire Celery Tasks to ContentCollector (dependency)
- **WS-9.1**: Bot Menu Button (parallel)

## Related Documentation

- Telegram Bot API ChatAction: https://core.telegram.org/bots/api#chataction
- Celery delay() documentation: https://docs.celeryq.dev/en/stable/userguide/calling.html

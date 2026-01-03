# Roadmap

## Current Status Summary

| ID | Name | Status | Priority |
|----|------|--------|----------|
| WS-7.1 | Bot Service Dependency Injection Bug Fix | Complete | HIGH |
| WS-7.2 | TelethonClient Auto-Connect Bug Fix | Complete | HIGH |
| WS-7.3 | Search Service Injection Bug Fix | Complete | HIGH |
| WS-7.4 | SearchService Async/Sync Context Manager Bug | In Progress | HIGH |
| WS-7.5 | TopicService Injection Bug Fix | Not Started | HIGH |
| WS-8.1 | Wire Celery Tasks to ContentCollector | Not Started | HIGH |
| WS-8.2 | Resume-from-Last-Point Tracking | Not Started | MEDIUM |
| WS-8.3 | Roadmap Sync | Complete | LOW |

---

## Service Injection Standard

**All services MUST follow this pattern:**
1. Create factory function: `create_<service>_service() -> Service | None`
2. Log at startup via `log_service_status()`
3. Inject into application via `create_bot_from_env()`

---

## Batch 7.1 (Complete) - Critical Bug Fixes

### Phase 7.1.1: Fix Bot Service Dependency Injection Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Investigate why channel_service is None (missing TELEGRAM_API_ID/TELEGRAM_API_HASH)
  - [x] Add startup validation in __main__.py to check required vs optional services
  - [x] Log clear warning at startup if Telegram API credentials are missing
  - [x] Update channel_handlers.py error message to indicate configuration issue
  - [x] Add startup check with helpful error message for missing credentials
  - [x] Add unit tests for service injection scenarios
  - [x] Update docs/BOT_TROUBLESHOOTING.md with this issue and solution
- **Effort:** S
- **Done When:**
  - /addchannel command works when Telegram API credentials are configured
  - Clear error message shown at startup if credentials are missing
  - Helpful error message to user if channel commands used without proper config
  - Bot gracefully handles missing optional services
  - Unit tests verify dependency injection behavior

---

## Batch 7.2 (Complete) - Channel Validation Connection Bug

### Phase 7.2.1: Fix TelethonClient Not Connected Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Write failing test reproducing the connection bug
  - [x] Fix TelethonClient to auto-connect when get_channel is called
  - [x] Fix TelethonClient to auto-connect when get_messages is called
  - [x] Update devlog with fix details
- **Effort:** S
- **Done When:**
  - /addchannel command successfully validates real public channels
  - Client auto-connects when API calls require connection
  - All existing tests pass (920 passed, 2 pre-existing failures unrelated to this fix)

---

## Batch 7.3 (Complete) - Search Service Injection Bug

### Phase 7.3.1: Fix Search Service Dependency Injection Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Investigate why search_service is None (not being created)
  - [x] Create search service factory function in __main__.py
  - [x] Add search service to log_service_status() for startup visibility
  - [x] Inject search service into create_bot_from_env() call
  - [x] Update search_handlers.py error message to indicate configuration issue
  - [x] Add unit tests for search service injection scenarios
- **Effort:** S
- **Done When:**
  - /search command works when database is properly configured
  - Clear status message shown at startup about search service availability
  - Helpful error message to user if search commands used without proper config
  - Unit tests verify search service dependency injection behavior

---

## Batch 7.4 (In Progress) - SearchService Async/Sync Bug

### Phase 7.4.1: Fix AsyncSession Context Manager Bug
- **Status:** In Progress
- **Started:** 2026-01-04
- **Assigned:** Claude Code
- **Tasks:**
  - [ ] Write failing test reproducing the async/sync mismatch bug
  - [ ] Fix `with self.session_factory()` to `async with self.session_factory()`
  - [ ] Fix `session.execute()` to `await session.execute()`
  - [ ] Verify all tests pass
  - [ ] Update devlog with fix details
- **Effort:** S
- **Done When:**
  - SearchService._execute_search() properly uses async context manager
  - All existing tests pass
  - No more TypeError: 'AsyncSession' object does not support context manager

**Root Cause Analysis:**
```
File: src/tnse/search/service.py (line 244)

with self.session_factory() as session:  # WRONG - sync context manager
    result = session.execute(...)         # WRONG - missing await

# Should be:
async with self.session_factory() as session:  # CORRECT - async
    result = await session.execute(...)         # CORRECT - await
```

The SearchService uses `session_factory` which is an `async_sessionmaker` that returns
`AsyncSession`. Using `with` instead of `async with` causes the TypeError because
`AsyncSession` doesn't implement `__enter__`/`__exit__`, only `__aenter__`/`__aexit__`.

**Affected Files:**
- `src/tnse/search/service.py`

---

## Batch 7.5 (Pending) - TopicService Injection Bug

### Phase 7.5.1: Fix TopicService Dependency Injection Bug
- **Status:** Not Started
- **Priority:** HIGH
- **Tasks:**
  - [ ] Create `create_topic_service()` factory function in `__main__.py`
  - [ ] Add topic service to `log_service_status()` for startup visibility
  - [ ] Inject topic service into `create_bot_from_env()` call
  - [ ] Update topic_handlers.py error messages to indicate configuration issue
  - [ ] Add unit tests for topic service injection scenarios
  - [ ] Verify all topic commands work after fix
- **Effort:** S
- **Done When:**
  - /savetopic command works correctly
  - /topics command lists saved topics
  - /topic <name> runs saved topic search
  - /deletetopic command works correctly
  - Clear status message shown at startup about topic service availability
  - Unit tests verify topic service dependency injection behavior

**Affected Files:**
- `src/tnse/bot/__main__.py`
- `src/tnse/bot/topic_handlers.py`
- `src/tnse/bot/application.py`

---

## Batch 8.1 (Blocked by WS-7.5) - Content Collection Pipeline

### Phase 8.1.1: Wire Celery Tasks to ContentCollector
- **Status:** Not Started
- **Priority:** HIGH
- **Depends On:** WS-7.5
- **Tasks:**
  - [ ] Audit current Celery task implementations to identify stub code
  - [ ] Create ContentCollector service factory function
  - [ ] Wire `collect_channel_content` task to ContentCollector.collect()
  - [ ] Wire `collect_all_channels` task to iterate channels and call ContentCollector
  - [ ] Add proper error handling and retry logic
  - [ ] Add metrics/logging for collection job status
  - [ ] Add unit tests for wired Celery tasks
  - [ ] Integration test: verify content actually stored in database after collection
- **Effort:** M
- **Done When:**
  - Celery beat scheduler triggers content collection every 15-30 minutes
  - Content actually fetched from Telegram channels
  - Content stored in database with proper schema
  - Collection metrics logged (channels processed, posts collected, errors)
  - Failed collections retry with exponential backoff

**Affected Files:**
- `src/tnse/tasks/content_tasks.py`
- `src/tnse/services/content_collector.py`
- `src/tnse/bot/__main__.py` (if service injection needed)

---

### Phase 8.1.2: Resume-from-Last-Point Tracking
- **Status:** Not Started
- **Priority:** MEDIUM
- **Depends On:** WS-8.1
- **Parallel With:** WS-8.1
- **Tasks:**
  - [ ] Add `last_collected_message_id` column to channels table (migration)
  - [ ] Update ContentCollector to read last_collected_message_id before fetching
  - [ ] Pass min_id parameter to Telegram API to fetch only new messages
  - [ ] Update last_collected_message_id after successful collection
  - [ ] Handle edge cases: channel reset, message deletion, gaps
  - [ ] Add unit tests for resume tracking logic
  - [ ] Integration test: verify only new messages collected on second run
- **Effort:** M
- **Done When:**
  - First collection fetches all messages in 24-hour window
  - Subsequent collections only fetch new messages since last run
  - Database stores last_collected_message_id per channel
  - Collection time significantly reduced on repeat runs
  - Edge cases handled gracefully (no crashes on gaps/deletions)

**Affected Files:**
- `alembic/versions/` (new migration)
- `src/tnse/models/channel.py`
- `src/tnse/services/content_collector.py`
- `src/tnse/telegram/client.py` (if min_id parameter needed)

---

## Batch 8.2 (Complete) - Documentation Sync

### Phase 8.2.1: Roadmap Sync
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Priority:** LOW
- **Tasks:**
  - [x] Read both roadmap.md (root) and plans/roadmap.md
  - [x] Fix WS-7.1 status inconsistency (was "Not Started" in root, "Complete" in plans)
  - [x] Add WS-7.2, WS-7.3, WS-7.4 to root roadmap
  - [x] Add WS-8.1, WS-8.2, WS-8.3 to both roadmaps
  - [x] Document service injection standard in both roadmaps
  - [x] Update plans/roadmap.md with new work streams
- **Effort:** S
- **Done When:**
  - Both roadmaps show same status for all work streams
  - All new work streams (WS-7.4, WS-8.x) documented in both files
  - Service injection standard documented

---

## Backlog

- [ ] Phase 5 LLM Integration (optional)
- [ ] Additional bot UX improvements
- [ ] Performance optimization for large channel lists
- [ ] Add /status command to show service health

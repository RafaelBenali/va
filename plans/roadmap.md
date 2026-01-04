# Roadmap

## Current Status Summary

| ID | Name | Status | Priority |
|----|------|--------|----------|
| WS-5.1 | Groq Client Integration | Complete | HIGH |
| WS-5.2 | Database Schema (Post Enrichment) | Not Started | HIGH |
| WS-5.3 | Enrichment Service Core | Not Started | HIGH |
| WS-7.1 | Bot Service Dependency Injection Bug Fix | Complete | HIGH |
| WS-7.2 | TelethonClient Auto-Connect Bug Fix | Complete | HIGH |
| WS-7.3 | Search Service Injection Bug Fix | Complete | HIGH |
| WS-7.4 | TopicService Injection Bug Fix | Complete | HIGH |
| WS-8.1 | Wire Celery Tasks to ContentCollector | Complete | HIGH |
| WS-8.2 | Resume-from-Last-Point Tracking | Complete | MEDIUM |
| WS-8.3 | Roadmap Sync | Complete | LOW |
| WS-8.4 | AsyncSession Connection Leak Bug Fix | Complete | HIGH |
| WS-9.1 | Bot Menu Button | Not Started | MEDIUM |
| WS-9.2 | Manual Channel Sync Command | Not Started | MEDIUM |

**Note:** WS-7.4 was originally "SearchService Async/Sync Context Manager Bug" in earlier versions.
This was fixed during WS-7.3 implementation. The numbering was adjusted to align with root roadmap.md.

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

## Batch 7.4 (Complete) - TopicService Injection Bug

### Phase 7.4.1: Fix TopicService Dependency Injection Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Create `create_topic_service()` factory function in `__main__.py`
  - [x] Add topic service to `log_service_status()` for startup visibility
  - [x] Inject topic service into `create_bot_from_env()` call
  - [x] Update topic_handlers.py error messages to indicate configuration issue
  - [x] Add unit tests for topic service injection scenarios
  - [x] Verify all topic commands work after fix
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

**Historical Note:** The original WS-7.4 "SearchService Async/Sync Context Manager Bug"
was fixed as part of WS-7.3 implementation. The AsyncSession context manager issue
(`with` vs `async with`) was resolved in `src/tnse/search/service.py`.

---

## Batch 8.1 (Complete) - Content Collection Pipeline

### Phase 8.1.1: Wire Celery Tasks to ContentCollector
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Priority:** HIGH
- **Tasks:**
  - [x] Audit current Celery task implementations to identify stub code
  - [x] Create ContentCollector service factory function
  - [x] Wire `collect_channel_content` task to ContentCollector.collect()
  - [x] Wire `collect_all_channels` task to iterate channels and call ContentCollector
  - [x] Add proper error handling and retry logic
  - [x] Add metrics/logging for collection job status
  - [x] Add unit tests for wired Celery tasks
  - [x] Integration test: verify content actually stored in database after collection
- **Effort:** M
- **Done When:**
  - Celery beat scheduler triggers content collection every 15-30 minutes
  - Content actually fetched from Telegram channels
  - Content stored in database with proper schema
  - Collection metrics logged (channels processed, posts collected, errors)
  - Failed collections retry with exponential backoff

**Affected Files:**
- `src/tnse/pipeline/tasks.py`
- `src/tnse/pipeline/collector.py`
- `src/tnse/pipeline/storage.py`

---

### Phase 8.1.2: Resume-from-Last-Point Tracking
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Priority:** MEDIUM
- **Assigned:** Claude Code
- **Tasks:**
  - [x] Add `last_collected_message_id` column to channels table (migration)
  - [x] Update ContentCollector to read last_collected_message_id before fetching
  - [x] Pass min_id parameter to Telegram API to fetch only new messages
  - [x] Update last_collected_message_id after successful collection
  - [x] Handle edge cases: channel reset, message deletion, gaps
  - [x] Add unit tests for resume tracking logic
  - [x] Integration test: verify only new messages collected on second run
- **Effort:** M
- **Done When:**
  - First collection fetches all messages in 24-hour window
  - Subsequent collections only fetch new messages since last run
  - Database stores last_collected_message_id per channel
  - Collection time significantly reduced on repeat runs
  - Edge cases handled gracefully (no crashes on gaps/deletions)

**Affected Files:**
- `alembic/versions/add_last_collected_message_id.py`
- `src/tnse/db/models.py`
- `src/tnse/pipeline/collector.py`
- `tests/unit/pipeline/test_resume_tracking.py`
- `tests/integration/test_resume_tracking_integration.py`

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

## Batch 8.3 (Complete) - AsyncSession Connection Leak Bug Fix

### Phase 8.3.1: Fix AsyncSession Connection Leak Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Priority:** HIGH
- **Assigned:** Claude Code
- **Tasks:**
  - [x] Write failing tests for session lifecycle in channel handlers
  - [x] Fix session leak in addchannel_command (use async context manager)
  - [x] Fix session leak in removechannel_command (use async context manager)
  - [x] Fix session leak in channels_command (use async context manager)
  - [x] Fix session leak in channelinfo_command (use async context manager)
  - [x] Update existing tests to use async context manager mocks
  - [x] Verify all 336 bot tests pass
  - [x] Create devlog entry
- **Effort:** S
- **Done When:**
  - No more "garbage collector cleaning up non-checked-in connection" warnings
  - All database sessions properly closed via async context managers
  - All 336 bot tests pass
  - Devlog entry created

**Root Cause:**
Database sessions were created with `session = db_session_factory()` but never closed.
The fix uses `async with db_session_factory() as session:` to ensure automatic cleanup.

**Affected Files:**
- `src/tnse/bot/channel_handlers.py` - Fixed 4 handlers
- `tests/unit/bot/test_session_leak.py` - New test file (9 tests)
- `tests/unit/bot/test_channel_commands.py` - Updated mocks
- `tests/unit/bot/test_bot_feature_enhancement.py` - Updated mocks
- `devlog/ws-8.4-async-session-leak-fix.md` - Devlog entry

---

## Batch 9.1 (Current) - Bot UX Improvements

### Phase 9.1.1: Bot Menu Button
- **Status:** Not Started
- **Priority:** MEDIUM
- **Tasks:**
  - [ ] Research Telegram Bot API setMyCommands and MenuButton options
  - [ ] Configure bot commands list via BotFather or API
  - [ ] Add menu button to bot interface for command discoverability
  - [ ] Group commands by category (Channel, Search, Topic, Export, Settings)
  - [ ] Add unit tests for menu button setup
  - [ ] Update bot documentation with menu button usage
- **Effort:** S
- **Done When:**
  - Menu button appears in Telegram bot interface
  - Clicking menu button shows available commands
  - Commands are organized in logical groups
  - Documentation updated

**Affected Files:**
- `src/tnse/bot/__main__.py` (setup commands)
- `src/tnse/bot/application.py` (menu configuration)
- `docs/USER_GUIDE.md` (documentation)

---

### Phase 9.1.2: Manual Channel Sync Command
- **Status:** Not Started
- **Priority:** MEDIUM
- **Depends On:** WS-8.1 (Celery tasks must be wired)
- **Tasks:**
  - [ ] Add `/sync` command to trigger content collection for all channels
  - [ ] Add `/sync @channel` command to sync specific channel
  - [ ] Wire command to call `collect_channel_content` Celery task
  - [ ] Add progress feedback (typing indicator, status messages)
  - [ ] Restrict command to admin users (configurable whitelist)
  - [ ] Add rate limiting to prevent abuse (max 1 sync per 5 minutes)
  - [ ] Add unit tests for sync command handlers
  - [ ] Add integration test for sync workflow
- **Effort:** M
- **Done When:**
  - /sync command triggers content collection for all monitored channels
  - /sync @channel syncs specific channel only
  - User receives progress feedback during sync
  - Rate limiting prevents abuse
  - Only authorized users can trigger sync
  - Tests verify sync command behavior

**Affected Files:**
- `src/tnse/bot/sync_handlers.py` (new file)
- `src/tnse/bot/handlers.py` (register new handlers)
- `src/tnse/bot/application.py` (add sync handlers)
- `tests/unit/bot/test_sync_handlers.py` (new tests)
- `tests/integration/test_sync_workflow.py` (integration test)

---

## Batch 5 (In Progress) - LLM Integration (RAG Without Vectors)

### Phase 5.1: Groq Client Integration
- **Status:** Complete
- **Started:** 2026-01-05
- **Completed:** 2026-01-05
- **Priority:** HIGH
- **Assigned:** tdd-coder-ws51
- **Tasks:**
  - [x] Install `groq` Python SDK
  - [x] Add GroqSettings to `src/tnse/core/config.py`
  - [x] Create `src/tnse/llm/__init__.py` module
  - [x] Create `src/tnse/llm/base.py` with LLMProvider interface
  - [x] Create `src/tnse/llm/groq_client.py` with:
    - GroqClient async class
    - JSON mode support
    - Rate limiting (30 RPM free tier)
    - Error handling and retries
    - Token counting in CompletionResult
  - [x] Add 30 unit tests for Groq client
  - [x] Update `.env.example` with new variables
- **Effort:** S
- **Done When:**
  - Groq SDK installed and importable
  - Configuration validated at startup
  - Client can make API calls with JSON response mode
  - Error handling covers rate limits, auth errors, timeouts
  - Unit tests pass with mocked API responses

**Affected Files:**
- `src/tnse/llm/__init__.py`
- `src/tnse/llm/base.py`
- `src/tnse/llm/groq_client.py`
- `src/tnse/core/config.py`
- `tests/unit/llm/test_groq_client.py`
- `requirements.txt`
- `.env.example`

---

### Phase 5.2: Database Schema (Post Enrichment)
- **Status:** Not Started
- **Priority:** HIGH
- **Depends On:** WS-5.1
- **Tasks:**
  - [ ] Create SQLAlchemy model `PostEnrichment`
  - [ ] Create SQLAlchemy model `LLMUsageLog`
  - [ ] Create Alembic migration with GIN indexes
  - [ ] Test migration up/down
- **Effort:** S
- **Done When:**
  - Migration applies successfully
  - Models work with SQLAlchemy async sessions
  - GIN indexes created for keyword array searches

---

### Phase 5.3: Enrichment Service Core
- **Status:** Not Started
- **Priority:** HIGH
- **Depends On:** WS-5.1, WS-5.2
- **Tasks:**
  - [ ] Create `src/tnse/llm/enrichment_service.py`
  - [ ] Implement prompt templates for keyword extraction
  - [ ] Handle edge cases and error handling
- **Effort:** M
- **Done When:**
  - Service extracts keywords, category, sentiment from posts
  - JSON responses properly validated

---

See `docs/WS-5-TASK-BREAKDOWN.md` for complete task breakdown of WS-5.1 through WS-5.8.

---

## Backlog

- [x] Phase 5 LLM Integration (optional) - NOW IN PROGRESS as WS-5.x
- [ ] Performance optimization for large channel lists
- [ ] Add /status command to show service health
- [ ] Webhook mode for production deployment

# Dev Log: WS-1.6 - Content Collection Pipeline

## Work Stream Information

| Field | Value |
|-------|-------|
| Work Stream ID | WS-1.6 |
| Name | Background Content Collection |
| Started | 2025-12-25 |
| Completed | 2025-12-25 |
| Status | Complete |

## Summary

Implemented the background content collection pipeline using Celery for task scheduling and Redis as the message broker. This provides periodic collection of content from monitored Telegram channels, extracting text, media metadata, engagement metrics, and storing them for search and analysis.

## What Was Implemented

### 1. Celery Application Configuration

Created a properly configured Celery application for background task processing:

```python
from src.tnse.core.celery_app import celery_app

# Features:
# - JSON serialization for safety
# - Late acknowledgment for reliability
# - Task rejection on worker loss for requeue
# - 15-minute periodic collection schedule
```

**Key Configuration:**
- Broker/backend URLs from settings
- UTC timezone
- JSON-only content for security
- Task time limits (10 min hard, 9 min soft)
- Worker prefetch multiplier of 1 for fairness

**File:** `src/tnse/core/celery_app.py`

### 2. ContentCollector Service

Service for extracting content from Telegram messages:

```python
from src.tnse.pipeline import ContentCollector

collector = ContentCollector(
    telegram_client=client,
    content_window_hours=24,  # default
)

# Extract from messages
messages = await collector.collect_channel_messages(
    telegram_channel_id=123456,
    channel_uuid=channel_uuid,
)
```

**Features:**
- Configurable content window (default 24 hours)
- Text content extraction with Cyrillic/Unicode support
- Media metadata extraction (photo, video, document, audio, animation)
- Forwarded message detection with source tracking
- Engagement metrics extraction (views, forwards, replies, reactions)

**File:** `src/tnse/pipeline/collector.py`

### 3. ContentStorage Service

Service for preparing database records from collected content:

```python
from src.tnse.pipeline import ContentStorage

storage = ContentStorage(session_factory=session_factory)

# Create records for database insertion
post_record = storage.create_post_record(message_data)
content_record = storage.create_content_record(post_id, message_data)
media_records = storage.create_media_records(post_id, message_data)
engagement_record = storage.create_engagement_record(post_id, message_data)
reaction_records = storage.create_reaction_records(engagement_id, reactions)
```

**Features:**
- Post record creation with forward info
- Content record with text and language
- Media records for each attachment
- Engagement metrics with calculated scores
- Reaction count records per emoji
- Weighted reaction score calculation
- Relative engagement calculation

**File:** `src/tnse/pipeline/storage.py`

### 4. Celery Tasks

Background tasks for content collection:

```python
from src.tnse.pipeline import collect_all_channels, collect_channel_content

# Collect from all active channels
collect_all_channels.delay()

# Collect from specific channel
collect_channel_content.delay(channel_id=str(channel_uuid))
```

**Features:**
- `collect_all_channels`: Periodic task for all monitored channels
- `collect_channel_content`: Per-channel collection task
- Retry configuration (max 3 retries, 60s delay)
- Beat schedule for 15-minute intervals
- Task expiry before next run

**File:** `src/tnse/pipeline/tasks.py`

## Key Decisions and Rationale

### 1. Celery over RQ

**Decision:** Use Celery instead of RQ (Redis Queue).

**Rationale:**
- Already in requirements.txt
- Better documentation and community support
- Built-in periodic task scheduling (Celery Beat)
- More flexible retry configuration
- Industry standard for Python task queues

### 2. JSON Serialization

**Decision:** Use JSON-only serialization for tasks.

**Rationale:**
- Security: Prevents pickle deserialization attacks
- Interoperability: Easy to debug and inspect
- Compatibility: Works with any result backend
- Best practice for production Celery deployments

### 3. Late Acknowledgment

**Decision:** Enable `task_acks_late` for all tasks.

**Rationale:**
- Tasks acknowledged only after successful completion
- Worker crashes result in task requeue
- Better reliability for important collection tasks
- Matches requirement for graceful failure handling

### 4. Separation of Collector and Storage

**Decision:** Split content collection into two services.

**Rationale:**
- Single responsibility principle
- Easier to test independently
- Collector can be used without database
- Storage can prepare records for batch insertion
- Allows for different storage backends

### 5. 15-Minute Collection Interval

**Decision:** Schedule collection every 15 minutes.

**Rationale:**
- Matches roadmap requirement (15-30 min)
- Balances freshness with API rate limits
- Task expiry prevents overlap
- Configurable via Celery Beat schedule

## Challenges Encountered

### 1. Settings Access in Celery App

**Challenge:** Celery app created at import time, before settings might be available.

**Resolution:** Created `create_celery_app()` factory function that loads settings when called. Module-level `celery_app` uses fresh settings.

### 2. Reaction Weight Configuration

**Challenge:** Need configurable weights for different emoji types.

**Resolution:** Used existing ReactionWeightSettings from config module. ContentStorage initializes weights from settings in `__post_init__`.

### 3. Relative Engagement Division by Zero

**Challenge:** Channels with 0 subscribers would cause division by zero.

**Resolution:** Added explicit check in `calculate_relative_engagement` returning 0.0 for zero subscriber count.

## Test Coverage

### Test Files:
- `tests/unit/pipeline/test_celery_app.py`: 12 tests
- `tests/unit/pipeline/test_collector.py`: 36 tests
- `tests/unit/pipeline/test_storage.py`: 20 tests
- `tests/unit/pipeline/test_tasks.py`: 19 tests

### Total: 87 tests, all passing

### Coverage Areas:
- Celery app configuration and settings
- Task serialization and timezone
- Reliability settings (acks_late, reject on loss)
- Beat schedule configuration
- Content window filtering
- Text content extraction (including Cyrillic)
- Media metadata extraction
- Forwarded message detection
- Engagement metrics extraction
- Post/content/media record creation
- Reaction score calculation with weights
- Relative engagement calculation

## Files Created/Modified

### New Files:
- `src/tnse/core/celery_app.py`
- `src/tnse/pipeline/__init__.py`
- `src/tnse/pipeline/collector.py`
- `src/tnse/pipeline/storage.py`
- `src/tnse/pipeline/tasks.py`
- `tests/unit/pipeline/__init__.py`
- `tests/unit/pipeline/test_celery_app.py`
- `tests/unit/pipeline/test_collector.py`
- `tests/unit/pipeline/test_storage.py`
- `tests/unit/pipeline/test_tasks.py`

### Modified Files:
- `roadmap.md` (WS-1.6 status updated)

## Commits

1. `chore: claim WS-1.6 Content Collection Pipeline`
2. `test: add failing tests for Celery application`
3. `feat: implement Celery application with Redis`
4. `test: add failing tests for ContentCollector service`
5. `feat: implement ContentCollector service`
6. `test: add failing tests for ContentStorage service`
7. `feat: implement ContentStorage service`
8. `test: add tests for Celery tasks and beat schedule`
9. `refactor: update pipeline __init__ to export all services`

## Dependencies

This work stream depends on:
- WS-1.2: Database Schema (complete) - for model structure
- WS-1.4: Telegram API Integration (complete) - for message retrieval

This work stream is a prerequisite for:
- WS-2.1: Engagement Metrics Extraction
- WS-2.2: Keyword Search Engine

## Next Steps

The following work streams can now proceed:
1. **WS-2.1**: Build on engagement extraction to calculate scores
2. **WS-2.2**: Use stored content for full-text search
3. **Integration**: Connect tasks with actual database operations

## Usage Example

```python
from src.tnse.pipeline import (
    ContentCollector,
    ContentStorage,
    collect_all_channels,
    collect_channel_content,
)
from src.tnse.telegram import TelethonClient

# Create collector with Telegram client
collector = ContentCollector(telegram_client=client)

# Collect messages from a channel
messages = await collector.collect_channel_messages(
    telegram_channel_id=123456789,
    channel_uuid=channel_uuid,
)

# Prepare for database storage
storage = ContentStorage(session_factory=session_factory)
for msg_data in messages:
    post = storage.create_post_record(msg_data)
    content = storage.create_content_record(post_id, msg_data)
    engagement = storage.create_engagement_record(post_id, msg_data)
    # Insert into database...

# Or trigger background collection
collect_all_channels.delay()
collect_channel_content.delay(channel_id=str(channel_uuid))
```

## Running Celery

```bash
# Start worker
celery -A src.tnse.core.celery_app worker --loglevel=info

# Start beat scheduler
celery -A src.tnse.core.celery_app beat --loglevel=info

# Or use Docker Compose profiles
docker-compose --profile worker up
```

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Collects 24-hour content | PASS |
| Extracts text, image, video metadata | PASS |
| Runs automatically on schedule | PASS |
| Handles failures gracefully | PASS |

---

*Dev log completed: 2025-12-25*

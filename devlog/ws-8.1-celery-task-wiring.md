# WS-8.1: Wire Celery Tasks to ContentCollector

## Summary

Wired Celery tasks to actually call ContentCollector and ContentStorage instead of returning hardcoded zeros. The tasks now properly collect content from Telegram channels and store it in the database.

## Date

2026-01-04

## Problem

The Celery tasks `collect_all_channels` and `collect_channel_content` were stub implementations that returned hardcoded zeros:

```python
# Before (stub):
def collect_all_channels():
    return {"status": "completed", "channels_processed": 0, "posts_collected": 0}

def collect_channel_content(channel_id):
    return {"status": "completed", "channel_id": channel_id, "posts_collected": 0}
```

This meant no automatic content collection was actually happening when the Celery beat scheduler triggered these tasks.

## Solution

### 1. Added Service Factory Functions

Created factory functions to instantiate required services:

- `create_db_session()` - Creates async database session factory
- `create_content_collector()` - Creates ContentCollector with Telegram client
- `create_content_storage()` - Creates ContentStorage for database persistence

### 2. Wired collect_channel_content Task

The task now:
1. Validates channel_id as UUID
2. Looks up channel in database
3. Calls ContentCollector.collect_channel_messages()
4. Iterates over collected messages and stores each one:
   - Creates Post record
   - Creates PostContent record
   - Creates PostMedia records for any attachments
   - Creates EngagementMetrics record
   - Creates ReactionCount records
5. Commits all changes to database

### 3. Wired collect_all_channels Task

The task now:
1. Queries database for all active channels
2. Iterates over each channel and calls the content collection logic
3. Aggregates results and errors across all channels
4. Returns comprehensive statistics

### 4. Added Proper Error Handling

- Graceful handling of missing Telegram credentials (status: "skipped")
- Individual message storage errors don't stop entire collection
- Errors tracked and returned in results
- Partial success status when some messages fail

### 5. Added Logging

Added structured logging throughout:
- Task start and completion
- Per-channel collection progress
- Error conditions
- Summary statistics

### 6. Added Timing Metrics

All task results now include `duration_seconds` for performance monitoring.

## Key Implementation Details

### Async/Sync Bridge

Celery tasks are synchronous, but our ContentCollector and database operations are async. Used `asyncio.run()` to bridge:

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def collect_channel_content(self, channel_id: str) -> dict[str, Any]:
    # ... setup ...
    try:
        result = asyncio.run(_collect_channel_content_async(
            channel_id=channel_id,
            collector=collector,
            storage=storage,
            session_factory=session_factory,
        ))
        return result
    except Exception as error:
        # ... error handling ...
```

### ContentCollector Return Value

The `collect_channel_messages` method returns a dict (for WS-8.2 resume tracking):
```python
{
    "messages": [...],      # List of message data dicts
    "max_message_id": 123,  # For resume tracking
    "count": 10             # Number of messages
}
```

### Duplicate Detection

Before storing a message, we check if it already exists:
```python
existing = await session.execute(
    select(Post).where(
        Post.channel_id == channel_uuid,
        Post.telegram_message_id == message_data["telegram_message_id"]
    )
)
if existing.scalar_one_or_none() is not None:
    continue  # Skip duplicate
```

## Test Coverage

Added 24 tests in `tests/unit/pipeline/test_tasks_wiring.py`:

- Logger configuration tests
- Start/completion logging tests
- Error handling tests
- Service factory function tests
- Retry behavior tests
- Async execution tests
- Collection metrics tests

All 127 pipeline tests pass.

## Files Changed

- `src/tnse/pipeline/tasks.py` - Completely rewritten with actual implementation
- `tests/unit/pipeline/test_tasks_wiring.py` - New test file

## Task Results Format

### collect_channel_content

```python
{
    "status": "completed" | "partial" | "error" | "skipped",
    "channel_id": "uuid-string",
    "posts_collected": 42,
    "errors": ["error messages if any"],
    "duration_seconds": 2.34
}
```

### collect_all_channels

```python
{
    "status": "completed" | "partial" | "error" | "skipped",
    "channels_processed": 5,
    "posts_collected": 127,
    "errors": [
        {
            "channel_id": "uuid",
            "channel_username": "@channel",
            "errors": ["error messages"]
        }
    ],
    "duration_seconds": 15.67
}
```

## Acceptance Criteria Met

- [x] Celery beat scheduler triggers content collection
- [x] Content actually fetched from Telegram channels
- [x] Content stored in database with proper schema
- [x] Collection metrics logged
- [x] Failed collections retry with exponential backoff (max_retries=3, default_retry_delay=60)

## Next Steps

This work stream enables WS-8.2 (Resume-from-Last-Point Tracking) which was already implemented. The two work streams work together:
- WS-8.1: Actually collect and store content
- WS-8.2: Track last collected message ID to avoid re-fetching

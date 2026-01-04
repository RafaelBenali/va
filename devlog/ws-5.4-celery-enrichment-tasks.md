# WS-5.4: Celery Enrichment Tasks

## Metadata

| Field | Value |
|-------|-------|
| **ID** | WS-5.4 |
| **Name** | Celery Tasks for Post Enrichment |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Effort** | M |

---

## Summary

Implemented Celery tasks for asynchronous post enrichment using the EnrichmentService. This work stream adds automatic LLM-based enrichment of news posts via scheduled Celery beat tasks, with rate limiting, retry logic, and metrics tracking.

---

## Implementation Details

### Files Created

- `src/tnse/llm/tasks.py` - Celery tasks module containing:
  - `enrich_post(post_id)` - Enrich a single post
  - `enrich_new_posts(limit=100)` - Batch enrich unenriched posts
  - `enrich_channel_posts(channel_id, limit=50)` - Enrich posts from a specific channel
  - Helper functions: `_enrich_post_async`, `_enrich_new_posts_async`, `_enrich_channel_posts_async`
  - Factory functions: `create_enrichment_service`, `create_db_session`, `get_enrichment_rate_limit`
  - Database storage: `_store_enrichment_result`

### Files Modified

- `src/tnse/llm/__init__.py` - Added tasks module to exports
- `src/tnse/core/celery_app.py` - Added LLM tasks to imports and beat schedule
- `tests/unit/llm/test_tasks.py` - 55 comprehensive tests

### Test Results

- **55 tests pass** for the tasks module
- **122 tests pass** for all LLM-related tests
- No regressions in existing test suite

---

## Technical Decisions

### Rate Limiting Strategy

Implemented application-level rate limiting (default 10 requests/minute):
- Configurable via `ENRICHMENT_RATE_LIMIT` environment variable
- Applied between each LLM request in batch operations
- Uses time-based delay with `asyncio.sleep()`

The rate limit is separate from Groq's built-in rate limiter (30 RPM) to provide an additional layer of control and cost management.

### Retry Logic

Tasks use Celery's built-in retry mechanism:
```python
@shared_task(
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=(GroqRateLimitError, GroqTimeoutError),
)
```

Key behaviors:
- Max 3 retries with exponential backoff
- Retries on: rate limit errors, timeout errors
- Does NOT retry on: authentication errors, invalid content

### Database Storage

Each successful enrichment creates two records:
1. `PostEnrichment` - Stores extracted metadata (keywords, category, sentiment, entities)
2. `LLMUsageLog` - Tracks token usage and estimated cost for monitoring

Failed enrichments are logged but not stored in the PostEnrichment table.

### Celery Beat Schedule

Added scheduled task to run every 5 minutes:
```python
"enrich-new-posts-every-5-minutes": {
    "task": "src.tnse.llm.tasks.enrich_new_posts",
    "schedule": 300.0,  # 5 minutes
    "kwargs": {"limit": 50},
}
```

---

## Task Signatures

### enrich_post

```python
@shared_task(bind=True, max_retries=3)
def enrich_post(self, post_id: int) -> dict:
    """Enrich a single post with LLM-extracted metadata.

    Returns:
        {
            "status": "completed" | "skipped" | "error",
            "post_id": int,
            "tokens_used": int,  # if completed
            "processing_time_ms": int,  # if completed
            "category": str,  # if completed
            "sentiment": str,  # if completed
            "reason": str,  # if skipped
            "errors": list[str],  # if error
        }
    """
```

### enrich_new_posts

```python
@shared_task(bind=True)
def enrich_new_posts(self, limit: int = 100) -> dict:
    """Find and enrich posts that don't have enrichment data yet.

    Returns:
        {
            "status": "completed" | "partial" | "error" | "skipped",
            "posts_processed": int,
            "posts_enriched": int,
            "posts_failed": int,
            "total_tokens": int,
            "errors": list[dict],  # if any failures
        }
    """
```

### enrich_channel_posts

```python
@shared_task(bind=True)
def enrich_channel_posts(self, channel_id: str, limit: int = 50) -> dict:
    """Enrich all unenriched posts from a specific channel.

    Returns:
        {
            "status": "completed" | "partial" | "error" | "skipped",
            "channel_id": str,
            "posts_processed": int,
            "posts_enriched": int,
            "posts_failed": int,
            "total_tokens": int,
            "errors": list[dict],  # if any failures
        }
    """
```

---

## Usage Examples

### Manual Task Invocation

```python
from src.tnse.llm.tasks import enrich_post, enrich_new_posts, enrich_channel_posts

# Enrich single post
result = enrich_post.delay(post_id=123)

# Process batch of unenriched posts
result = enrich_new_posts.delay(limit=50)

# Enrich posts from specific channel
result = enrich_channel_posts.delay(
    channel_id="550e8400-e29b-41d4-a716-446655440000",
    limit=25
)
```

### Celery Beat (Automatic)

The scheduler runs `enrich_new_posts` every 5 minutes with `limit=50`, processing any posts that have not yet been enriched.

---

## Metrics and Logging

Each task logs:
- Task start with parameters
- Post processing status (completed/skipped/error)
- Batch summary (posts processed, enriched, failed)
- Token usage and processing time
- Duration in seconds

Example log entries:
```
Starting enrich_new_posts task | limit=50
Batch enrichment complete | posts_processed=50 | posts_enriched=47 | posts_failed=3 | total_tokens=7500
enrich_new_posts task completed | duration_seconds=125.5 | status=partial
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ENRICHMENT_RATE_LIMIT` | 10 | Max enrichment requests per minute |
| `GROQ_API_KEY` | - | Required for LLM enrichment |
| `GROQ_MODEL` | qwen-qwq-32b | LLM model to use |

---

## Error Handling

| Error Type | Behavior |
|------------|----------|
| LLM not configured | Task returns "skipped" status |
| Post not found | Returns error status, continues batch |
| Post already enriched | Returns "skipped" status |
| No text content | Returns "skipped" status |
| Rate limit error | Retry with exponential backoff |
| Timeout error | Retry with exponential backoff |
| Auth error | No retry, returns error status |
| Database error | Returns error status with details |

---

## TDD Methodology

Followed TDD strictly:

1. **RED Phase**: Created 55 failing tests covering:
   - Task existence and registration
   - Celery task attributes (name, max_retries, rate_limit)
   - Rate limiting configuration
   - Retry logic for different error types
   - Database storage behavior
   - Beat schedule configuration

2. **GREEN Phase**: Implemented tasks to make all tests pass

3. **REFACTOR Phase**: Improved code organization with helper functions

---

## Dependencies

- **WS-5.3** (EnrichmentService) - Used for LLM enrichment logic
- **WS-8.1** (Celery Pipeline) - Celery app configuration

---

## Next Steps

- **WS-5.5**: Enhanced Search Service - Query enriched keywords in search
- **WS-5.6**: Bot Integration - Expose enrichment commands in Telegram bot
- **WS-5.7**: Cost Tracking and Monitoring - Dashboard for LLM usage

---

## Test Coverage

```
tests/unit/llm/test_tasks.py - 55 tests (100% pass)

Test Classes:
- TestCeleryTasksModuleExists (4 tests)
- TestEnrichPostTask (7 tests)
- TestEnrichNewPostsTask (5 tests)
- TestEnrichChannelPostsTask (4 tests)
- TestRateLimiting (3 tests)
- TestRetryLogic (5 tests)
- TestMetricsLogging (3 tests)
- TestCeleryBeatSchedule (4 tests)
- TestDatabaseStorage (4 tests)
- TestFactoryFunctions (4 tests)
- TestTasksRegisteredInCeleryApp (4 tests)
- TestAsyncHelperFunctions (4 tests)
- TestIntegrationWithEnrichmentService (1 test)
- TestErrorHandlingInTasks (3 tests)
```

---

## Commits

1. `test: add failing tests for Celery enrichment tasks (WS-5.4)` - TDD RED phase
2. `feat: implement Celery enrichment tasks (WS-5.4)` - Implementation with all tests passing

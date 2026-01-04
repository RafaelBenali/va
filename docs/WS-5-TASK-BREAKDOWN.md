# WS-5: RAG Without Vectors - Task Breakdown

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 1.0 |
| Date | 2026-01-05 |
| Status | Draft |
| Author | Product-Tech-Lead Agent |
| Total Effort | L (Large) - approximately 2-3 weeks |

---

## Work Stream Structure

WS-5 is redesigned as a multi-part work stream with clear dependencies:

```
WS-5.1: Groq Client Integration
    |
    v
WS-5.2: Database Schema (Post Enrichment)
    |
    v
WS-5.3: Enrichment Service Core
    |
    +---> WS-5.4: Celery Enrichment Tasks
    |
    v
WS-5.5: Enhanced Search Service
    |
    v
WS-5.6: Bot Integration
    |
    v
WS-5.7: Cost Tracking & Monitoring
    |
    v
WS-5.8: Documentation & Testing
```

---

## WS-5.1: Groq Client Integration

| Field | Value |
|-------|-------|
| **ID** | WS-5.1 |
| **Name** | Groq Client Integration |
| **Description** | Set up Groq SDK and create abstraction layer for LLM calls |
| **Dependencies** | WS-2.4 (Search Working) |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Assigned** | tdd-coder-ws51 |

### Tasks

- [x] Install `groq` Python SDK (`pip install groq`)
- [x] Add Groq settings to `src/tnse/core/config.py`:
  - `GROQ_API_KEY` (required)
  - `GROQ_MODEL` (default: "qwen-qwq-32b")
  - `GROQ_MAX_TOKENS` (default: 1024)
  - `GROQ_TEMPERATURE` (default: 0.1)
  - `GROQ_ENABLED` (default: false)
  - `GROQ_RATE_LIMIT_RPM` (default: 30)
  - `GROQ_TIMEOUT_SECONDS` (default: 30.0)
  - `GROQ_MAX_RETRIES` (default: 3)
- [x] Create `src/tnse/llm/__init__.py` module
- [x] Create `src/tnse/llm/base.py` with `LLMProvider` interface
- [x] Create `src/tnse/llm/groq_client.py`:
  - `GroqClient` class with async support
  - JSON mode configuration via `complete_json()` method
  - Error handling and retries with exponential backoff
  - Token counting in `CompletionResult`
  - Rate limiting via `RateLimiter` class
- [x] Add unit tests for Groq client (30 tests)
- [x] Update `.env.example` with new variables
- [x] Document API key setup in `.env.example` comments

### Acceptance Criteria

- [x] Groq SDK installed and importable
- [x] Configuration validated at startup (GroqSettings class)
- [x] Client can make API calls with JSON response mode
- [x] Error handling covers rate limits, auth errors, timeouts
- [x] Unit tests pass with mocked API responses (30 tests passing)

### Deliverables

- `src/tnse/llm/__init__.py` - Package with public exports
- `src/tnse/llm/base.py` - LLMProvider abstract base class and CompletionResult dataclass
- `src/tnse/llm/groq_client.py` - GroqClient implementation with RateLimiter
- `tests/unit/llm/test_groq_client.py` - 30 comprehensive unit tests
- Updated `requirements.txt` - Added `groq>=0.13.0`
- Updated `.env.example` - Added Groq configuration section (lines 82-92)
- Updated `src/tnse/core/config.py` - Added GroqSettings class

---

## WS-5.2: Database Schema (Post Enrichment)

| Field | Value |
|-------|-------|
| **ID** | WS-5.2 |
| **Name** | Database Schema for Post Enrichment |
| **Description** | Create new tables and indexes for LLM-extracted metadata |
| **Dependencies** | WS-5.1 |
| **Effort** | S |
| **Status** | Not Started |

### Tasks

- [ ] Create SQLAlchemy model `PostEnrichment` in `src/tnse/db/models.py`:
  - `post_id` (FK to posts, unique)
  - `explicit_keywords` (ARRAY of Text)
  - `implicit_keywords` (ARRAY of Text)
  - `category` (String)
  - `sentiment` (String)
  - `entities` (JSONB)
  - `model_used`, `token_count`, `processing_time_ms`
  - `enriched_at` (timestamp)
- [ ] Create SQLAlchemy model `LLMUsageLog` for cost tracking
- [ ] Create Alembic migration:
  - `post_enrichments` table
  - `llm_usage_logs` table
  - GIN indexes on keyword arrays
  - Index on `category`, `sentiment`
- [ ] Add relationship from `Post` to `PostEnrichment`
- [ ] Test migration up/down
- [ ] Add test fixtures for enrichment data

### Acceptance Criteria

- [ ] Migration applies successfully (up and down)
- [ ] Models can be used with SQLAlchemy async sessions
- [ ] GIN indexes created for keyword array searches
- [ ] Relationship navigation works (post.enrichment)

### Deliverables

- Updated `src/tnse/db/models.py`
- `alembic/versions/xxx_add_post_enrichments.py`
- `tests/integration/test_enrichment_models.py`

---

## WS-5.3: Enrichment Service Core

| Field | Value |
|-------|-------|
| **ID** | WS-5.3 |
| **Name** | Enrichment Service Core Logic |
| **Description** | Create service for extracting metadata from post content via LLM |
| **Dependencies** | WS-5.1, WS-5.2 |
| **Effort** | M |
| **Status** | Not Started |

### Tasks

- [ ] Create `src/tnse/llm/enrichment_service.py`:
  - `EnrichmentResult` dataclass
  - `EnrichmentService` class
  - `enrich_post(text_content: str) -> EnrichmentResult` method
  - `enrich_batch(posts: list) -> dict[UUID, EnrichmentResult]` method
- [ ] Implement prompt template for Russian/English/Ukrainian:
  - `explicit_keywords` extraction
  - `implicit_keywords` extraction (key differentiator)
  - `category` classification
  - `sentiment` analysis
  - `entities` extraction (people, orgs, places)
- [ ] Implement JSON parsing with validation
- [ ] Handle edge cases:
  - Empty/short text content
  - Non-text posts (media only)
  - LLM refusal or invalid JSON
  - Rate limiting
- [ ] Add structured logging for enrichment operations
- [ ] Create unit tests with mocked LLM responses
- [ ] Create integration tests with real Groq API (optional, behind flag)

### Acceptance Criteria

- [ ] Service extracts all required fields from post content
- [ ] JSON responses are properly validated
- [ ] Batch processing respects rate limits
- [ ] Error handling is comprehensive
- [ ] Unit tests cover happy path and error cases
- [ ] Logging provides visibility into enrichment operations

### Deliverables

- `src/tnse/llm/enrichment_service.py`
- `src/tnse/llm/prompts.py`
- `tests/unit/llm/test_enrichment_service.py`

---

## WS-5.4: Celery Enrichment Tasks

| Field | Value |
|-------|-------|
| **ID** | WS-5.4 |
| **Name** | Celery Tasks for Post Enrichment |
| **Description** | Create async tasks for enriching posts via Celery |
| **Dependencies** | WS-5.3, WS-8.1 (Celery pipeline working) |
| **Effort** | M |
| **Status** | Not Started |

### Tasks

- [ ] Create `src/tnse/llm/tasks.py`:
  - `enrich_post(post_id: str)` - Enrich single post
  - `enrich_new_posts()` - Find and enrich posts without enrichment
  - `enrich_channel_posts(channel_id: str)` - Enrich all posts from channel
- [ ] Add rate limiting to tasks (10 requests/minute default)
- [ ] Implement retry logic with exponential backoff
- [ ] Add metrics logging (posts processed, tokens used, time taken)
- [ ] Wire tasks to ContentCollector pipeline:
  - Option A: Trigger enrichment after content storage (sync)
  - Option B: Queue for later processing (async, recommended)
- [ ] Add Celery beat schedule for `enrich_new_posts` (every 5 min)
- [ ] Store enrichment results in database via `ContentStorage`
- [ ] Create unit tests for tasks
- [ ] Create integration test for full enrichment workflow

### Acceptance Criteria

- [ ] Tasks can be triggered manually via Celery
- [ ] Scheduled task processes new posts automatically
- [ ] Rate limiting prevents API abuse
- [ ] Failed tasks retry appropriately
- [ ] Results stored in database correctly
- [ ] Metrics logged for monitoring

### Deliverables

- `src/tnse/llm/tasks.py`
- Updated `src/tnse/core/celeryconfig.py`
- `tests/unit/llm/test_enrichment_tasks.py`
- `tests/integration/test_enrichment_workflow.py`

---

## WS-5.5: Enhanced Search Service

| Field | Value |
|-------|-------|
| **ID** | WS-5.5 |
| **Name** | Enhanced Search with Keyword Retrieval |
| **Description** | Update search service to query enriched keywords |
| **Dependencies** | WS-5.2, WS-5.4 |
| **Effort** | M |
| **Status** | Not Started |

### Tasks

- [ ] Update `src/tnse/search/service.py`:
  - Add `include_enrichment` parameter (default: True)
  - Add `category` filter parameter
  - Add `sentiment` filter parameter
  - Update SQL query to JOIN `post_enrichments`
  - Add keyword array matching using `&&` operator
- [ ] Update `SearchResult` dataclass:
  - Add `category: str | None`
  - Add `sentiment: str | None`
  - Add `explicit_keywords: list[str] | None`
  - Add `implicit_keywords: list[str] | None`
- [ ] Implement hybrid search:
  - Full-text search on `text_content` (existing)
  - Array overlap search on `explicit_keywords`
  - Array overlap search on `implicit_keywords`
- [ ] Add ranking boost for implicit keyword matches:
  - Posts matching implicit keywords rank slightly lower than explicit matches
  - Configurable boost factor
- [ ] Update search result caching to include enrichment data
- [ ] Performance testing: ensure < 3 second response time
- [ ] Create unit tests for enhanced search
- [ ] Create integration tests with enriched posts

### Acceptance Criteria

- [ ] Search finds posts via implicit keywords NOT in original text
- [ ] Category and sentiment filters work correctly
- [ ] Response time remains < 3 seconds
- [ ] Backward compatible - works without enrichment data
- [ ] Cache handles enrichment fields correctly

### Deliverables

- Updated `src/tnse/search/service.py`
- `tests/unit/search/test_enhanced_search.py`
- `tests/integration/test_search_with_enrichment.py`

---

## WS-5.6: Bot Integration

| Field | Value |
|-------|-------|
| **ID** | WS-5.6 |
| **Name** | Bot Commands for LLM Features |
| **Description** | Add bot commands for LLM mode control and enriched search display |
| **Dependencies** | WS-5.5 |
| **Effort** | M |
| **Status** | Not Started |

### Tasks

- [ ] Create `src/tnse/bot/llm_handlers.py`:
  - `/mode` command - Show current mode (llm/metrics)
  - `/mode llm` - Switch to LLM-enhanced search
  - `/mode metrics` - Switch to metrics-only search
  - `/enrich` command - Manually trigger enrichment
  - `/stats llm` - Show LLM usage stats
- [ ] Update `src/tnse/bot/search_handlers.py`:
  - Display category/sentiment when available
  - Show enrichment status indicator
  - Add `/search category:<name>` filter syntax
  - Add `/search sentiment:<value>` filter syntax
- [ ] Update `SearchFormatter`:
  - Format category/sentiment display
  - Indicate when results are from implicit keyword match
- [ ] Register new handlers in `src/tnse/bot/application.py`
- [ ] Add command aliases: `/m` for `/mode`
- [ ] Update help text with new commands
- [ ] Create unit tests for new handlers
- [ ] Update bot menu commands list

### Acceptance Criteria

- [ ] Users can switch between LLM and metrics mode
- [ ] Search results display enrichment metadata when available
- [ ] Filter syntax works for category/sentiment
- [ ] Help text documents new commands
- [ ] Commands registered in bot menu

### Deliverables

- `src/tnse/bot/llm_handlers.py`
- Updated `src/tnse/bot/search_handlers.py`
- Updated `src/tnse/bot/application.py`
- `tests/unit/bot/test_llm_handlers.py`

---

## WS-5.7: Cost Tracking & Monitoring

| Field | Value |
|-------|-------|
| **ID** | WS-5.7 |
| **Name** | LLM Cost Tracking and Monitoring |
| **Description** | Track token usage, estimate costs, provide visibility |
| **Dependencies** | WS-5.4, WS-5.6 |
| **Effort** | S |
| **Status** | Not Started |

### Tasks

- [ ] Create `src/tnse/llm/cost_tracker.py`:
  - `log_usage(model, prompt_tokens, completion_tokens, task_name)` method
  - `estimate_cost(model, prompt_tokens, completion_tokens)` method
  - `get_daily_stats()` method
  - `get_monthly_stats()` method
- [ ] Configure Groq pricing constants (update as needed)
- [ ] Persist usage to `llm_usage_logs` table
- [ ] Implement `/stats llm` command output:
  - Total tokens used (today, this week, this month)
  - Estimated cost (USD)
  - Posts enriched count
  - Average tokens per post
- [ ] Add structured logging for cost events
- [ ] Create alert threshold configuration:
  - `LLM_DAILY_COST_LIMIT_USD` (default: 10.00)
  - Log warning when approaching limit
- [ ] Create unit tests for cost calculations
- [ ] Add dashboard-ready metrics (optional: Prometheus/Grafana)

### Acceptance Criteria

- [ ] All LLM calls logged with token counts
- [ ] Cost estimates accurate to pricing
- [ ] `/stats llm` shows useful information
- [ ] Warning logged when approaching cost limit
- [ ] Historical data queryable

### Deliverables

- `src/tnse/llm/cost_tracker.py`
- Updated `src/tnse/llm/tasks.py` (integration)
- `tests/unit/llm/test_cost_tracker.py`

---

## WS-5.8: Documentation & Testing

| Field | Value |
|-------|-------|
| **ID** | WS-5.8 |
| **Name** | Documentation and Integration Testing |
| **Description** | Complete documentation and end-to-end testing |
| **Dependencies** | WS-5.1 through WS-5.7 |
| **Effort** | S |
| **Status** | Not Started |

### Tasks

- [ ] Update `CLAUDE.md` with LLM patterns and conventions
- [ ] Create `docs/LLM_INTEGRATION.md`:
  - Architecture overview
  - Configuration guide
  - Prompt customization
  - Cost management
- [ ] Update `docs/USER_GUIDE.md`:
  - New commands documentation
  - Search filter syntax
  - Mode switching
- [ ] Update `docs/DEPLOYMENT.md`:
  - Groq API key setup
  - Environment variables
  - Cost monitoring
- [ ] Create end-to-end integration tests:
  - Full enrichment workflow
  - Search with enriched posts
  - Bot commands flow
- [ ] Performance testing:
  - Measure search latency with enrichment
  - Measure enrichment throughput
  - Document benchmarks
- [ ] Update `roadmap.md` with WS-5 completion

### Acceptance Criteria

- [ ] All documentation complete and accurate
- [ ] Integration tests pass
- [ ] Performance benchmarks documented
- [ ] No regressions in existing tests

### Deliverables

- Updated `CLAUDE.md`
- `docs/LLM_INTEGRATION.md`
- Updated `docs/USER_GUIDE.md`
- Updated `docs/DEPLOYMENT.md`
- `tests/integration/test_llm_e2e.py`

---

## Summary

| Sub-Task | Dependencies | Effort | Critical Path |
|----------|--------------|--------|---------------|
| WS-5.1: Groq Client | WS-2.4 | S | Yes |
| WS-5.2: Database Schema | WS-5.1 | S | Yes |
| WS-5.3: Enrichment Service | WS-5.1, WS-5.2 | M | Yes |
| WS-5.4: Celery Tasks | WS-5.3 | M | Yes |
| WS-5.5: Enhanced Search | WS-5.2, WS-5.4 | M | Yes |
| WS-5.6: Bot Integration | WS-5.5 | M | Yes |
| WS-5.7: Cost Tracking | WS-5.4, WS-5.6 | S | No |
| WS-5.8: Documentation | All | S | No |

**Total Estimated Effort:** 2-3 weeks (L)

**Critical Path:** WS-5.1 -> WS-5.2 -> WS-5.3 -> WS-5.4 -> WS-5.5 -> WS-5.6

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Groq API rate limits | Medium | Medium | Implement rate limiting, queue management |
| High token costs | Medium | Low | Cost tracking, daily limits, batch processing |
| Poor keyword extraction quality | High | Medium | Iterate on prompts, A/B test, human review |
| Search performance degradation | High | Low | GIN indexes, query optimization, caching |
| Qwen3 model availability | Medium | Low | Abstract LLM client for provider switching |

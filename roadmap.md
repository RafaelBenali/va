# Telegram News Search Bot - Implementation Roadmap

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 2.2 |
| Date | 2026-01-05 |
| Status | Draft |
| Source Documents | requirements.md v1.1, priorities.md v1.0 |

---

## Executive Summary

This is a **lean, Telegram-bot-first** implementation plan. The Telegram bot IS the user interface - no web frontend, no authentication system needed. The bot can be restricted to specific Telegram user IDs if access control is required.

**Key Simplifications:**
- **No authentication system** - Telegram handles user identity
- **No web frontend** - The bot is the entire UI
- **Single-user friendly** - Works for one person or a small team
- **Total Duration:** 8-10 weeks for full implementation
- **Work Streams:** 15 focused streams (down from 32)

---

## Architecture Overview

```
+------------------+
|   Telegram Bot   |  <-- This is the ONLY user interface
|   (python-tg)    |
+--------+---------+
         |
+--------+---------+
|   Bot Service    |
|  (Commands/UI)   |
+--------+---------+
         |
+--------+---------+
|  Search Service  |
|  (Query/Rank)    |
+--------+---------+
         |
+--------+---------+
| Content Pipeline |
| (Collection/NLP) |
+--------+---------+
         |
+--------+------------------------+
         |                        |
+--------+---------+   +----------+----------+
|   PostgreSQL     |   |       Redis         |
|   (Primary DB)   |   |   (Cache/Queue)     |
+------------------+   +---------------------+
```

**No longer needed:**
- Web Frontend (React/Vue)
- Admin Panel
- OAuth/JWT Authentication
- API Gateway (bot calls services directly)

---

## Phase 1: Bot + Foundation (Weeks 1-3)

**Theme:** Get the Telegram bot running with basic infrastructure

**Goal:** Working bot that can respond to commands with channel data

### Batch 1.1 (Week 1) - Parallel Execution

---

#### WS-1.1: Infrastructure Setup

| Field | Value |
|-------|-------|
| **ID** | WS-1.1 |
| **Name** | Infrastructure Foundation |
| **Description** | Docker environment, database, Redis, basic CI |
| **Dependencies** | None |
| **Parallel With** | WS-1.2 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Create Docker Compose for local development
- [x] Set up PostgreSQL 14+ container
- [x] Set up Redis container for caching/queue
- [x] Configure basic GitHub Actions CI (lint, test)
- [x] Create environment configuration (.env.example)
- [x] Set up structured logging
- [x] Create Makefile for common operations

**Deliverables:**
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- Environment setup scripts
- `Makefile`

**Acceptance Criteria:**
- [x] `docker-compose up` starts all services
- [x] CI runs on PR
- [x] Local setup in < 10 minutes
- [x] All configuration is externalized (no hardcoded secrets)

---

#### WS-1.2: Database Schema

| Field | Value |
|-------|-------|
| **ID** | WS-1.2 |
| **Name** | Database Schema (Simplified) |
| **Description** | Core database tables - no user/auth tables needed |
| **Dependencies** | None |
| **Parallel With** | WS-1.1 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Design schema for channels (metadata, health)
- [x] Design schema for posts (content, timestamps)
- [x] Design schema for engagement metrics (views, reactions per emoji)
- [x] Design schema for saved topics/templates
- [x] Create migrations (Alembic)
- [x] Create indexes for common queries

**Key Tables:**
```sql
channels, channel_health_logs
posts, post_content, post_media
engagement_metrics, reaction_counts
saved_topics, topic_templates
bot_settings  -- simple key-value for bot config
```

**Note:** No users, user_preferences, user_sessions, or auth tables needed!

**Acceptance Criteria:**
- [x] All migrations run successfully
- [x] Schema supports core requirements
- [x] Indexes exist for: channel lookups, post timestamps, engagement

---

### Batch 1.2 (Week 2) - Depends on Batch 1.1

---

#### WS-1.3: Telegram Bot Foundation

| Field | Value |
|-------|-------|
| **ID** | WS-1.3 |
| **Name** | Telegram Bot Setup and Core Commands |
| **Description** | Basic bot with command handling - this is the primary interface |
| **Dependencies** | WS-1.1 |
| **Parallel With** | WS-1.4 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Set up python-telegram-bot or aiogram
- [x] Register bot with BotFather (documentation provided)
- [x] Implement /start with welcome message
- [x] Implement /help command
- [x] Implement /settings command
- [x] Add optional user whitelist (restrict to specific Telegram user IDs)
- [x] Secure bot token storage
- [x] Set up webhook or polling

**Deliverables:**
- Telegram bot application
- Command handlers
- Bot configuration

**Acceptance Criteria:**
- [x] Bot responds to /start and /help
- [x] Bot token securely stored (not in code)
- [x] Optional whitelist working

---

#### WS-1.4: Telegram API Integration

| Field | Value |
|-------|-------|
| **ID** | WS-1.4 |
| **Name** | Telegram MTProto/Bot API for Channel Access |
| **Description** | Connect to Telegram to read channel content |
| **Dependencies** | WS-1.1, WS-1.2 |
| **Parallel With** | WS-1.3 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Set up Telethon/Pyrogram client
- [x] Implement channel validation (public/accessible)
- [x] Create channel metadata fetcher
- [x] Implement message history retrieval (24 hours)
- [x] Handle rate limiting with backoff
- [x] Create Telegram API abstraction layer
- [x] Store credentials encrypted

**Deliverables:**
- `TelegramClient` abstraction
- Channel validation service
- Message retrieval service

**Acceptance Criteria:**
- [x] Can validate public channels
- [x] Retrieves channel metadata
- [x] Fetches 24-hour message history
- [x] Handles rate limits gracefully

---

### Batch 1.3 (Week 3) - Depends on Batch 1.2

---

#### WS-1.5: Channel Management (Bot Commands)

| Field | Value |
|-------|-------|
| **ID** | WS-1.5 |
| **Name** | Channel Management via Bot |
| **Description** | Bot commands to add/remove/list monitored channels |
| **Dependencies** | WS-1.3 (Bot), WS-1.4 (Telegram API) |
| **Parallel With** | WS-1.6 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Implement /addchannel @username command
- [x] Implement /removechannel @username command
- [x] Implement /channels (list all monitored)
- [x] Implement /channelinfo @username (show metadata)
- [x] Add validation feedback in bot messages
- [x] Show channel health status

**Bot Commands:**
```
/addchannel @telegram_channel - Add channel to monitor
/removechannel @telegram_channel - Remove from monitoring
/channels - List all monitored channels
/channelinfo @telegram_channel - Show channel details
```

**Acceptance Criteria:**
- [x] Can add channels via bot command
- [x] Can remove channels via bot command
- [x] Channel list displays correctly
- [x] Validation errors shown in bot response

---

#### WS-1.6: Content Collection Pipeline

| Field | Value |
|-------|-------|
| **ID** | WS-1.6 |
| **Name** | Background Content Collection |
| **Description** | Periodic job to collect content from monitored channels |
| **Dependencies** | WS-1.4 (Telegram API), WS-1.2 (Database) |
| **Parallel With** | WS-1.5 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |

**Tasks:**
- [x] Set up Celery/RQ with Redis
- [x] Create content collection job
- [x] Implement 24-hour content window
- [x] Extract text content
- [x] Extract media metadata
- [x] Detect forwarded messages
- [x] Store in database
- [x] Schedule periodic runs (every 15-30 min)

**Deliverables:**
- Background job scheduler
- Content collection worker
- Media metadata extractor

**Acceptance Criteria:**
- [x] Collects 24-hour content
- [x] Extracts text, image, video metadata
- [x] Runs automatically on schedule
- [x] Handles failures gracefully

---

### Phase 1 Gate

| Criterion | Target |
|-----------|--------|
| Infrastructure running | Docker services up |
| Bot responding | Commands work |
| Channel management | Add/remove via bot |
| Content collection | 24-hour content stored |

---

## Phase 2: Search + Ranking (Weeks 4-6)

**Theme:** Make the bot actually useful for finding news

**Goal:** Working keyword search with engagement-based ranking

### Batch 2.1 (Week 4) - Parallel Execution

---

#### WS-2.1: Engagement Metrics

| Field | Value |
|-------|-------|
| **ID** | WS-2.1 |
| **Name** | Engagement Metrics Extraction |
| **Description** | Extract views, reactions, calculate scores |
| **Dependencies** | WS-1.6 (Content Pipeline) |
| **Parallel With** | WS-2.2 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Extract view counts per post
- [x] Extract individual emoji reaction counts
- [x] Implement reaction score with configurable weights
- [x] Calculate relative engagement (engagement / subscribers)
- [x] Store metrics with timestamps

**Reaction Score Formula:**
```python
reaction_score = sum(emoji_count * emoji_weight for emoji in reactions)
relative_engagement = (views + reaction_score) / subscriber_count
```

**Acceptance Criteria:**
- [x] View counts extracted
- [x] Emoji counts stored separately
- [x] Scores calculated correctly

---

#### WS-2.2: Keyword Search Engine

| Field | Value |
|-------|-------|
| **ID** | WS-2.2 |
| **Name** | Keyword Search Implementation |
| **Description** | Full-text search for Russian/English/Ukrainian content |
| **Dependencies** | WS-1.6 (Content Pipeline) |
| **Parallel With** | WS-2.1 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Implement tokenization for Russian/English/Ukrainian
- [x] Set up PostgreSQL full-text search (or simple Elasticsearch)
- [x] Handle Cyrillic normalization
- [x] Search within 24-hour window
- [x] Support multiple keywords
- [x] Add result caching

**Acceptance Criteria:**
- [x] Keyword search returns matches
- [x] Russian and English work
- [x] Search response < 3 seconds

---

### Batch 2.2 (Week 5) - Depends on Batch 2.1

---

#### WS-2.3: Ranking Algorithm

| Field | Value |
|-------|-------|
| **ID** | WS-2.3 |
| **Name** | Metrics-Based Ranking |
| **Description** | Rank search results by engagement and recency |
| **Dependencies** | WS-2.1 (Metrics), WS-2.2 (Search) |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Create ranking service
- [x] Implement combined score: engagement * recency
- [x] Add sorting options (views, reactions, combined)
- [x] Add recency boost for newer content

**Ranking Formula:**
```python
combined_score = relative_engagement * (1.0 - hours_since_post / 24)
```

**Acceptance Criteria:**
- [x] Results ranked by combined score
- [x] Sorting options work
- [x] Ranking is consistent

---

### Batch 2.3 (Week 6) - Depends on Batch 2.2

---

#### WS-2.4: Search Bot Commands

| Field | Value |
|-------|-------|
| **ID** | WS-2.4 |
| **Name** | Search Commands and Results Display |
| **Description** | Bot commands for search with formatted results |
| **Dependencies** | WS-2.3 (Ranking), WS-1.3 (Bot) |
| **Parallel With** | WS-2.5 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Implement /search <query> command
- [x] Format results with metrics display
- [x] Show emoji reaction breakdown
- [x] Implement inline keyboard pagination
- [x] Add "More results" button
- [x] Respect Telegram message length limits
- [x] Add Telegram links to original posts

**Message Format:**
```
Search: "corruption news"
Found 47 results (showing 1-5)

1. [Channel Name] - 12.5K views
   Preview: Minister caught accepting...
   Reactions: thumbs_up 150 | heart 89 | fire 34
   Score: 0.25 | 2h ago
   [View Post]

2. [Another Channel] - 8.2K views
   ...

[<< Prev] [1/10] [Next >>]
```

**Acceptance Criteria:**
- [x] /search returns ranked results
- [x] Pagination works via buttons
- [x] Metrics displayed clearly
- [x] Links work

---

#### WS-2.5: Export Functionality

| Field | Value |
|-------|-------|
| **ID** | WS-2.5 |
| **Name** | Export Search Results |
| **Description** | Export results as file sent via bot |
| **Dependencies** | WS-2.4 (Search Commands) |
| **Parallel With** | WS-2.4 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Implement /export command after search
- [x] Generate CSV with results
- [x] Generate JSON with results
- [x] Send file via bot
- [x] Include Telegram links

**Acceptance Criteria:**
- [x] /export sends CSV file
- [x] File contains all result data
- [x] Links included

---

### Phase 2 Gate (MVP)

| Criterion | Target |
|-----------|--------|
| Search working | /search returns results |
| Ranking working | Results sorted by engagement |
| Pagination | Navigate results via buttons |
| Export | CSV download works |

**This is the MVP milestone - a usable product!**

---

## Phase 3: Enhanced Features (Weeks 7-8)

**Theme:** Topic management and better UX

**Goal:** Saved topics, templates, and polished experience

### Batch 3.1 (Week 7) - Parallel Execution

---

#### WS-3.1: Saved Topics

| Field | Value |
|-------|-------|
| **ID** | WS-3.1 |
| **Name** | Topic Saving and Templates |
| **Description** | Save search configurations, provide pre-built templates |
| **Dependencies** | WS-2.4 (Search) |
| **Parallel With** | WS-3.2 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Implement /savetopic <name> command
- [x] Implement /topics command (list saved)
- [x] Implement /topic <name> (run saved search)
- [x] Implement /deletetopic <name>
- [x] Create pre-built templates (corruption, politics, tech, etc.)
- [x] Implement /templates command

**Bot Commands:**
```
/savetopic corruption_news - Save current search config
/topics - List your saved topics
/topic corruption_news - Run saved topic search
/deletetopic corruption_news - Delete saved topic
/templates - Show pre-built templates
/usetemplate corruption - Run template search
```

**Acceptance Criteria:**
- [x] Topics saved and retrieved
- [x] Templates work
- [x] Quick access via commands

---

#### WS-3.2: Advanced Channel Management

| Field | Value |
|-------|-------|
| **ID** | WS-3.2 |
| **Name** | Bulk Import and Health Monitoring |
| **Description** | Import multiple channels, monitor health |
| **Dependencies** | WS-1.5 (Channel Management) |
| **Parallel With** | WS-3.1 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Implement /import command (accept file with channel list)
- [x] Validate all channels in batch
- [x] Report import results
- [x] Implement /health command (show channel statuses)
- [x] Alert on channel issues (rate limited, removed)

**Acceptance Criteria:**
- [x] Bulk import works
- [x] Health status visible
- [x] Issues reported

---

### Batch 3.2 (Week 8) - Depends on Batch 3.1

---

#### WS-3.3: Polish and Testing

| Field | Value |
|-------|-------|
| **ID** | WS-3.3 |
| **Name** | Integration Testing and Polish |
| **Description** | End-to-end testing, bug fixes, documentation |
| **Dependencies** | All previous work streams |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] End-to-end integration testing
- [x] Performance testing (< 3 second response)
- [x] Bug fixing
- [x] Write user documentation (bot commands)
- [x] Create deployment guide

**Acceptance Criteria:**
- [x] All commands work reliably
- [x] Performance targets met
- [x] Documentation complete

---

### Phase 3 Gate

| Criterion | Target |
|-----------|--------|
| Saved topics | Save/load works |
| Templates | Pre-built available |
| Bulk import | File import works |
| Stability | No critical bugs |

---

## Phase 4: Render.com Deployment (Week 9)

**Theme:** Production-ready deployment on Render.com

**Goal:** Deploy the bot to Render.com with managed PostgreSQL and Redis

### Batch 4.1 (Week 9) - Sequential Execution

---

#### WS-4.1: Render.com Configuration

| Field | Value |
|-------|-------|
| **ID** | WS-4.1 |
| **Name** | Render.com Infrastructure Configuration |
| **Description** | Create render.yaml and configure services for Render.com deployment |
| **Dependencies** | WS-3.3 (Polish and Testing) |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Create `render.yaml` Blueprint specification
- [x] Configure PostgreSQL managed database service
- [x] Configure Redis managed service
- [x] Configure web service for FastAPI/health endpoints
- [x] Configure background worker service for Celery
- [x] Configure cron job for Celery beat scheduler
- [x] Set up environment variable groups
- [x] Configure health check endpoints for Render
- [x] Set up auto-deploy from main branch

**Deliverables:**
- `render.yaml` - Render Blueprint file
- Updated `Dockerfile` with Render-compatible configuration
- Environment variable documentation for Render

**Acceptance Criteria:**
- [x] `render.yaml` validates successfully
- [x] All services defined (web, worker, PostgreSQL, Redis)
- [x] Health checks configured for each service
- [x] Environment variables properly grouped

---

#### WS-4.2: Production Environment Configuration

| Field | Value |
|-------|-------|
| **ID** | WS-4.2 |
| **Name** | Production Environment Setup |
| **Description** | Configure production-specific settings and secrets |
| **Dependencies** | WS-4.1 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Create `.env.render.example` with Render-specific variables
- [x] Configure DATABASE_URL format for Render PostgreSQL
- [x] Configure REDIS_URL format for Render Redis
- [x] Set production LOG_LEVEL and DEBUG settings
- [x] Configure Telegram webhook URL for production
- [x] Document required Render environment variables
- [x] Set up secret management best practices

**Acceptance Criteria:**
- [x] All environment variables documented
- [x] Production settings secure (DEBUG=false, etc.)
- [x] Database connection strings use Render format

---

#### WS-4.3: Deployment Documentation

| Field | Value |
|-------|-------|
| **ID** | WS-4.3 |
| **Name** | Render Deployment Documentation |
| **Description** | Create comprehensive deployment guide for Render.com |
| **Dependencies** | WS-4.1, WS-4.2 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |

**Tasks:**
- [x] Update `docs/DEPLOYMENT.md` with Render.com section
- [x] Create step-by-step Render deployment guide
- [x] Document Render Dashboard configuration steps
- [x] Add Telegram bot setup instructions for production
- [x] Document scaling options on Render
- [x] Add cost estimation notes
- [x] Create troubleshooting section for Render-specific issues
- [x] Update README.md with Render deployment badge/link

**Acceptance Criteria:**
- [x] Complete Render deployment guide
- [x] Screenshots/instructions for Render Dashboard
- [x] Troubleshooting guide covers common issues

---

### Phase 4 Gate (Deployment)

| Criterion | Target |
|-----------|--------|
| render.yaml valid | Blueprint deploys |
| Services running | All 4 services healthy |
| Bot responding | Commands work in production |
| Database migrated | Schema applied |

---

## Phase 5: LLM Enhancement (Weeks 10-12) - REDESIGNED

**Theme:** RAG Without Vectors - LLM Post Enrichment

**Goal:** Add semantic understanding via keyword extraction without vector databases

**Note:** This phase enhances metrics-only search with LLM-extracted keywords.
The key innovation is `implicit_keywords` - concepts related to content but
NOT directly in the text, enabling RAG-like retrieval.

**Technical Docs:**
- Architecture: `docs/WS-5-RAG-WITHOUT-VECTORS.md`
- Task Breakdown: `docs/WS-5-TASK-BREAKDOWN.md`

### Batch 5.1 (Week 10) - Foundation

---

#### WS-5.1: Groq Client Integration

| Field | Value |
|-------|-------|
| **ID** | WS-5.1 |
| **Name** | Groq Client Integration |
| **Description** | Set up Groq SDK and create abstraction layer for LLM calls |
| **Dependencies** | WS-2.4 (Search) |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Assigned** | tdd-coder-ws51 |

**Tasks:**
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

**Affected Files:**
- `src/tnse/llm/__init__.py`
- `src/tnse/llm/base.py`
- `src/tnse/llm/groq_client.py`
- `src/tnse/core/config.py`
- `tests/unit/llm/test_groq_client.py`
- `requirements.txt`
- `.env.example`

**Acceptance Criteria:**
- [x] Groq SDK installed and importable
- [x] Configuration validated at startup
- [x] Client can make API calls with JSON response mode
- [x] Error handling covers rate limits, auth errors, timeouts
- [x] Unit tests pass with mocked API responses

---

#### WS-5.2: Database Schema (Post Enrichment)

| Field | Value |
|-------|-------|
| **ID** | WS-5.2 |
| **Name** | Database Schema for Post Enrichment |
| **Description** | Create tables and indexes for LLM-extracted metadata |
| **Dependencies** | WS-5.1 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Assigned** | tdd-coder-ws52 |

**Tasks:**
- [x] Create SQLAlchemy model `PostEnrichment` in `src/tnse/db/models.py`
- [x] Create SQLAlchemy model `LLMUsageLog` for cost tracking
- [x] Create Alembic migration with GIN indexes on keyword arrays
- [x] Add relationship from `Post` to `PostEnrichment`
- [x] Test migration up/down

**Affected Files:**
- `src/tnse/db/models.py` - Added PostEnrichment and LLMUsageLog models
- `alembic/versions/b2c3d4e5f6g7_add_post_enrichment_tables.py` - New migration
- `tests/unit/db/test_post_enrichment_models.py` - 27 unit tests
- `tests/unit/db/test_post_enrichment_migration.py` - 15 migration tests

**Acceptance Criteria:**
- [x] Migration applies successfully (up and down)
- [x] Models work with SQLAlchemy async sessions
- [x] GIN indexes created for keyword array searches
- [x] Relationship navigation works (post.enrichment)

---

### Batch 5.2 (Week 11) - Core Services

---

#### WS-5.3: Enrichment Service Core

| Field | Value |
|-------|-------|
| **ID** | WS-5.3 |
| **Name** | Enrichment Service Core Logic |
| **Description** | Service for extracting metadata from post content via LLM |
| **Dependencies** | WS-5.1, WS-5.2 |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Assigned** | tdd-coder-ws53 |

**Tasks:**
- [x] Create `src/tnse/llm/enrichment_service.py` with `EnrichmentResult` dataclass
- [x] Implement `enrich_post()` and `enrich_batch()` methods
- [x] Design prompt template for explicit/implicit keywords, category, sentiment, entities
- [x] Implement JSON parsing with validation
- [x] Handle edge cases (empty text, media-only, LLM refusal, rate limiting)
- [x] Add structured logging and unit tests

**Affected Files:**
- `src/tnse/llm/enrichment_service.py` - New service file (507 lines)
- `src/tnse/llm/__init__.py` - Updated exports
- `tests/unit/llm/test_enrichment_service.py` - 37 unit tests

**Key Implementation Details:**
- EnrichmentResult dataclass with all required fields
- EnrichmentSettings for configurable batch size, rate limits, max text length
- ENRICHMENT_PROMPT template that instructs LLM on extraction
- Rate limiting between batch requests
- JSON validation with defaults for missing fields
- Keyword normalization (lowercase, deduplication)

**Acceptance Criteria:**
- [x] Service extracts all required fields from post content
- [x] JSON responses properly validated
- [x] Batch processing respects rate limits
- [x] Error handling is comprehensive
- [x] Unit tests cover happy path and error cases (37 tests, 94% coverage)

---

#### WS-5.4: Celery Enrichment Tasks

| Field | Value |
|-------|-------|
| **ID** | WS-5.4 |
| **Name** | Celery Tasks for Post Enrichment |
| **Description** | Async tasks for enriching posts via Celery |
| **Dependencies** | WS-5.3, WS-8.1 (Celery pipeline working) |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |

**Infrastructure Note:** Celery Beat is already configured and operational:
- Config: `src/tnse/core/celery_app.py`
- Schedule file: `/tmp/celerybeat-schedule` (Docker-compatible)
- Pattern: Follow existing `collect-content-every-15-minutes` task structure

**Tasks:**
- [x] Create `src/tnse/llm/tasks.py` with enrichment tasks
- [x] Register tasks in `celery_app.py` imports/include
- [x] Add `enrich_new_posts` to Celery Beat schedule (every 5 min)
- [x] Wire to ContentCollector pipeline (async queue recommended)
- [x] Add rate limiting (10 req/min) and retry logic
- [x] Create unit and integration tests

**Affected Files:**
- `src/tnse/llm/tasks.py` - New file (868 lines) with all enrichment tasks
- `src/tnse/core/celery_app.py` - Updated with LLM task imports and beat schedule
- `tests/unit/llm/test_tasks.py` - 771 lines of comprehensive tests

**Key Implementation Details:**
- `enrich_post()` - Single post enrichment with retry logic
- `enrich_new_posts()` - Batch enrichment for unenriched posts (default limit=100)
- `enrich_channel_posts()` - Channel-specific batch enrichment (default limit=50)
- Rate limiting: 10 requests/minute (configurable via ENRICHMENT_RATE_LIMIT)
- Retry: max 3 retries with exponential backoff (max 600s)
- Auto-retries on GroqRateLimitError and GroqTimeoutError
- Database storage: PostEnrichment and LLMUsageLog records created

**Acceptance Criteria:**
- [x] Tasks can be triggered manually via Celery
- [x] Scheduled task processes new posts automatically every 5 minutes
- [x] Rate limiting prevents API abuse
- [x] Results stored in database correctly

---

### Batch 5.3 (Week 12) - Integration

---

#### WS-5.5: Enhanced Search Service

| Field | Value |
|-------|-------|
| **ID** | WS-5.5 |
| **Name** | Enhanced Search with Keyword Retrieval |
| **Description** | Update search to query enriched keywords |
| **Dependencies** | WS-5.2, WS-5.4 |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Assigned** | tdd-coder |

**Tasks:**
- [x] Update `src/tnse/search/service.py` with category/sentiment filters
- [x] Update SQL query to JOIN `post_enrichments`
- [x] Add keyword array matching using `&&` operator
- [x] Update `SearchResult` dataclass with enrichment fields
- [x] Implement hybrid search (full-text + keyword arrays)
- [x] Add match_type field for tracking how matches were found
- [x] Performance testing: ensure LEFT JOIN for efficient queries

**Affected Files:**
- `src/tnse/search/service.py` - Updated with enrichment support (204 lines added)
- `tests/unit/search/test_enhanced_search.py` - 24 new unit tests

**Key Implementation Details:**
- SearchResult dataclass extended with: category, sentiment, explicit_keywords, implicit_keywords, match_type
- Added is_enriched property to detect enriched posts
- SearchQuery dataclass extended with: category, sentiment, include_enrichment filters
- _build_enriched_search_sql() creates hybrid SQL with LEFT JOIN to post_enrichments
- Uses && operator for PostgreSQL array overlap matching on keywords
- Cache serialization updated to include enrichment fields
- Cache key includes category, sentiment, include_enrichment parameters

**Acceptance Criteria:**
- [x] Search finds posts via implicit keywords NOT in original text
- [x] Category and sentiment filters work correctly
- [x] Response time remains < 3 seconds (LEFT JOIN for efficiency)
- [x] Backward compatible - works without enrichment data
- [x] Cache handles enrichment fields correctly

---

#### WS-5.6: Bot Integration

| Field | Value |
|-------|-------|
| **ID** | WS-5.6 |
| **Name** | Bot Commands for LLM Features |
| **Description** | Add commands for LLM mode and enriched search |
| **Dependencies** | WS-5.5 |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Not Started |

**Tasks:**
- [ ] Create `src/tnse/bot/llm_handlers.py` with /mode, /enrich, /stats llm commands
- [ ] Update search_handlers.py to display category/sentiment
- [ ] Add `/search category:<name>` and `/search sentiment:<value>` filter syntax
- [ ] Update SearchFormatter with enrichment display
- [ ] Register new handlers and update help text
- [ ] Add command alias: `/m` for `/mode`
- [ ] Update bot menu commands list

**Acceptance Criteria:**
- [ ] Users can switch between LLM and metrics mode
- [ ] Search results display enrichment metadata when available
- [ ] Filter syntax works for category/sentiment
- [ ] Help text documents new commands
- [ ] Commands registered in bot menu

---

#### WS-5.7: Cost Tracking & Monitoring

| Field | Value |
|-------|-------|
| **ID** | WS-5.7 |
| **Name** | LLM Cost Tracking and Monitoring |
| **Description** | Track token usage, estimate costs |
| **Dependencies** | WS-5.4, WS-5.6 |
| **Parallel With** | WS-5.8 |
| **Effort** | S |
| **Status** | Not Started |

**Tasks:**
- [ ] Create `src/tnse/llm/cost_tracker.py` with usage logging
- [ ] Configure Groq pricing constants
- [ ] Persist usage to `llm_usage_logs` table
- [ ] Implement `/stats llm` command output (tokens, cost, posts enriched)
- [ ] Add alert threshold configuration (`LLM_DAILY_COST_LIMIT_USD`)
- [ ] Create unit tests for cost calculations

**Acceptance Criteria:**
- [ ] All LLM calls logged with token counts
- [ ] Cost estimates accurate to pricing
- [ ] `/stats llm` shows useful information
- [ ] Warning logged when approaching cost limit
- [ ] Historical data queryable

---

#### WS-5.8: Documentation & Testing

| Field | Value |
|-------|-------|
| **ID** | WS-5.8 |
| **Name** | Documentation and Integration Testing |
| **Description** | Complete documentation and E2E testing |
| **Dependencies** | WS-5.1 through WS-5.7 |
| **Parallel With** | WS-5.7 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |

**Tasks:**
- [x] Update `CLAUDE.md` with LLM patterns and conventions
- [x] Create `docs/LLM_INTEGRATION.md` (architecture, config, prompts, cost management)
- [x] Update `docs/USER_GUIDE.md` with new commands and filter syntax
- [x] Update `docs/DEPLOYMENT.md` with Groq API setup
- [x] Create end-to-end integration tests
- [x] Performance testing and benchmarks
- [x] Update `roadmap.md` with WS-5 completion

**Deliverables:**
- `CLAUDE.md` - Added LLM Integration Patterns section
- `docs/LLM_INTEGRATION.md` - New comprehensive LLM guide
- `docs/USER_GUIDE.md` - Added LLM Enhancement Commands section
- `docs/DEPLOYMENT.md` - Added Groq API configuration
- `tests/integration/test_llm_integration.py` - 41 integration tests

**Performance Benchmarks:**
| Metric | Value |
|--------|-------|
| Enrichment time per post | 1-3 seconds |
| Tokens per post (average) | 400-600 input, 200-400 output |
| Throughput (with rate limit) | ~10 posts/minute |
| Search response time | <500ms (with enriched data) |

**Acceptance Criteria:**
- [x] All documentation complete and accurate
- [x] Integration tests pass (41 new tests)
- [x] Performance benchmarks documented
- [x] No regressions in existing tests

---

### Phase 5 Gate (RAG Without Vectors Complete)

| Criterion | Target |
|-----------|--------|
| Groq client working | API calls succeed with JSON mode |
| Enrichment pipeline | Posts automatically enriched via Celery |
| Enhanced search | Finds posts via implicit keywords |
| Bot integration | /mode, /enrich, /stats llm work |
| Cost tracking | Token usage and costs monitored |
| Fallback | Metrics-only mode still works |
| Performance | Search < 3 seconds |

**Environment Variables Required:**
```bash
GROQ_API_KEY=          # Required for LLM features
GROQ_MODEL=qwen-qwq-32b
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.1
ENRICHMENT_BATCH_SIZE=10
ENRICHMENT_RATE_LIMIT=10
LLM_DAILY_COST_LIMIT_USD=10.00
```

---


## Phase 6: Codebase Modernization Audit (Week 12+)

**Theme:** Comprehensive review and update of the entire codebase considering all technology updates through December 2025

**Goal:** Ensure all code, dependencies, and patterns align with current best practices and latest stable releases


### Batch 6.1 - Dependency and Security Audit

---

#### WS-6.1: Dependency Modernization

| Field | Value |
|-------|-------|
| **ID** | WS-6.1 |
| **Name** | Dependency Version Audit and Update |
| **Description** | Review all project dependencies against December 2025 releases |
| **Dependencies** | WS-4.3 (Deployment Complete) |
| **Parallel With** | WS-6.2 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Audit `requirements.txt` and `requirements-dev.txt` versions
- [x] Update FastAPI to latest stable (check for breaking changes)
- [x] Update SQLAlchemy and Alembic to latest stable
- [x] Update python-telegram-bot/aiogram to latest stable
- [x] Update Telethon/Pyrogram to latest stable
- [x] Update Celery and Redis clients to latest stable
- [x] Update testing tools (pytest, coverage, etc.)
- [x] Update linting tools (ruff, black, mypy)
- [x] Document breaking changes and migration steps
- [x] Run full test suite after updates

**Acceptance Criteria:**
- [x] All dependencies at December 2025 stable versions
- [x] No known security vulnerabilities (pip-audit clean)
- [x] All tests passing after updates
- [x] Breaking changes documented with migration guide

---

#### WS-6.2: Security Audit

| Field | Value |
|-------|-------|
| **ID** | WS-6.2 |
| **Name** | Security Vulnerability Assessment |
| **Description** | Comprehensive security review of codebase and dependencies |
| **Dependencies** | WS-4.3 (Deployment Complete) |
| **Parallel With** | WS-6.1 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Run pip-audit for dependency vulnerabilities
- [x] Run safety check for known CVEs
- [x] Review secrets management (no hardcoded credentials)
- [x] Audit SQL queries for injection vulnerabilities
- [x] Review Telegram API credential storage
- [x] Check Docker image base security
- [x] Review environment variable handling
- [x] Audit input validation on bot commands
- [x] Review rate limiting implementation

**Acceptance Criteria:**
- [x] No high/critical CVEs in dependencies
- [x] All secrets properly externalized
- [x] Input validation on all user inputs
- [x] Security audit report generated

---

### Batch 6.2 - Code Quality and Patterns

---

#### WS-6.3: Python Modernization

| Field | Value |
|-------|-------|
| **ID** | WS-6.3 |
| **Name** | Python 3.12+ Feature Adoption |
| **Description** | Evaluate and adopt modern Python features and patterns |
| **Dependencies** | WS-6.1 |
| **Parallel With** | WS-6.4 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Update to Python 3.12+ if applicable
- [x] Review and adopt new typing features (TypedDict improvements, etc.)
- [x] Evaluate new async patterns and improvements
- [x] Review dataclass usage vs Pydantic v2 models
- [x] Update exception handling patterns
- [x] Review and optimize context managers
- [x] Evaluate new match/case pattern opportunities
- [x] Review str formatting (f-strings optimization)

**Acceptance Criteria:**
- [x] Codebase uses modern Python idioms
- [x] Type hints comprehensive and using latest syntax
- [x] Code passes mypy strict mode
- [x] Performance benchmarks maintained or improved

---

#### WS-6.4: API and Database Review

| Field | Value |
|-------|-------|
| **ID** | WS-6.4 |
| **Name** | API Design and Database Optimization |
| **Description** | Review FastAPI patterns and database query optimization |
| **Dependencies** | WS-6.1 |
| **Parallel With** | WS-6.3 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Review FastAPI router organization
- [x] Update Pydantic models to v2 patterns
- [x] Audit database indexes for query patterns
- [x] Review and optimize N+1 query patterns
- [x] Evaluate PostgreSQL 16+ features for applicability
- [x] Review Redis usage patterns and key expiry
- [x] Audit Celery task patterns and error handling
- [x] Review connection pooling configuration

**Acceptance Criteria:**
- [x] API response times within targets
- [x] Database queries optimized
- [x] Connection pools properly configured
- [x] Celery tasks properly retrying on failure

---

### Batch 6.3 - Infrastructure and Documentation

---

#### WS-6.5: Infrastructure Modernization

| Field | Value |
|-------|-------|
| **ID** | WS-6.5 |
| **Name** | Docker and CI/CD Updates |
| **Description** | Update containerization and CI/CD to latest practices |
| **Dependencies** | WS-6.3, WS-6.4 |
| **Parallel With** | WS-6.6 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Update Docker base images to latest stable
- [x] Review multi-stage build optimization
- [x] Update docker-compose to Compose V2 syntax if needed
- [x] Review GitHub Actions workflow versions
- [x] Update CI dependencies caching strategy
- [x] Review Render.com configuration for new features
- [x] Update Makefile targets as needed

**Acceptance Criteria:**
- [x] Docker images build successfully
- [x] CI pipeline runs efficiently
- [x] Deployment process unchanged or improved

---

#### WS-6.6: Documentation Refresh

| Field | Value |
|-------|-------|
| **ID** | WS-6.6 |
| **Name** | Documentation Update |
| **Description** | Update all documentation to reflect changes |
| **Dependencies** | WS-6.3, WS-6.4 |
| **Parallel With** | WS-6.5 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-28 |
| **Completed** | 2025-12-28 |

**Tasks:**
- [x] Update CLAUDE.md with any new patterns
- [x] Update README.md with version requirements
- [x] Update DEPLOYMENT.md with new configurations
- [x] Update API documentation if applicable
- [x] Create CHANGELOG.md entry for modernization phase
- [x] Update requirements documentation

**Acceptance Criteria:**
- [x] All documentation reflects current state
- [x] Version requirements clearly stated
- [x] Breaking changes documented

---

### Batch 6.4 - Telegram Bot Evaluation and Enhancement

---

#### WS-6.7: Telegram Bot Implementation Audit

| Field | Value |
|-------|-------|
| **ID** | WS-6.7 |
| **Name** | Telegram Bot Implementation Evaluation |
| **Description** | Comprehensive review of current bot implementation against best practices |
| **Dependencies** | WS-6.1, WS-6.2 |
| **Parallel With** | WS-6.8 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-29 |
| **Completed** | 2025-12-29 |

**Tasks:**
- [x] Review python-telegram-bot/aiogram usage patterns
- [x] Evaluate current command handler architecture
- [x] Audit conversation flow and state management
- [x] Review error handling in bot commands
- [x] Assess bot response formatting and UX
- [x] Evaluate inline keyboard implementations
- [x] Review callback query handling patterns
- [x] Audit message size and rate limit handling
- [x] Review webhook vs polling configuration

**Acceptance Criteria:**
- [x] Complete audit report of current bot implementation
- [x] List of improvement opportunities identified
- [x] Priority ranking of enhancements
- [x] Compatibility assessment with latest library versions

---

#### WS-6.8: Bot Library Modernization

| Field | Value |
|-------|-------|
| **ID** | WS-6.8 |
| **Name** | Telegram Bot Library Update |
| **Description** | Update bot library to latest stable and adopt new features |
| **Dependencies** | WS-6.1, WS-6.2 |
| **Parallel With** | WS-6.7 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-29 |
| **Completed** | 2025-12-29 |

**Tasks:**
- [x] Update to latest python-telegram-bot or aiogram version
- [x] Migrate deprecated API calls to new patterns
- [x] Adopt new async/await patterns if applicable
- [x] Update handler decorators to current syntax
- [x] Review and update bot configuration approach
- [x] Update application lifecycle management
- [x] Verify MTProto API RSA public key connection for secure server authentication
- [x] Test all commands after library update
- [x] Document breaking changes and migrations

**Acceptance Criteria:**
- [x] Bot library at December 2025 stable version
- [x] All deprecated patterns replaced
- [x] MTProto RSA public key verification properly configured
- [x] All commands functioning after update
- [x] Migration guide documented

---

#### WS-6.9: Bot Feature Enhancement

| Field | Value |
|-------|-------|
| **ID** | WS-6.9 |
| **Name** | Bot Functionality Improvements |
| **Description** | Implement improvements identified in audit |
| **Dependencies** | WS-6.7, WS-6.8 |
| **Parallel With** | None |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2025-12-29 |
| **Completed** | 2025-12-29 |

**Tasks:**
- [x] Improve command response formatting
- [x] Enhance inline keyboard navigation
- [x] Add command aliases for common operations (/h, /ch, /s, /e, /t)
- [x] Improve error messages and user feedback
- [x] Optimize pagination for search results
- [x] Add progress indicators for long operations (typing action)
- [x] Improve help command with examples and Quick Start
- [x] Add input validation improvements
- [x] Review and enhance accessibility of responses

**Acceptance Criteria:**
- [x] Improved user experience documented
- [x] All enhancements tested (28 new tests, 844 total)
- [x] User-facing changes documented in help
- [x] Performance maintained or improved

---

#### WS-6.10: Bot Testing and Documentation

| Field | Value |
|-------|-------|
| **ID** | WS-6.10 |
| **Name** | Bot Testing Suite and Documentation Update |
| **Description** | Comprehensive testing of bot functionality and documentation refresh |
| **Dependencies** | WS-6.9 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2025-12-29 |
| **Completed** | 2025-12-29 |

**Tasks:**
- [x] Create/update unit tests for bot handlers
- [x] Add integration tests for bot commands
- [x] Test bot behavior with rate limits
- [x] Test error scenarios and recovery
- [x] Update bot command documentation
- [x] Update user guide with new features
- [x] Document bot configuration options
- [x] Create bot troubleshooting guide

**Acceptance Criteria:**
- [x] Test coverage for all bot commands
- [x] Integration tests passing
- [x] Documentation fully updated
- [x] Troubleshooting guide complete

**Test Summary:**
- 304 bot-related tests passing
- 24 new unit tests for rate limits, errors, edge cases
- 11 new integration tests for workflows
- Coverage: 63% overall, 72-91% for bot handlers

**Documentation Created:**
- `docs/BOT_CONFIGURATION.md` - Complete configuration reference
- `docs/BOT_TROUBLESHOOTING.md` - Detailed troubleshooting guide
- Updated `docs/USER_GUIDE.md` - Added aliases and enhanced troubleshooting

---

### Phase 6 Gate (Modernization Complete)

| Criterion | Target |
|-----------|--------|
| Dependencies updated | All at December 2025 stable |
| Security audit | No high/critical vulnerabilities |
| Tests passing | 100% test suite success |
| Documentation | Fully updated |

---

## Updated Work Stream Quick Reference (Phase 5-6)

| ID | Name | Dependencies | Effort |
|----|------|--------------|--------|
| WS-5.1 | Groq Client Integration | WS-2.4 | S |
| WS-5.2 | Database Schema (Post Enrichment) | WS-5.1 | S |
| WS-5.3 | Enrichment Service Core | WS-5.1, WS-5.2 | M |
| WS-5.4 | Celery Enrichment Tasks | WS-5.3, WS-8.1 | M |
| WS-5.5 | Enhanced Search Service | WS-5.2, WS-5.4 | M |
| WS-5.6 | Bot Integration (LLM) | WS-5.5 | M |
| WS-5.7 | Cost Tracking & Monitoring | WS-5.4, WS-5.6 | S |
| WS-5.8 | Documentation & Testing (LLM) | WS-5.1-5.7 | S |
| WS-6.1 | Dependency Modernization | WS-4.3 | M |
| WS-6.2 | Security Audit | WS-4.3 | M |
| WS-6.3 | Python Modernization | WS-6.1 | M |
| WS-6.4 | API and Database Review | WS-6.1 | M |
| WS-6.5 | Infrastructure Modernization | WS-6.3, WS-6.4 | S |
| WS-6.6 | Documentation Refresh | WS-6.3, WS-6.4 | S |
| WS-6.7 | Telegram Bot Implementation Audit | WS-6.1, WS-6.2 | M |
| WS-6.8 | Bot Library Modernization | WS-6.1, WS-6.2 | M |
| WS-6.9 | Bot Feature Enhancement | WS-6.7, WS-6.8 | M |
| WS-6.10 | Bot Testing and Documentation | WS-6.9 | S |

---

## Updated Timeline Summary

| Phase | Duration | End State |
|-------|----------|-----------|
| Phase 1: Bot + Foundation | 3 weeks | Bot running, channels managed, content collected |
| Phase 2: Search + Ranking | 3 weeks | **MVP** - Working search with metrics |
| Phase 3: Enhanced Features | 2 weeks | Topics, templates, polish |
| Phase 4: Render.com Deployment | 1 week | **PRODUCTION** - Bot deployed on Render.com |
| Phase 5: LLM (RAG Without Vectors) | 2-3 weeks | Groq/Qwen3 enrichment, enhanced search |
| Phase 6: Codebase Modernization | 2-3 weeks | December 2025 technology refresh + Bot enhancement |
| **Total (with Modernization)** | **13-14 weeks** | Full implementation with modern stack and enhanced bot |
 

## Critical Path

```
[WS-1.1: Infrastructure] + [WS-1.2: Database]
        |
        v
[WS-1.3: Bot Foundation] + [WS-1.4: Telegram API]
        |
        v
[WS-1.5: Channel Mgmt] + [WS-1.6: Content Pipeline]
        |
        v
[WS-2.1: Metrics] + [WS-2.2: Search]
        |
        v
[WS-2.3: Ranking]
        |
        v
[WS-2.4: Search Commands] + [WS-2.5: Export]
        |
        v
     [MVP READY]
        |
        v
[WS-3.1: Topics] + [WS-3.2: Advanced Channels]
        |
        v
[WS-3.3: Polish]
        |
        v
   [FULL RELEASE]
        |
        v
[WS-4.1: Render Config] -> [WS-4.2: Prod Env] -> [WS-4.3: Deploy Docs]
        |
        v
  [PRODUCTION DEPLOYED]
        |
        v
[WS-5.1: Groq Client] -> [WS-5.2: DB Schema]
        |
        v
[WS-5.3: Enrichment Service]
        |
        v
[WS-5.4: Celery Tasks]
        |
        v
[WS-5.5: Enhanced Search]
        |
        v
[WS-5.6: Bot Integration]
        |
        v
[WS-5.7: Cost Tracking] + [WS-5.8: Docs & Testing]
        |
        v
  [RAG WITHOUT VECTORS COMPLETE]
        |
        v
[WS-6.1: Dependencies] + [WS-6.2: Security Audit]
        |
        v
[WS-6.3: Python Modern] + [WS-6.4: API/DB Review]
        |
        v
[WS-6.5: Infrastructure] + [WS-6.6: Documentation]
        |
        v
[WS-6.7: Bot Audit] + [WS-6.8: Bot Library Update]
        |
        v
[WS-6.9: Bot Enhancement]
        |
        v
[WS-6.10: Bot Testing & Docs]
        |
        v
  [MODERNIZATION COMPLETE]
        |
        v
[WS-7.1: Bot DI Bug Fix] -> [WS-7.2] -> [WS-7.3] -> [WS-7.4]
        |
        v
  [BUG FIXES COMPLETE]
        |
        v
[WS-8.1: Celery Tasks] + [WS-8.2: Resume Tracking]
        |
        v
  [CONTENT COLLECTION COMPLETE]
        |
        v
[WS-9.1: Menu Button] + [WS-9.2: Sync Command]
        |
        v
  [BOT UX IMPROVEMENTS COMPLETE]
```

---

## Phase 7: Critical Bug Fixes (Week 13)

**Theme:** Fix critical bugs blocking core functionality

**Goal:** Ensure channel management commands work correctly with proper dependency injection

### Batch 7.1 (Current) - Critical Bug Fix

---

#### WS-7.1: Bot Service Dependency Injection Bug Fix

| Field | Value |
|-------|-------|
| **ID** | WS-7.1 |
| **Name** | Fix Bot Service Dependency Injection |
| **Description** | Fix the bug where channel_service and db_session_factory are not properly injected into bot_data, causing /addchannel to fail |
| **Dependencies** | WS-6.10 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Tasks:**
- [x] Add startup validation in `__main__.py` to check required vs optional services
- [x] Log clear warning at startup if Telegram API credentials are missing
- [x] Update `channel_handlers.py` to provide better error messages indicating configuration issues
- [x] Add environment variable check at bot startup with helpful error message
- [x] Add unit tests for service injection scenarios
- [x] Update documentation with required environment variables for channel commands

**Acceptance Criteria:**
- [x] /addchannel works when TELEGRAM_API_ID and TELEGRAM_API_HASH are configured
- [x] Clear error message at startup if required credentials are missing
- [x] Helpful error message to user if they try to use channel commands without proper config
- [x] Unit tests verify dependency injection behavior
- [x] Documentation updated with required environment variables

---

#### WS-7.2: TelethonClient Auto-Connect Bug Fix

| Field | Value |
|-------|-------|
| **ID** | WS-7.2 |
| **Name** | Fix TelethonClient Not Connected Bug |
| **Description** | Fix TelethonClient to auto-connect when API methods are called |
| **Dependencies** | WS-7.1 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Tasks:**
- [x] Write failing test reproducing the connection bug
- [x] Fix TelethonClient to auto-connect when get_channel is called
- [x] Fix TelethonClient to auto-connect when get_messages is called
- [x] Update devlog with fix details

**Acceptance Criteria:**
- [x] /addchannel command successfully validates real public channels
- [x] Client auto-connects when API calls require connection
- [x] All existing tests pass

---

#### WS-7.3: Search Service Injection Bug Fix

| Field | Value |
|-------|-------|
| **ID** | WS-7.3 |
| **Name** | Fix Search Service Dependency Injection Bug |
| **Description** | Create and inject search service into bot application |
| **Dependencies** | WS-7.1 |
| **Parallel With** | WS-7.2 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Tasks:**
- [x] Create search service factory function in __main__.py
- [x] Add search service to log_service_status() for startup visibility
- [x] Inject search service into create_bot_from_env() call
- [x] Update search_handlers.py error message to indicate configuration issue
- [x] Add unit tests for search service injection scenarios

**Acceptance Criteria:**
- [x] /search command works when database is properly configured
- [x] Clear status message shown at startup about search service availability
- [x] Helpful error message to user if search commands used without proper config
- [x] Unit tests verify search service dependency injection behavior

---

#### WS-7.4: TopicService Injection Bug Fix

| Field | Value |
|-------|-------|
| **ID** | WS-7.4 |
| **Name** | Fix TopicService Dependency Injection Bug |
| **Description** | Create and inject topic service into bot application so /savetopic, /topics, /topic, /deletetopic commands work |
| **Dependencies** | WS-7.3 |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Bug Report:**
All topic-related commands (/savetopic, /topics, /topic, /deletetopic) are broken because TopicService is not injected into bot_data.

**Required Pattern (Service Injection Standard):**
All services MUST follow this pattern:
1. Create factory function: `create_<service>_service() -> Service | None`
2. Log at startup via `log_service_status()`
3. Inject into application via `create_bot_from_env()`

**Tasks:**
- [x] Create `create_topic_service()` factory function in `__main__.py`
- [x] Add topic service to `log_service_status()` for startup visibility
- [x] Inject topic service into `create_bot_from_env()` call
- [x] Update topic_handlers.py error messages to indicate configuration issue
- [x] Add unit tests for topic service injection scenarios
- [x] Verify all topic commands work after fix

**Affected Files:**
- `src/tnse/bot/__main__.py`
- `src/tnse/bot/topic_handlers.py`
- `src/tnse/bot/application.py`

**Acceptance Criteria:**
- [x] /savetopic command works correctly
- [x] /topics command lists saved topics
- [x] /topic <name> runs saved topic search
- [x] /deletetopic command works correctly
- [x] Clear status message shown at startup about topic service availability
- [x] Unit tests verify topic service dependency injection behavior

---

### Phase 7 Gate

| Criterion | Target |
|-----------|--------|
| Channel commands working | /addchannel, /removechannel work correctly |
| Search commands working | /search returns results |
| Topic commands working | /savetopic, /topics, /topic, /deletetopic work correctly |
| Configuration validated | Startup checks for required env vars |
| Tests passing | All dependency injection tests pass |
| Documentation updated | Troubleshooting guide addresses these issues |

**Service Injection Standard (MUST follow for all services):**
1. Factory function created: `create_<service>_service()`
2. Logged at startup via `log_service_status()`
3. Injected into application via `create_bot_from_env()`

---

## Phase 8: Content Collection Pipeline Fixes (Week 14)

**Theme:** Fix critical issues with automatic content collection

**Goal:** Make Celery tasks actually collect content and track progress to avoid re-fetching

### Batch 8.1 (Current) - Parallel Execution

---

#### WS-8.1: Wire Celery Tasks to ContentCollector

| Field | Value |
|-------|-------|
| **ID** | WS-8.1 |
| **Name** | Wire Celery Tasks to ContentCollector |
| **Description** | Celery tasks currently return hardcoded zeros - wire them to actually call ContentCollector |
| **Dependencies** | WS-7.4 |
| **Parallel With** | WS-8.2 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Bug Report:**
Celery tasks are stubs that return hardcoded zeros. No automatic content collection is happening.

**Tasks:**
- [x] Audit current Celery task implementations to identify stub code
- [x] Create ContentCollector service factory function
- [x] Wire `collect_channel_content` task to ContentCollector.collect()
- [x] Wire `collect_all_channels` task to iterate channels and call ContentCollector
- [x] Add proper error handling and retry logic
- [x] Add metrics/logging for collection job status
- [x] Add unit tests for wired Celery tasks
- [x] Integration test: verify content actually stored in database after collection

**Affected Files:**
- `src/tnse/pipeline/tasks.py`
- `src/tnse/pipeline/collector.py`
- `src/tnse/pipeline/storage.py`

**Acceptance Criteria:**
- [x] Celery beat scheduler triggers content collection every 15-30 minutes
- [x] Content actually fetched from Telegram channels
- [x] Content stored in database with proper schema
- [x] Collection metrics logged (channels processed, posts collected, errors)
- [x] Failed collections retry with exponential backoff

---

#### WS-8.2: Resume-from-Last-Point Tracking

| Field | Value |
|-------|-------|
| **ID** | WS-8.2 |
| **Name** | Resume-from-Last-Point Tracking |
| **Description** | Track last collected message ID per channel to avoid re-fetching same content |
| **Dependencies** | WS-8.1 |
| **Parallel With** | WS-8.1 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |
| **Assigned** | Claude Code |

**Bug Report:**
Currently re-fetches same messages each collection cycle because there's no tracking of what was already collected.

**Tasks:**
- [x] Add `last_collected_message_id` column to channels table (migration)
- [x] Update ContentCollector to read last_collected_message_id before fetching
- [x] Pass min_id parameter to Telegram API to fetch only new messages
- [x] Update last_collected_message_id after successful collection
- [x] Handle edge cases: channel reset, message deletion, gaps
- [x] Add unit tests for resume tracking logic
- [x] Integration test: verify only new messages collected on second run

**Affected Files:**
- `alembic/versions/add_last_collected_message_id.py` (new migration)
- `src/tnse/db/models.py` (updated Channel model)
- `src/tnse/pipeline/collector.py` (updated collect_channel_messages)
- `tests/unit/pipeline/test_resume_tracking.py` (new)
- `tests/integration/test_resume_tracking_integration.py` (new)

**Acceptance Criteria:**
- [x] First collection fetches all messages in 24-hour window
- [x] Subsequent collections only fetch new messages since last run
- [x] Database stores last_collected_message_id per channel
- [x] Collection time significantly reduced on repeat runs
- [x] Edge cases handled gracefully (no crashes on gaps/deletions)

---

### Batch 8.2 (After WS-7.4 Complete) - Documentation Sync

---

#### WS-8.3: Roadmap Sync

| Field | Value |
|-------|-------|
| **ID** | WS-8.3 |
| **Name** | Roadmap Sync |
| **Description** | Ensure root roadmap.md and plans/roadmap.md are synchronized |
| **Dependencies** | None |
| **Parallel With** | None |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |

**Tasks:**
- [x] Read both roadmap.md (root) and plans/roadmap.md
- [x] Fix WS-7.1 status inconsistency (was "Not Started" in root, "Complete" in plans)
- [x] Add WS-7.2, WS-7.3, WS-7.4, WS-7.5  to root roadmap
- [x] Add WS-8.1, WS-8.2, WS-8.3 to both roadmaps
- [x] Document service injection standard in both roadmaps
- [x] Update plans/roadmap.md with new work streams

**Acceptance Criteria:**
- [x] Both roadmaps show same status for all work streams
- [x] All new work streams (WS-7.4, WS-8.x) documented in both files
- [x] Service injection standard documented

---

### Phase 8 Gate

| Criterion | Target |
|-----------|--------|
| Content collection working | Celery tasks actually collect content |
| Resume tracking | Only new messages fetched |
| Roadmaps synchronized | Both files show consistent state |
| Database populated | Posts table has real content |

---

## Phase 9: Bot UX Improvements (Week 15)

**Theme:** Improve bot discoverability and add manual sync controls

**Goal:** Make the bot more user-friendly with a menu button and allow admins to manually trigger content sync

### Batch 9.1 (Current) - Parallel Execution

---

#### WS-9.1: Bot Menu Button

| Field | Value |
|-------|-------|
| **ID** | WS-9.1 |
| **Name** | Bot Menu Button |
| **Description** | Add a menu button to the Telegram bot interface for better UX and command discoverability |
| **Dependencies** | WS-8.3 |
| **Parallel With** | WS-9.2 |
| **Effort** | S |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |
| **Assigned** | Claude Code |

**Tasks:**
- [x] Research Telegram Bot API setMyCommands and MenuButton options
- [x] Configure bot commands list via BotFather or API
- [x] Add menu button to bot interface for command discoverability
- [x] Group commands by category (Channel, Search, Topic, Export, Settings)
- [x] Add unit tests for menu button setup
- [x] Update bot documentation with menu button usage

**Deliverables:**
- Menu button configuration in bot startup
- Grouped command list
- Updated documentation

**Acceptance Criteria:**
- [x] Menu button appears in Telegram bot interface
- [x] Clicking menu button shows available commands
- [x] Commands are organized in logical groups
- [x] Documentation updated

---

#### WS-9.2: Manual Channel Sync Command

| Field | Value |
|-------|-------|
| **ID** | WS-9.2 |
| **Name** | Manual Channel Sync Command |
| **Description** | Add a new bot command that allows users/admins to manually trigger channel data synchronization using Celery tasks |
| **Dependencies** | WS-8.1 (Celery tasks wired) |
| **Parallel With** | WS-9.1 |
| **Effort** | M |
| **Status** | Complete |
| **Started** | 2026-01-04 |
| **Completed** | 2026-01-04 |
| **Assigned** | Claude Code |

**Tasks:**
- [x] Add `/sync` command to trigger content collection for all channels
- [x] Add `/sync @channel` command to sync specific channel
- [x] Wire command to call `collect_channel_content` Celery task
- [x] Add progress feedback (typing indicator, status messages)
- [x] Restrict command to admin users (configurable whitelist)
- [x] Add rate limiting to prevent abuse (max 1 sync per 5 minutes)
- [x] Add unit tests for sync command handlers
- [x] Add integration test for sync workflow

**Bot Commands:**
```
/sync - Trigger content collection for all monitored channels
/sync @channel - Trigger content collection for specific channel
```

**Deliverables:**
- `src/tnse/bot/sync_handlers.py` (new file)
- Unit tests for sync handlers
- Integration test for sync workflow

**Acceptance Criteria:**
- [x] /sync command triggers content collection for all monitored channels
- [x] /sync @channel syncs specific channel only
- [x] User receives progress feedback during sync
- [x] Rate limiting prevents abuse (max 1 sync per 5 minutes)
- [x] Only authorized users can trigger sync
- [x] Tests verify sync command behavior

---

### Phase 9 Gate

| Criterion | Target |
|-----------|--------|
| Menu button working | Commands visible in bot menu |
| Sync command working | /sync triggers Celery tasks |
| Rate limiting | Abuse prevention in place |
| Tests passing | All new tests pass |

---

## Timeline Summary

| Phase | Duration | End State |
|-------|----------|-----------|
| Phase 1: Bot + Foundation | 3 weeks | Bot running, channels managed, content collected |
| Phase 2: Search + Ranking | 3 weeks | **MVP** - Working search with metrics |
| Phase 3: Enhanced Features | 2 weeks | Topics, templates, polish |
| Phase 4: Render.com Deployment | 1 week | **PRODUCTION** - Bot deployed on Render.com |
| Phase 5: LLM (RAG Without Vectors) | 2-3 weeks | Groq/Qwen3 enrichment, enhanced search |
| Phase 6: Codebase Modernization | 2-3 weeks | December 2025 technology refresh |
| Phase 7: Critical Bug Fixes | 1 week | Dependency injection fixes (channel, search, topic services) |
| Phase 8: Content Collection Fixes | 1-2 weeks | Wire Celery tasks, resume tracking |
| Phase 9: Bot UX Improvements | 1 week | Menu button, manual sync command |
| **Total (without LLM)** | **12-13 weeks** | Full production deployment with UX improvements |
| **Total (with LLM)** | **14-15 weeks** | Full implementation with AI |

---

## Work Stream Quick Reference

| ID | Name | Dependencies | Effort | Status |
|----|------|--------------|--------|--------|
| WS-1.1 | Infrastructure Setup | None | M | Complete |
| WS-1.2 | Database Schema | None | S | Complete |
| WS-1.3 | Telegram Bot Foundation | WS-1.1 | M | Complete |
| WS-1.4 | Telegram API Integration | WS-1.1, WS-1.2 | M | Complete |
| WS-1.5 | Channel Management (Bot) | WS-1.3, WS-1.4 | S | Complete |
| WS-1.6 | Content Collection Pipeline | WS-1.4, WS-1.2 | M | Complete |
| WS-2.1 | Engagement Metrics | WS-1.6 | M | Complete |
| WS-2.2 | Keyword Search Engine | WS-1.6 | M | Complete |
| WS-2.3 | Ranking Algorithm | WS-2.1, WS-2.2 | S | Complete |
| WS-2.4 | Search Bot Commands | WS-2.3, WS-1.3 | M | Complete |
| WS-2.5 | Export Functionality | WS-2.4 | S | Complete |
| WS-3.1 | Saved Topics | WS-2.4 | S | Complete |
| WS-3.2 | Advanced Channel Management | WS-1.5 | S | Complete |
| WS-3.3 | Polish and Testing | All | M | Complete |
| WS-4.1 | Render.com Configuration | WS-3.3 | M | Complete |
| WS-4.2 | Production Environment Configuration | WS-4.1 | S | Complete |
| WS-4.3 | Deployment Documentation | WS-4.1, WS-4.2 | S | Complete |
| WS-5.1 | Groq Client Integration | WS-2.4 | S | Complete |
| WS-5.2 | Database Schema (Post Enrichment) | WS-5.1 | S | Complete |
| WS-5.3 | Enrichment Service Core | WS-5.1, WS-5.2 | M | Complete |
| WS-5.4 | Celery Enrichment Tasks | WS-5.3, WS-8.1 | M | Complete |
| WS-5.5 | Enhanced Search Service | WS-5.2, WS-5.4 | M | Complete |
| WS-5.6 | Bot Integration (LLM) | WS-5.5 | M | Not Started |
| WS-5.7 | Cost Tracking & Monitoring | WS-5.4, WS-5.6 | S | Not Started |
| WS-5.8 | Documentation & Testing (LLM) | WS-5.1-5.7 | S | Complete |
| WS-6.1 | Dependency Modernization | WS-4.3 | M | Complete |
| WS-6.2 | Security Audit | WS-4.3 | M | Complete |
| WS-6.3 | Python Modernization | WS-6.1 | M | Complete |
| WS-6.4 | API and Database Review | WS-6.1 | M | Complete |
| WS-6.5 | Infrastructure Modernization | WS-6.3, WS-6.4 | S | Complete |
| WS-6.6 | Documentation Refresh | WS-6.3, WS-6.4 | S | Complete |
| WS-6.7 | Telegram Bot Implementation Audit | WS-6.1, WS-6.2 | M | Complete |
| WS-6.8 | Bot Library Modernization | WS-6.1, WS-6.2 | M | Complete |
| WS-6.9 | Bot Feature Enhancement | WS-6.7, WS-6.8 | M | Complete |
| WS-6.10 | Bot Testing and Documentation | WS-6.9 | S | Complete |
| WS-7.1 | Bot Service Dependency Injection Bug Fix | WS-6.10 | S | Complete |
| WS-7.2 | TelethonClient Auto-Connect Bug Fix | WS-7.1 | S | Complete |
| WS-7.3 | Search Service Injection Bug Fix | WS-7.1 | S | Complete |
| WS-7.4 | TopicService Injection Bug Fix | WS-7.3 | S | Complete |
| WS-8.1 | Wire Celery Tasks to ContentCollector | WS-7.4 | M | Complete |
| WS-8.2 | Resume-from-Last-Point Tracking | WS-8.1 | M | Complete |
| WS-8.3 | Roadmap Sync | None | S | Complete |
| WS-9.1 | Bot Menu Button | WS-8.3 | S | Complete |
| WS-9.2 | Manual Channel Sync Command | WS-8.1 | M | Complete |

---

## Removed from Original Roadmap

The following were removed to simplify:

| Removed | Reason |
|---------|--------|
| WS-1.3: Authentication Service | Not needed - Telegram handles identity |
| WS-1.6: Frontend Project Setup | Not needed - bot is the UI |
| WS-1.10: Channel Management UI | Not needed - bot commands instead |
| WS-2.4: Search Results UI | Not needed - bot formatting instead |
| WS-2.5: Search Interface (Web) | Not needed - bot is the interface |
| WS-3.3: Mode Switching UI | Simplified to bot command |
| WS-3.7: Cluster Display UI | Not needed |
| All frontend work streams | Bot-only architecture |
| API Gateway complexity | Bot calls services directly |
| OAuth/JWT | Telegram user IDs for access control |

---

## Access Control (Simple)

Instead of authentication, use Telegram user ID whitelist:

```python
ALLOWED_USERS = [123456789, 987654321]  # Telegram user IDs

async def check_access(update):
    if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Access denied.")
        return False
    return True
```

Set `ALLOWED_USERS = []` for open access, or list specific user IDs for restricted access.

---

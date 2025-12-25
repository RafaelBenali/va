# Telegram News Search Bot - Implementation Roadmap

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 2.0 |
| Date | 2025-12-25 |
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
| **Status** | In Progress |
| **Started** | 2025-12-25 |

**Tasks:**
- [ ] Set up python-telegram-bot or aiogram
- [ ] Register bot with BotFather
- [ ] Implement /start with welcome message
- [ ] Implement /help command
- [ ] Implement /settings command
- [ ] Add optional user whitelist (restrict to specific Telegram user IDs)
- [ ] Secure bot token storage
- [ ] Set up webhook or polling

**Deliverables:**
- Telegram bot application
- Command handlers
- Bot configuration

**Acceptance Criteria:**
- [ ] Bot responds to /start and /help
- [ ] Bot token securely stored (not in code)
- [ ] Optional whitelist working

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

**Tasks:**
- [ ] Set up Telethon/Pyrogram client
- [ ] Implement channel validation (public/accessible)
- [ ] Create channel metadata fetcher
- [ ] Implement message history retrieval (24 hours)
- [ ] Handle rate limiting with backoff
- [ ] Create Telegram API abstraction layer
- [ ] Store credentials encrypted

**Deliverables:**
- `TelegramClient` abstraction
- Channel validation service
- Message retrieval service

**Acceptance Criteria:**
- [ ] Can validate public channels
- [ ] Retrieves channel metadata
- [ ] Fetches 24-hour message history
- [ ] Handles rate limits gracefully

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

**Tasks:**
- [ ] Implement /addchannel @username command
- [ ] Implement /removechannel @username command
- [ ] Implement /channels (list all monitored)
- [ ] Implement /channelinfo @username (show metadata)
- [ ] Add validation feedback in bot messages
- [ ] Show channel health status

**Bot Commands:**
```
/addchannel @telegram_channel - Add channel to monitor
/removechannel @telegram_channel - Remove from monitoring
/channels - List all monitored channels
/channelinfo @telegram_channel - Show channel details
```

**Acceptance Criteria:**
- [ ] Can add channels via bot command
- [ ] Can remove channels via bot command
- [ ] Channel list displays correctly
- [ ] Validation errors shown in bot response

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

**Tasks:**
- [ ] Set up Celery/RQ with Redis
- [ ] Create content collection job
- [ ] Implement 24-hour content window
- [ ] Extract text content
- [ ] Extract media metadata
- [ ] Detect forwarded messages
- [ ] Store in database
- [ ] Schedule periodic runs (every 15-30 min)

**Deliverables:**
- Background job scheduler
- Content collection worker
- Media metadata extractor

**Acceptance Criteria:**
- [ ] Collects 24-hour content
- [ ] Extracts text, image, video metadata
- [ ] Runs automatically on schedule
- [ ] Handles failures gracefully

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

**Tasks:**
- [ ] Extract view counts per post
- [ ] Extract individual emoji reaction counts
- [ ] Implement reaction score with configurable weights
- [ ] Calculate relative engagement (engagement / subscribers)
- [ ] Store metrics with timestamps

**Reaction Score Formula:**
```python
reaction_score = sum(emoji_count * emoji_weight for emoji in reactions)
relative_engagement = (views + reaction_score) / subscriber_count
```

**Acceptance Criteria:**
- [ ] View counts extracted
- [ ] Emoji counts stored separately
- [ ] Scores calculated correctly

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

**Tasks:**
- [ ] Implement tokenization for Russian/English/Ukrainian
- [ ] Set up PostgreSQL full-text search (or simple Elasticsearch)
- [ ] Handle Cyrillic normalization
- [ ] Search within 24-hour window
- [ ] Support multiple keywords
- [ ] Add result caching

**Acceptance Criteria:**
- [ ] Keyword search returns matches
- [ ] Russian and English work
- [ ] Search response < 3 seconds

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

**Tasks:**
- [ ] Create ranking service
- [ ] Implement combined score: engagement * recency
- [ ] Add sorting options (views, reactions, combined)
- [ ] Add recency boost for newer content

**Ranking Formula:**
```python
combined_score = relative_engagement * (1.0 - hours_since_post / 24)
```

**Acceptance Criteria:**
- [ ] Results ranked by combined score
- [ ] Sorting options work
- [ ] Ranking is consistent

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

**Tasks:**
- [ ] Implement /search <query> command
- [ ] Format results with metrics display
- [ ] Show emoji reaction breakdown
- [ ] Implement inline keyboard pagination
- [ ] Add "More results" button
- [ ] Respect Telegram message length limits
- [ ] Add Telegram links to original posts

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
- [ ] /search returns ranked results
- [ ] Pagination works via buttons
- [ ] Metrics displayed clearly
- [ ] Links work

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

**Tasks:**
- [ ] Implement /export command after search
- [ ] Generate CSV with results
- [ ] Generate JSON with results
- [ ] Send file via bot
- [ ] Include Telegram links

**Acceptance Criteria:**
- [ ] /export sends CSV file
- [ ] File contains all result data
- [ ] Links included

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

**Tasks:**
- [ ] Implement /savetopic <name> command
- [ ] Implement /topics command (list saved)
- [ ] Implement /topic <name> (run saved search)
- [ ] Implement /deletetopic <name>
- [ ] Create pre-built templates (corruption, politics, tech, etc.)
- [ ] Implement /templates command

**Bot Commands:**
```
/savetopic corruption_news - Save current search config
/topics - List your saved topics
/topic corruption_news - Run saved topic search
/deletetopic corruption_news - Delete saved topic
/templates - Show pre-built templates
```

**Acceptance Criteria:**
- [ ] Topics saved and retrieved
- [ ] Templates work
- [ ] Quick access via commands

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

**Tasks:**
- [ ] Implement /import command (accept file with channel list)
- [ ] Validate all channels in batch
- [ ] Report import results
- [ ] Implement /health command (show channel statuses)
- [ ] Alert on channel issues (rate limited, removed)

**Acceptance Criteria:**
- [ ] Bulk import works
- [ ] Health status visible
- [ ] Issues reported

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

**Tasks:**
- [ ] End-to-end integration testing
- [ ] Performance testing (< 3 second response)
- [ ] Bug fixing
- [ ] Write user documentation (bot commands)
- [ ] Create deployment guide

**Acceptance Criteria:**
- [ ] All commands work reliably
- [ ] Performance targets met
- [ ] Documentation complete

---

### Phase 3 Gate

| Criterion | Target |
|-----------|--------|
| Saved topics | Save/load works |
| Templates | Pre-built available |
| Bulk import | File import works |
| Stability | No critical bugs |

---

## Phase 4: LLM Enhancement (Weeks 9-10) - OPTIONAL

**Theme:** AI-powered features (if budget/need exists)

**Goal:** Add semantic understanding - this is optional!

**Note:** This phase is entirely optional. The system works great with metrics-only search. Only implement if you need semantic topic analysis.

### Batch 4.1 (Week 9)

---

#### WS-4.1: LLM Integration

| Field | Value |
|-------|-------|
| **ID** | WS-4.1 |
| **Name** | LLM Provider Integration |
| **Description** | Connect to OpenAI/Anthropic for semantic analysis |
| **Dependencies** | WS-2.4 (Search) |
| **Parallel With** | None |
| **Effort** | M |

**Tasks:**
- [ ] Create LLM provider abstraction
- [ ] Implement OpenAI client
- [ ] Implement Anthropic client (optional)
- [ ] Add API key secure storage
- [ ] Implement cost tracking
- [ ] Add graceful fallback to metrics-only

**Acceptance Criteria:**
- [ ] LLM calls work
- [ ] Fallback to metrics-only works
- [ ] Costs tracked

---

#### WS-4.2: Semantic Topic Analysis

| Field | Value |
|-------|-------|
| **ID** | WS-4.2 |
| **Name** | LLM-Powered Topic Categorization |
| **Description** | Use LLM to categorize posts by topic |
| **Dependencies** | WS-4.1 (LLM Integration) |
| **Parallel With** | None |
| **Effort** | M |

**Tasks:**
- [ ] Create topic categorization prompts
- [ ] Analyze posts for topic tags
- [ ] Store topic tags per post
- [ ] Add topic filter to search
- [ ] Implement /mode command (llm/metrics-only toggle)
- [ ] Cache LLM responses

**Acceptance Criteria:**
- [ ] Posts tagged with topics
- [ ] Topic filter works
- [ ] Mode switching works

---

### Phase 4 Gate

| Criterion | Target |
|-----------|--------|
| LLM working | API calls succeed |
| Fallback | Metrics-only still works |
| Topic tagging | Posts categorized |
| Caching | Costs reduced |

---

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
        v (optional)
[WS-4.1: LLM] -> [WS-4.2: Semantic]
```

---

## Timeline Summary

| Phase | Duration | End State |
|-------|----------|-----------|
| Phase 1: Bot + Foundation | 3 weeks | Bot running, channels managed, content collected |
| Phase 2: Search + Ranking | 3 weeks | **MVP** - Working search with metrics |
| Phase 3: Enhanced Features | 2 weeks | Topics, templates, polish |
| Phase 4: LLM (Optional) | 2 weeks | Semantic analysis |
| **Total (without LLM)** | **8 weeks** | Full metrics-only implementation |
| **Total (with LLM)** | **10 weeks** | Full implementation with AI |

---

## Work Stream Quick Reference

| ID | Name | Dependencies | Effort |
|----|------|--------------|--------|
| WS-1.1 | Infrastructure Setup | None | M |
| WS-1.2 | Database Schema | None | S |
| WS-1.3 | Telegram Bot Foundation | WS-1.1 | M |
| WS-1.4 | Telegram API Integration | WS-1.1, WS-1.2 | M |
| WS-1.5 | Channel Management (Bot) | WS-1.3, WS-1.4 | S |
| WS-1.6 | Content Collection Pipeline | WS-1.4, WS-1.2 | M |
| WS-2.1 | Engagement Metrics | WS-1.6 | M |
| WS-2.2 | Keyword Search Engine | WS-1.6 | M |
| WS-2.3 | Ranking Algorithm | WS-2.1, WS-2.2 | S |
| WS-2.4 | Search Bot Commands | WS-2.3, WS-1.3 | M |
| WS-2.5 | Export Functionality | WS-2.4 | S |
| WS-3.1 | Saved Topics | WS-2.4 | S |
| WS-3.2 | Advanced Channel Management | WS-1.5 | S |
| WS-3.3 | Polish and Testing | All | M |
| WS-4.1 | LLM Integration (Optional) | WS-2.4 | M |
| WS-4.2 | Semantic Topic Analysis (Optional) | WS-4.1 | M |

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

*End of Simplified Roadmap*

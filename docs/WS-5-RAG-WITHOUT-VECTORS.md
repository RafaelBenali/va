# WS-5: RAG Without Vectors - Technical Architecture

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 1.0 |
| Date | 2026-01-05 |
| Status | Draft |
| Author | Product-Tech-Lead Agent |
| Scope | Phase 5 Redesign - LLM Post Enrichment with Groq/Qwen3 |

---

## Executive Summary

This document describes the redesigned WS-5 (LLM Integration) work stream to implement a **Python RAG Without Vectors** system. Instead of traditional vector embeddings and semantic search, this approach uses LLM-extracted keywords (both explicit and implicit) to improve search recall while maintaining the existing PostgreSQL full-text search infrastructure.

**Key Innovation:** The `implicit_keywords` field captures concepts, entities, and themes NOT directly in the text but semantically related, enabling "RAG-like" retrieval without vector databases.

---

## Current Architecture Analysis

### Existing Post Storage Schema

```
posts
  - id (UUID)
  - channel_id (UUID, FK)
  - telegram_message_id (BigInteger)
  - published_at (DateTime)
  - is_forwarded (Boolean)
  - forward_from_channel_id (BigInteger, nullable)
  - forward_from_message_id (BigInteger, nullable)
  - created_at, updated_at (TimestampMixin)

post_content
  - id (UUID)
  - post_id (UUID, FK)
  - text_content (Text, nullable)
  - language (String(10), nullable)
  - created_at (DateTime)

engagement_metrics
  - id (UUID)
  - post_id (UUID, FK)
  - view_count, forward_count, reply_count (Integer)
  - reaction_score (Float)
  - relative_engagement (Float)
  - collected_at (DateTime)
```

### Current Search Implementation

The `SearchService` (`src/tnse/search/service.py`) uses PostgreSQL full-text search with:
- `plainto_tsquery` for Russian, English, and simple text configurations
- Searches against `post_content.text_content`
- Orders by `relative_engagement DESC, view_count DESC`
- Supports caching with configurable TTL

### Content Collection Pipeline

The `ContentCollector` (`src/tnse/pipeline/collector.py`) extracts:
- Text content
- Media metadata
- Forwarding information
- Engagement metrics (views, reactions)

**Integration Point:** LLM enrichment should hook into the collection pipeline as an async post-processing step.

---

## Technical Architecture

### Architecture Overview

```
+------------------+     +-------------------+     +------------------+
|  Content         |     |  LLM Enrichment   |     |  PostgreSQL      |
|  Collector       | --> |  Service          | --> |  (Extended       |
|  (existing)      |     |  (new: Groq API)  |     |   Schema)        |
+------------------+     +-------------------+     +------------------+
         |                       |                        |
         v                       v                        v
+------------------+     +-------------------+     +------------------+
|  Post Storage    |     |  Enrichment       |     |  Enhanced        |
|  (existing)      |     |  Queue (Celery)   |     |  Search Service  |
+------------------+     +-------------------+     +------------------+
```

### Key Design Decisions

1. **Non-blocking Enrichment:** LLM enrichment runs asynchronously via Celery tasks - does NOT block content collection
2. **Graceful Fallback:** System works in metrics-only mode when LLM is disabled or fails
3. **Keyword-Based Retrieval:** No vectors - uses PostgreSQL GIN indexes on keyword arrays
4. **Cost Tracking:** Built-in token usage and cost monitoring for Groq API
5. **Structured Output:** Uses Groq's JSON mode for reliable extraction

### LLM Provider: Groq with Qwen3 32B

**Why Groq + Qwen3:**
- Fast inference (low latency for batch processing)
- Cost-effective for high-volume post enrichment
- Qwen3 32B has strong multilingual support (Russian, English, Ukrainian)
- JSON mode for structured output

**Model Configuration:**
```python
GROQ_MODEL = "qwen-qwq-32b"  # or appropriate Qwen3 model ID
GROQ_MAX_TOKENS = 1024
GROQ_TEMPERATURE = 0.1  # Low for consistent extraction
```

---

## Database Schema Changes

### New Table: `post_enrichments`

```sql
CREATE TABLE post_enrichments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,

    -- LLM-extracted fields
    explicit_keywords TEXT[],      -- Words/phrases directly in text
    implicit_keywords TEXT[],      -- Related concepts NOT in text (key differentiator)
    category VARCHAR(100),         -- Primary topic category
    sentiment VARCHAR(20),         -- positive/negative/neutral
    entities JSONB,                -- {people: [], organizations: [], places: []}

    -- Metadata
    model_used VARCHAR(100),       -- e.g., "groq/qwen-qwq-32b"
    token_count INTEGER,           -- Total tokens used
    processing_time_ms INTEGER,    -- Time taken for LLM call
    enriched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_post_enrichments_post UNIQUE (post_id)
);

-- GIN indexes for keyword search
CREATE INDEX ix_post_enrichments_explicit_keywords
    ON post_enrichments USING GIN (explicit_keywords);
CREATE INDEX ix_post_enrichments_implicit_keywords
    ON post_enrichments USING GIN (implicit_keywords);
CREATE INDEX ix_post_enrichments_category
    ON post_enrichments (category);
CREATE INDEX ix_post_enrichments_sentiment
    ON post_enrichments (sentiment);

-- JSONB index for entity search
CREATE INDEX ix_post_enrichments_entities
    ON post_enrichments USING GIN (entities);
```

### SQLAlchemy Model

```python
# src/tnse/db/models.py (new model)

class PostEnrichment(Base, UUIDPrimaryKeyMixin):
    """LLM-enriched metadata for posts.

    Stores extracted keywords, categories, sentiment, and entities
    from LLM analysis of post content.
    """

    __tablename__ = "post_enrichments"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    explicit_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    implicit_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    entities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        backref="enrichment",
    )
```

---

## LLM Enrichment Service

### Prompt Design

```python
ENRICHMENT_PROMPT = """Analyze this Russian/Ukrainian/English Telegram post. Extract structured information.

POST CONTENT:
{text_content}

Extract the following in JSON format:
{{
    "explicit_keywords": ["list of keywords/phrases that appear directly in the text"],
    "implicit_keywords": ["list of related concepts, themes, entities NOT in the text but semantically relevant"],
    "category": "primary topic category (politics, economics, technology, sports, entertainment, health, military, crime, society, other)",
    "sentiment": "positive|negative|neutral",
    "entities": {{
        "people": ["names of people mentioned or implied"],
        "organizations": ["names of organizations, companies, institutions"],
        "places": ["geographic locations mentioned or implied"]
    }}
}}

IMPORTANT for implicit_keywords:
- These are concepts that a reader would associate with this content
- Include related terms, synonyms, broader categories, contextual associations
- Example: If post mentions "iPhone", implicit keywords might include ["Apple", "smartphone", "iOS", "tech gadget"]

Return ONLY valid JSON, no explanations."""
```

### Service Implementation

```python
# src/tnse/llm/enrichment_service.py

@dataclass
class EnrichmentResult:
    """Result of LLM enrichment for a post."""
    explicit_keywords: list[str]
    implicit_keywords: list[str]
    category: str
    sentiment: str
    entities: dict[str, list[str]]
    model_used: str
    token_count: int
    processing_time_ms: int


@dataclass
class EnrichmentService:
    """Service for enriching posts with LLM-extracted metadata."""

    groq_client: AsyncGroq
    model: str = "qwen-qwq-32b"
    max_tokens: int = 1024
    temperature: float = 0.1

    async def enrich_post(
        self,
        text_content: str,
    ) -> EnrichmentResult | None:
        """Extract enrichment metadata from post content."""
        ...

    async def enrich_batch(
        self,
        posts: list[tuple[UUID, str]],  # (post_id, text_content)
        batch_size: int = 10,
    ) -> dict[UUID, EnrichmentResult]:
        """Batch process multiple posts for efficiency."""
        ...
```

---

## Enhanced Search Service

### Keyword-Based Retrieval

The enhanced search will query both original text AND enriched keywords:

```sql
-- Enhanced search query
SELECT
    p.id AS post_id,
    p.channel_id,
    c.username AS channel_username,
    c.title AS channel_title,
    pc.text_content,
    p.published_at,
    p.telegram_message_id,
    COALESCE(em.view_count, 0) AS view_count,
    COALESCE(em.reaction_score, 0.0) AS reaction_score,
    COALESCE(em.relative_engagement, 0.0) AS relative_engagement,
    pe.category,
    pe.sentiment,
    pe.entities
FROM posts p
JOIN channels c ON p.channel_id = c.id
LEFT JOIN post_content pc ON p.id = pc.post_id
LEFT JOIN post_enrichments pe ON p.id = pe.post_id
LEFT JOIN LATERAL (
    SELECT view_count, reaction_score, relative_engagement
    FROM engagement_metrics
    WHERE post_id = p.id
    ORDER BY collected_at DESC
    LIMIT 1
) em ON true
WHERE p.published_at >= :cutoff_time
AND (
    -- Original full-text search
    to_tsvector('russian', COALESCE(pc.text_content, '')) @@
        plainto_tsquery('russian', :search_terms)
    OR to_tsvector('english', COALESCE(pc.text_content, '')) @@
        plainto_tsquery('english', :search_terms)
    OR to_tsvector('simple', COALESCE(pc.text_content, '')) @@
        plainto_tsquery('simple', :search_terms)
    -- NEW: Keyword array search (both explicit and implicit)
    OR :search_keywords && pe.explicit_keywords
    OR :search_keywords && pe.implicit_keywords
)
ORDER BY em.relative_engagement DESC, em.view_count DESC
LIMIT :limit OFFSET :offset
```

### Search with Filters

New search capabilities enabled by enrichment:

```python
async def search(
    self,
    query: str,
    hours: int = 24,
    category: str | None = None,     # NEW: Filter by category
    sentiment: str | None = None,     # NEW: Filter by sentiment
    include_implicit: bool = True,    # NEW: Include implicit keyword matches
    limit: int = 100,
    offset: int = 0,
) -> list[SearchResult]:
    ...
```

---

## Celery Tasks for Enrichment

### Task: Enrich Single Post

```python
@shared_task(
    name="src.tnse.llm.tasks.enrich_post",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",  # Rate limit for Groq API
)
def enrich_post(self, post_id: str) -> dict[str, Any]:
    """Enrich a single post with LLM-extracted metadata."""
    ...
```

### Task: Enrich New Posts (Scheduled)

```python
@shared_task(
    name="src.tnse.llm.tasks.enrich_new_posts",
    bind=True,
    max_retries=3,
)
def enrich_new_posts(self) -> dict[str, Any]:
    """Find posts without enrichment and process them."""
    ...
```

### Celery Beat Schedule

**Note:** Celery Beat is already configured and operational in the project:
- Configuration file: `src/tnse/core/celery_app.py`
- Schedule file location: `/tmp/celerybeat-schedule` (configured for Docker container compatibility)
- Existing schedule: Content collection runs every 15 minutes

Add the enrichment schedule to the existing `celery_app.conf.beat_schedule` dictionary:

```python
# Add to celery_app.conf.beat_schedule in src/tnse/core/celery_app.py
celery_app.conf.beat_schedule = {
    # Existing: Content collection
    "collect-content-every-15-minutes": {
        "task": "src.tnse.pipeline.tasks.collect_all_channels",
        "schedule": 900.0,  # 15 minutes
        "options": {"expires": 840.0},
    },
    # NEW: Post enrichment
    "enrich-new-posts-every-5-minutes": {
        "task": "src.tnse.llm.tasks.enrich_new_posts",
        "schedule": 300.0,  # 5 minutes
        "options": {"expires": 240.0},
    },
}
```

Also register the LLM tasks module in the Celery app configuration:
```python
imports=["src.tnse.pipeline.tasks", "src.tnse.llm.tasks"],
include=["src.tnse.pipeline.tasks", "src.tnse.llm.tasks"],
```

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_ENABLED=true
LLM_PROVIDER=groq

# Groq Configuration
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen-qwq-32b
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.1

# Enrichment Settings
ENRICHMENT_BATCH_SIZE=10
ENRICHMENT_RATE_LIMIT=10  # requests per minute
ENRICHMENT_MAX_RETRIES=3
```

### Settings Class Update

```python
# src/tnse/core/config.py

class GroqSettings(BaseSettings):
    """Groq API configuration."""

    model_config = SettingsConfigDict(env_prefix="GROQ_")

    api_key: str | None = Field(default=None, description="Groq API key")
    model: str = Field(default="qwen-qwq-32b", description="Groq model ID")
    max_tokens: int = Field(default=1024, description="Max tokens for response")
    temperature: float = Field(default=0.1, description="Temperature for generation")


class EnrichmentSettings(BaseSettings):
    """Post enrichment configuration."""

    model_config = SettingsConfigDict(env_prefix="ENRICHMENT_")

    batch_size: int = Field(default=10, description="Batch size for enrichment")
    rate_limit: int = Field(default=10, description="Requests per minute")
    max_retries: int = Field(default=3, description="Max retries per post")
```

---

## Cost Tracking

### Token Usage Table

```sql
CREATE TABLE llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    estimated_cost_usd DECIMAL(10, 6),
    task_name VARCHAR(255),
    posts_processed INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_llm_usage_logs_created_at ON llm_usage_logs (created_at);
CREATE INDEX ix_llm_usage_logs_model ON llm_usage_logs (model);
```

### Cost Estimation

```python
# Groq pricing (as of 2025)
GROQ_PRICING = {
    "qwen-qwq-32b": {
        "input_per_million": 0.29,
        "output_per_million": 0.39,
    }
}

def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate cost in USD for token usage."""
    pricing = GROQ_PRICING.get(model, {"input_per_million": 0.5, "output_per_million": 0.5})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input_per_million"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output_per_million"]
    return input_cost + output_cost
```

---

## Bot Integration

### New Commands

```
/mode [llm|metrics] - Switch between LLM and metrics-only search
/enrich @channel - Manually trigger enrichment for channel posts
/stats llm - Show LLM usage statistics and costs
```

### Enhanced Search Display

When LLM enrichment is available, search results will show:

```
Search: "corruption news"
Found 47 results (showing 1-5)

1. [Channel Name] - 12.5K views
   Preview: Minister caught accepting...
   Reactions: thumbs_up 150 | heart 89 | fire 34
   Category: politics | Sentiment: negative
   Score: 0.25 | 2h ago
   [View Post]
```

---

## Future Phase: Chat Q&A

Once enrichment is complete, the system enables a future chat-like Q&A interface:

1. **Retrieve:** Find posts matching keywords (explicit + implicit)
2. **Augment:** Inject retrieved posts into LLM prompt as context
3. **Generate:** LLM synthesizes answer from retrieved posts

This is the "RAG" - but using keyword retrieval instead of vector similarity.

---

## Work Stream Breakdown

See `WS-5-TASK-BREAKDOWN.md` for detailed sub-tasks.

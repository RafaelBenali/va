# LLM Integration Guide

This guide covers the LLM (Large Language Model) integration in TNSE for post enrichment and semantic search capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Components](#components)
5. [Prompt Templates](#prompt-templates)
6. [Cost Management](#cost-management)
7. [Celery Tasks](#celery-tasks)
8. [Enhanced Search](#enhanced-search)
9. [Performance](#performance)
10. [Troubleshooting](#troubleshooting)

---

## Overview

TNSE implements a "RAG Without Vectors" approach to semantic search. Instead of using traditional vector embeddings, the system uses LLM-extracted keywords to improve search recall while maintaining the existing PostgreSQL full-text search infrastructure.

### Key Innovation: Implicit Keywords

The core innovation is the `implicit_keywords` field, which captures concepts, entities, and themes that are NOT directly in the text but are semantically related. This enables "RAG-like" retrieval without the complexity and cost of vector databases.

**Example:**
- Post content: "Minister caught accepting cash from contractor"
- Explicit keywords: ["minister", "cash", "contractor"]
- Implicit keywords: ["corruption", "bribery", "scandal", "politics", "government"]

A search for "corruption" would find this post even though "corruption" does not appear in the text.

### Benefits

- No vector database required
- Uses existing PostgreSQL infrastructure (GIN indexes)
- Lower latency than vector similarity search
- Cost-effective (uses Groq free tier)
- Graceful fallback to metrics-only mode

---

## Architecture

```
+------------------+     +-------------------+     +------------------+
|  Content         |     |  LLM Enrichment   |     |  PostgreSQL      |
|  Collector       | --> |  Service          | --> |  (Extended       |
|  (existing)      |     |  (Groq API)       |     |   Schema)        |
+------------------+     +-------------------+     +------------------+
         |                       |                        |
         v                       v                        v
+------------------+     +-------------------+     +------------------+
|  Post Storage    |     |  Enrichment       |     |  Enhanced        |
|  (existing)      |     |  Queue (Celery)   |     |  Search Service  |
+------------------+     +-------------------+     +------------------+
```

### Data Flow

1. **Content Collection:** Posts are collected from Telegram channels (existing pipeline)
2. **Enrichment Queue:** Celery task `enrich_new_posts` runs every 5 minutes
3. **LLM Processing:** EnrichmentService sends posts to Groq API for analysis
4. **Storage:** Enrichment results stored in `post_enrichments` table
5. **Search:** Enhanced search queries both text content and keyword arrays

### Design Decisions

1. **Non-blocking Enrichment:** LLM enrichment runs asynchronously via Celery - does NOT block content collection
2. **Graceful Fallback:** System works in metrics-only mode when LLM is disabled or fails
3. **Keyword-Based Retrieval:** Uses PostgreSQL GIN indexes on keyword arrays
4. **Cost Tracking:** Built-in token usage and cost monitoring
5. **Structured Output:** Uses Groq's JSON mode for reliable extraction

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Groq API Configuration (Required for LLM features)
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=qwen-qwq-32b
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.1
GROQ_ENABLED=true
GROQ_RATE_LIMIT_RPM=30
GROQ_TIMEOUT_SECONDS=30.0
GROQ_MAX_RETRIES=3

# Enrichment Settings
ENRICHMENT_BATCH_SIZE=10
ENRICHMENT_RATE_LIMIT=10

# Cost Limits (Optional)
LLM_DAILY_COST_LIMIT_USD=10.00
```

### Configuration Classes

The configuration is managed through Pydantic settings classes in `src/tnse/core/config.py`:

```python
class GroqSettings(BaseSettings):
    """Groq API configuration."""
    model_config = SettingsConfigDict(env_prefix="GROQ_")

    api_key: str | None = Field(default=None)
    model: str = Field(default="qwen-qwq-32b")
    max_tokens: int = Field(default=1024)
    temperature: float = Field(default=0.1)
    enabled: bool = Field(default=False)
    rate_limit_rpm: int = Field(default=30)
    timeout_seconds: float = Field(default=30.0)
    max_retries: int = Field(default=3)
```

### Model Selection

| Model | Context | Speed | Cost | Notes |
|-------|---------|-------|------|-------|
| `qwen-qwq-32b` | 32K | Fast | Low | **Recommended** - Best for multilingual |
| `llama-3.1-70b-versatile` | 128K | Medium | Medium | Good for complex analysis |
| `llama-3.1-8b-instant` | 128K | Very Fast | Very Low | For simple extraction |

---

## Components

### LLMProvider Interface (`base.py`)

Abstract base class defining the LLM provider interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, ...) -> CompletionResult:
        """Generate text completion."""

    @abstractmethod
    async def complete_json(self, prompt: str, ...) -> CompletionResult:
        """Generate JSON completion with format enforcement."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available."""
```

### GroqClient (`groq_client.py`)

Async client for Groq API with:

- **Rate Limiting:** Token bucket algorithm respecting API limits
- **JSON Mode:** Structured output with automatic parsing
- **Retries:** Exponential backoff on transient failures
- **Error Handling:** Custom exceptions for common failure modes

```python
from src.tnse.llm import GroqClient

# Using context manager (recommended)
async with GroqClient(api_key="your-key") as client:
    result = await client.complete_json("Extract keywords from: ...")
    print(result.parsed_json)

# Or create from settings
from src.tnse.core.config import get_settings
client = GroqClient.from_settings(get_settings().groq)
```

### EnrichmentService (`enrichment_service.py`)

Service for extracting metadata from post content:

```python
from src.tnse.llm import EnrichmentService, GroqClient

client = GroqClient(api_key="your-key")
service = EnrichmentService(llm_client=client)

# Single post enrichment
result = await service.enrich_post(
    post_id=123,
    text="Minister caught accepting cash from contractor"
)
# Returns EnrichmentResult with:
# - explicit_keywords: ["minister", "cash", "contractor"]
# - implicit_keywords: ["corruption", "bribery", "scandal", "politics"]
# - category: "politics"
# - sentiment: "negative"
# - entities: {"persons": ["minister"], "organizations": [], "locations": []}

# Batch enrichment with rate limiting
posts = [(1, "text1"), (2, "text2"), (3, "text3")]
results = await service.enrich_batch(posts)
```

### EnrichmentResult Dataclass

```python
@dataclass
class EnrichmentResult:
    post_id: int
    explicit_keywords: list[str]   # Words in text
    implicit_keywords: list[str]   # Related concepts NOT in text
    category: str                  # politics, economics, technology, etc.
    sentiment: str                 # positive, negative, neutral
    entities: dict[str, list[str]] # persons, organizations, locations
    input_tokens: int
    output_tokens: int
    processing_time_ms: int
    success: bool
    error_message: str | None
```

---

## Prompt Templates

### Main Enrichment Prompt

The enrichment prompt is defined in `src/tnse/llm/enrichment_service.py`:

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
        "persons": ["names of people mentioned or implied"],
        "organizations": ["names of organizations, companies, institutions"],
        "locations": ["geographic locations mentioned or implied"]
    }}
}}

IMPORTANT for implicit_keywords:
- These are concepts that a reader would associate with this content but are NOT directly mentioned in the text
- Include related terms, synonyms, broader categories, contextual associations
- Example: If post mentions "iPhone", implicit keywords might include ["Apple", "smartphone", "iOS", "tech gadget"]
- Example: If post mentions "Minister caught accepting cash", implicit keywords might include ["corruption", "bribery", "scandal", "politics"]

IMPORTANT for explicit_keywords:
- Extract key words and phrases that actually appear in the text
- Focus on nouns, proper nouns, and significant terms

Return ONLY valid JSON, no explanations or additional text."""
```

### Prompt Design Guidelines

When modifying or creating new prompts:

1. **Be explicit about JSON structure** - Include exact field names and types
2. **Provide examples** - Show what implicit keywords should look like
3. **Specify language support** - Russian, Ukrainian, English
4. **Use low temperature** - 0.1 for consistent extraction
5. **Handle edge cases** - Empty text, media-only, very long content

### Valid Categories

```python
valid_categories = [
    "politics",
    "economics",
    "technology",
    "sports",
    "entertainment",
    "health",
    "military",
    "crime",
    "society",
    "other",
]
```

---

## Cost Management

### Token Usage Tracking

All LLM calls are logged to the `llm_usage_logs` table:

```sql
CREATE TABLE llm_usage_logs (
    id UUID PRIMARY KEY,
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    estimated_cost_usd DECIMAL(10, 6),
    task_name VARCHAR(255),
    posts_processed INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### Groq Pricing (Estimates)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| qwen-qwq-32b | $0.15 | $0.60 |
| llama-3.1-70b-versatile | $0.59 | $0.79 |
| llama-3.1-8b-instant | $0.05 | $0.08 |

### Cost Estimation

The system automatically estimates costs for each LLM call:

```python
def _estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> Decimal:
    pricing = GROQ_PRICING.get(model, GROQ_PRICING["default"])
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return Decimal(str(round(input_cost + output_cost, 6)))
```

### Cost Monitoring

Query usage statistics:

```sql
-- Daily usage summary
SELECT
    DATE(created_at) as date,
    model,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost_usd) as total_cost,
    COUNT(*) as api_calls,
    SUM(posts_processed) as posts_processed
FROM llm_usage_logs
GROUP BY DATE(created_at), model
ORDER BY date DESC;

-- Last 7 days total
SELECT
    SUM(total_tokens) as tokens,
    SUM(estimated_cost_usd) as cost
FROM llm_usage_logs
WHERE created_at > NOW() - INTERVAL '7 days';
```

### Free Tier Limits

Groq free tier provides:
- 30 requests per minute
- 14,400 requests per day
- Limited tokens per day (varies by model)

The system respects these limits through built-in rate limiting.

---

## Celery Tasks

### Available Tasks

```python
# Single post enrichment
from src.tnse.llm import tasks
tasks.enrich_post.delay(post_id=123)

# Batch enrichment of new posts
tasks.enrich_new_posts.delay(limit=100)

# Channel-specific enrichment
tasks.enrich_channel_posts.delay(channel_id="uuid", limit=50)
```

### Celery Beat Schedule

Add to `src/tnse/core/celery_app.py`:

```python
celery_app.conf.beat_schedule = {
    # Existing: Content collection
    "collect-content-every-15-minutes": {
        "task": "src.tnse.pipeline.tasks.collect_all_channels",
        "schedule": 900.0,
        "options": {"expires": 840.0},
    },
    # NEW: Post enrichment
    "enrich-new-posts-every-5-minutes": {
        "task": "src.tnse.llm.tasks.enrich_new_posts",
        "schedule": 300.0,
        "options": {"expires": 240.0},
    },
}
```

### Task Configuration

Tasks include:
- **Max retries:** 3 with exponential backoff
- **Rate limiting:** 10 requests/minute (configurable)
- **Auto-retry:** For GroqRateLimitError, GroqTimeoutError

### Monitoring Tasks

Check task status in Celery logs:

```
[INFO] Starting enrich_new_posts task - limit=100
[INFO] Starting batch enrichment - posts_found=25, limit=100
[INFO] Post enriched successfully - post_id=123, category=politics, sentiment=negative
[INFO] Batch enrichment complete - posts_processed=25, posts_enriched=24, posts_failed=1
```

---

## Enhanced Search

### Database Schema

The `post_enrichments` table stores enrichment data:

```sql
CREATE TABLE post_enrichments (
    id UUID PRIMARY KEY,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    explicit_keywords TEXT[],
    implicit_keywords TEXT[],
    category VARCHAR(100),
    sentiment VARCHAR(20),
    entities JSONB,
    model_used VARCHAR(100),
    token_count INTEGER,
    processing_time_ms INTEGER,
    enriched_at TIMESTAMP WITH TIME ZONE
);

-- GIN indexes for keyword array search
CREATE INDEX ix_post_enrichments_explicit_keywords
    ON post_enrichments USING GIN (explicit_keywords);
CREATE INDEX ix_post_enrichments_implicit_keywords
    ON post_enrichments USING GIN (implicit_keywords);
```

### Search Query Pattern

```sql
SELECT p.*, pc.text_content, pe.category, pe.sentiment
FROM posts p
JOIN post_content pc ON p.id = pc.post_id
LEFT JOIN post_enrichments pe ON p.id = pe.post_id
WHERE
    -- Full-text search on content
    to_tsvector('russian', pc.text_content) @@ plainto_tsquery('russian', :query)
    -- OR keyword array match (explicit)
    OR :keywords && pe.explicit_keywords
    -- OR keyword array match (implicit - key for RAG!)
    OR :keywords && pe.implicit_keywords
ORDER BY em.relative_engagement DESC;
```

### Search Filters (Future - WS-5.5/5.6)

Once WS-5.5 and WS-5.6 are complete:

```
/search corruption category:politics
/search tech news sentiment:positive
/search category:military
```

---

## Performance

### Benchmarks

Based on testing with Groq qwen-qwq-32b:

| Metric | Value |
|--------|-------|
| Enrichment time per post | 1-3 seconds |
| Tokens per post (average) | 400-600 input, 200-400 output |
| Throughput (with rate limit) | ~10 posts/minute |
| Search response time | <500ms (with enriched data) |

### Optimization Tips

1. **Batch Processing:** Use `enrich_batch()` for multiple posts
2. **Rate Limiting:** Respect API limits to avoid errors
3. **Text Truncation:** Long posts are truncated to 4000 characters
4. **Skip Empty:** Empty/media-only posts are skipped automatically
5. **Database Indexes:** GIN indexes on keyword arrays are essential

### Scalability

- **Horizontal:** Multiple Celery workers can process enrichment tasks
- **Vertical:** Increase `ENRICHMENT_BATCH_SIZE` for faster processing
- **Cost:** Monitor `llm_usage_logs` to stay within budget

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "GROQ_API_KEY not configured" | Missing API key | Set `GROQ_API_KEY` environment variable |
| Rate limit errors | Too many requests | Reduce `ENRICHMENT_RATE_LIMIT` |
| JSON parse errors | Malformed LLM response | Lower temperature, check prompt |
| Timeout errors | Slow API response | Increase `GROQ_TIMEOUT_SECONDS` |
| Empty enrichment results | No text content | Check post has text (not media-only) |

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
```

Check logs for:
```
[DEBUG] Starting enrichment for post 123 (text length: 1500)
[INFO] Enriched post 123: category=politics, sentiment=negative, explicit_keywords=5, implicit_keywords=8
```

### Testing LLM Connection

```python
import asyncio
from src.tnse.llm import GroqClient

async def test_connection():
    async with GroqClient(api_key="your-key") as client:
        if await client.is_available():
            print("Client configured")
            if await client.health_check():
                print("API responding")
            else:
                print("API not responding")
        else:
            print("Client not configured")

asyncio.run(test_connection())
```

### Checking Enrichment Status

```sql
-- Posts awaiting enrichment
SELECT COUNT(*) as unenriched
FROM posts p
WHERE NOT EXISTS (
    SELECT 1 FROM post_enrichments pe WHERE pe.post_id = p.id
);

-- Recent enrichment stats
SELECT
    DATE(enriched_at) as date,
    COUNT(*) as enriched,
    AVG(token_count) as avg_tokens,
    AVG(processing_time_ms) as avg_time_ms
FROM post_enrichments
WHERE enriched_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(enriched_at)
ORDER BY date DESC;
```

### Manual Enrichment Trigger

```python
from src.tnse.llm import tasks

# Trigger batch enrichment immediately
result = tasks.enrich_new_posts.apply(args=[100])
print(result.get())
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Coding standards and LLM patterns
- [USER_GUIDE.md](USER_GUIDE.md) - Bot commands for LLM features
- [DEPLOYMENT.md](DEPLOYMENT.md) - Groq API setup for production
- [WS-5-RAG-WITHOUT-VECTORS.md](WS-5-RAG-WITHOUT-VECTORS.md) - Technical architecture

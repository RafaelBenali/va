# WS-5.3: Enrichment Service Core - Dev Log

## Summary

Implemented the core EnrichmentService that extracts metadata from post content via LLM. This is the heart of the RAG-without-vectors approach, extracting both explicit keywords (in text) and implicit keywords (related concepts NOT in text).

**Status:** Complete
**Date:** 2026-01-05
**Agent:** tdd-coder-ws53

---

## What Was Implemented

### 1. EnrichmentResult Dataclass

A comprehensive dataclass to hold enrichment results:

```python
@dataclass
class EnrichmentResult:
    post_id: int
    explicit_keywords: list[str]
    implicit_keywords: list[str]  # Key RAG innovation
    category: str
    sentiment: str  # positive/negative/neutral
    entities: dict[str, list[str]]  # {persons, organizations, locations}
    input_tokens: int
    output_tokens: int
    processing_time_ms: int
    success: bool
    error_message: str | None = None
```

### 2. EnrichmentSettings Configuration

Pydantic settings class with sensible defaults:

- `batch_size`: 10 posts per batch
- `rate_limit_per_minute`: 30 requests (Groq free tier)
- `max_text_length`: 4000 characters before truncation
- `valid_categories`: politics, economics, technology, sports, entertainment, health, military, crime, society, other
- `valid_sentiments`: positive, negative, neutral

### 3. EnrichmentService Class

Main service class with two primary methods:

#### `enrich_post(post_id: int, text: str | None) -> EnrichmentResult`

Enriches a single post by:
1. Handling empty/None text as empty success result
2. Truncating long text at word boundaries
3. Building prompt from template
4. Calling LLM with JSON mode
5. Parsing and validating response
6. Normalizing keywords (lowercase, deduplication)
7. Handling all error types gracefully

#### `enrich_batch(posts: list[tuple[int, str]]) -> list[EnrichmentResult]`

Processes multiple posts with rate limiting:
1. Iterates through posts sequentially
2. Waits between requests to respect rate limit
3. Collects results (including partial failures)
4. Logs progress and final summary

### 4. ENRICHMENT_PROMPT Template

The prompt is the key to quality extraction:

```
Analyze this Russian/Ukrainian/English Telegram post. Extract structured information.

POST CONTENT:
{text_content}

Extract the following in JSON format:
{
    "explicit_keywords": ["list of keywords/phrases that appear directly in the text"],
    "implicit_keywords": ["list of related concepts, themes, entities NOT in the text but semantically relevant"],
    "category": "primary topic category (politics, economics, technology, ...)",
    "sentiment": "positive|negative|neutral",
    "entities": {
        "persons": ["names of people mentioned or implied"],
        "organizations": ["names of organizations, companies, institutions"],
        "locations": ["geographic locations mentioned or implied"]
    }
}

IMPORTANT for implicit_keywords:
- These are concepts that a reader would associate with this content but are NOT directly mentioned
- Include related terms, synonyms, broader categories, contextual associations
- Example: If post mentions "iPhone", implicit keywords might include ["Apple", "smartphone", "iOS"]
```

---

## Key Design Decisions

### 1. RAG Without Vectors

The key innovation is **implicit_keywords** - concepts related to content but NOT in the text:

| Post Text | Explicit Keywords | Implicit Keywords |
|-----------|-------------------|-------------------|
| "Minister caught accepting cash in hotel room" | minister, cash, hotel | corruption, bribery, scandal, politics |
| "Bitcoin reaches new all-time high" | bitcoin, high | cryptocurrency, blockchain, finance, investment |

This enables semantic search without vector embeddings.

### 2. Validation with Defaults

Instead of failing on invalid LLM responses, we use sensible defaults:

- Missing `implicit_keywords` -> `[]`
- Invalid `category` -> `"other"`
- Invalid `sentiment` -> `"neutral"`
- Missing `entities` keys -> `[]` for each

### 3. Keyword Normalization

All keywords are:
- Converted to lowercase
- Stripped of whitespace
- Deduplicated (case-insensitive)

### 4. Rate Limiting Strategy

The service implements rate limiting at the batch level:
- Uses asyncio.Lock for thread safety
- Tracks `_last_request_time`
- Waits `60 / rate_limit_per_minute` seconds between requests
- First request doesn't wait

---

## Test Coverage

37 tests covering:

| Category | Tests |
|----------|-------|
| EnrichmentResult dataclass | 4 |
| EnrichmentSettings | 2 |
| EnrichmentService creation | 3 |
| enrich_post() method | 3 |
| enrich_batch() method | 3 |
| Edge cases | 8 |
| JSON validation | 5 |
| Prompt template | 5 |
| Structured logging | 2 |
| Multilingual support | 2 |

Coverage: 94% on `enrichment_service.py`

---

## Files Changed

| File | Change |
|------|--------|
| `src/tnse/llm/enrichment_service.py` | New file (507 lines) |
| `src/tnse/llm/__init__.py` | Added exports |
| `tests/unit/llm/test_enrichment_service.py` | New file (969 lines) |

---

## Challenges and Solutions

### 1. Rate Limiting Test Timing

**Challenge:** Rate limit test was timing-sensitive and flaky.

**Solution:** Rewrote test to capture call timestamps and verify delays between calls rather than total elapsed time.

### 2. First Request Delay

**Challenge:** First request in batch was being delayed unnecessarily.

**Solution:** Modified rate limiter to only wait if `_last_request_time > 0`, allowing first request to proceed immediately.

### 3. Keyword Case Sensitivity

**Challenge:** LLM returns keywords in various cases.

**Solution:** Normalize all keywords to lowercase and deduplicate after normalization.

---

## Next Steps

WS-5.4: Celery Enrichment Tasks
- Wire EnrichmentService into Celery scheduled tasks
- Add task to enrich new posts automatically
- Implement batch processing with progress tracking

---

## Usage Example

```python
from src.tnse.llm import GroqClient, EnrichmentService

async with GroqClient(api_key="your-key") as client:
    service = EnrichmentService(llm_client=client)

    # Single post
    result = await service.enrich_post(
        post_id=123,
        text="Minister caught accepting cash in hotel room"
    )

    print(result.implicit_keywords)  # ['corruption', 'bribery', 'scandal']

    # Batch processing
    posts = [(1, "text1"), (2, "text2"), (3, "text3")]
    results = await service.enrich_batch(posts)
```

---

## Commits

1. `test: add failing tests for EnrichmentService core logic (WS-5.3)`
2. `feat: implement EnrichmentService for LLM-based post enrichment (WS-5.3)`

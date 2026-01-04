# WS-5.2: Database Schema for Post Enrichment

**Status:** Complete
**Started:** 2026-01-05
**Completed:** 2026-01-05
**Assigned:** tdd-coder-ws52

## Summary

This work stream implemented the database schema for storing LLM-extracted metadata from posts, enabling the "RAG without Vectors" approach described in WS-5. The schema supports keyword-based semantic search using PostgreSQL's array operators and GIN indexes.

## What Was Implemented

### PostEnrichment Model

A new SQLAlchemy model for storing LLM-extracted metadata:

- **explicit_keywords**: `ARRAY(Text)` - Keywords directly present in the post text
- **implicit_keywords**: `ARRAY(Text)` - Related concepts NOT in the text (the key innovation for RAG)
- **category**: `String(100)` - Post category (politics, tech, economics, etc.)
- **sentiment**: `String(20)` - Sentiment classification (positive/negative/neutral)
- **entities**: `JSONB` - Named entities (people, organizations, places)
- **model_used**: LLM model identifier used for enrichment
- **token_count**: Total tokens used in the enrichment request
- **processing_time_ms**: Time taken for LLM processing
- **enriched_at**: Timestamp of enrichment

The model has a one-to-one relationship with Post (CASCADE on delete).

### LLMUsageLog Model

A new model for tracking LLM API usage and costs:

- **model**: LLM model identifier
- **prompt_tokens**: Input token count
- **completion_tokens**: Output token count
- **total_tokens**: Combined token count
- **estimated_cost_usd**: `Numeric(10, 6)` - Cost estimation
- **task_name**: Task/operation identifier
- **posts_processed**: Number of posts in batch
- **created_at**: Timestamp

### Alembic Migration

Migration `b2c3d4e5f6g7` creates both tables with appropriate indexes:

**Standard Indexes:**
- `ix_post_enrichments_post_id` - Foreign key lookup
- `ix_post_enrichments_category` - Category filtering
- `ix_llm_usage_logs_created_at` - Time-based queries
- `ix_llm_usage_logs_model` - Model-based filtering

**GIN Indexes (for efficient array overlap queries):**
- `ix_post_enrichments_explicit_keywords_gin` - Search by explicit keywords
- `ix_post_enrichments_implicit_keywords_gin` - Search by implicit keywords
- `ix_post_enrichments_entities_gin` - Search by entities

GIN indexes enable efficient use of PostgreSQL's `&&` (overlap) and `@>` (contains) operators for keyword searches.

## Key Decisions

1. **ARRAY vs JSONB for Keywords**: Used `ARRAY(Text)` for keywords instead of JSONB because:
   - Native PostgreSQL array operators (`&&`, `@>`) are simpler to use
   - GIN indexes work efficiently with array overlap queries
   - Keywords are naturally flat lists, not nested structures

2. **JSONB for Entities**: Kept entities as JSONB because:
   - Entities have structure (people, organizations, places)
   - Flexible schema for different entity types
   - GIN indexing still works for containment queries

3. **One-to-One with Post**: Each post has at most one enrichment record:
   - Simplifies relationship navigation
   - `unique=True` constraint on `post_id` enforces this
   - CASCADE delete removes enrichment when post is deleted

4. **Separate LLMUsageLog**: Not linked to specific posts because:
   - Batch processing enriches multiple posts per API call
   - Usage tracking is for cost management, not per-post audit
   - Simpler schema without foreign key complexity

## Test Coverage

### Model Tests (27 tests)
- Model existence and import
- Required field presence
- Field types (ARRAY, JSONB, String lengths)
- Foreign key constraints and CASCADE behavior
- Unique constraints on post_id
- Default values (enriched_at, created_at)
- Instance creation with valid data
- Relationship navigation (Post.enrichment, PostEnrichment.post)
- String representation (__repr__)

### Migration Tests (15 tests)
- Module import and structure
- Revision chain correctness
- upgrade/downgrade functions callable
- Table creation for both models
- GIN index creation with correct method
- Index drop order before table drop
- Column structure validation

## Challenges and Solutions

1. **Testing Alembic Migrations**: Standard import failed because `alembic/versions/` is not a Python package. Solved by using `importlib.util.spec_from_file_location()` to load the migration module directly.

2. **GIN Index Specification**: Initially unclear how to specify index type in Alembic. Found that `postgresql_using="gin"` is the correct parameter for `op.create_index()`.

## Next Steps

WS-5.3 (Enrichment Service Core) can now proceed to implement the service that:
- Takes post content as input
- Calls the Groq LLM (from WS-5.1)
- Stores results in PostEnrichment (from this WS-5.2)
- Logs usage to LLMUsageLog

## Commits

1. `03ba7ce` - test: add failing tests for PostEnrichment and LLMUsageLog models (WS-5.2)
2. `7a61f9c` - feat: implement PostEnrichment and LLMUsageLog models (WS-5.2)
3. `3b556c7` - feat: create Alembic migration for post enrichment tables (WS-5.2)

## Files Changed

- `src/tnse/db/models.py` - Added PostEnrichment and LLMUsageLog models, Post.enrichment relationship
- `alembic/versions/b2c3d4e5f6g7_add_post_enrichment_tables.py` - New migration
- `tests/unit/db/test_post_enrichment_models.py` - 27 unit tests for models
- `tests/unit/db/test_post_enrichment_migration.py` - 15 tests for migration

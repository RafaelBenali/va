# WS-5.5: Enhanced Search Service

## Summary

Implemented hybrid search functionality that combines PostgreSQL full-text search with keyword array matching on LLM-enriched data. This is the core RAG-without-vectors feature that enables finding posts via implicit keywords NOT present in the original text.

## Date Completed

2026-01-05

## Developer

tdd-coder

## Changes Made

### 1. Updated SearchResult Dataclass

Extended `SearchResult` with new enrichment fields:
- `category` (str | None): LLM-extracted topic category
- `sentiment` (str | None): Sentiment classification (positive/negative/neutral)
- `explicit_keywords` (list[str] | None): Keywords directly in the text
- `implicit_keywords` (list[str] | None): Related concepts NOT in text (key RAG feature)
- `match_type` (str | None): How the search matched (fulltext/explicit_keyword/implicit_keyword)

Added `is_enriched` property to detect if a result has LLM enrichment data.

### 2. Updated SearchQuery Dataclass

Extended with new filter parameters:
- `category` (str | None): Filter by category
- `sentiment` (str | None): Filter by sentiment
- `include_enrichment` (bool): Whether to include enrichment data in search (default: True)

### 3. Hybrid Search SQL

Created two SQL builders:
- `_build_basic_search_sql()`: Original full-text only search
- `_build_enriched_search_sql()`: Hybrid search with LEFT JOIN to post_enrichments

The enriched SQL:
- JOINs post_enrichments table with LEFT JOIN for backward compatibility
- Uses `&&` operator for PostgreSQL array overlap matching
- Matches against both explicit_keywords and implicit_keywords arrays
- Applies optional category and sentiment filters

### 4. Cache Serialization

Updated cache methods to include enrichment fields:
- `_serialize_results()`: Now serializes all enrichment fields
- `_deserialize_results()`: Restores enrichment fields using `.get()` for backward compatibility
- `_build_cache_key()`: Includes category, sentiment, include_enrichment in cache key

## Key Design Decisions

### 1. LEFT JOIN for Backward Compatibility

Used LEFT JOIN instead of INNER JOIN so posts without enrichment data still appear in search results. This ensures the search service works correctly even if:
- Enrichment pipeline is disabled
- New posts haven't been enriched yet
- Enrichment failed for some posts

### 2. Keyword Array Matching with && Operator

PostgreSQL's `&&` operator checks if two arrays have any overlapping elements. This is more efficient than using `ANY()` or `IN` for array matching and leverages the GIN index on the keyword arrays.

### 3. Separate SQL Builders

Split SQL generation into two methods to:
- Reduce complexity of the main search method
- Allow `include_enrichment=False` to skip the JOIN entirely for faster queries
- Make testing easier with isolated SQL generation

### 4. Enrichment Fields Default to None

All enrichment fields default to `None` for backward compatibility. The `is_enriched` property checks if any enrichment field is populated.

## Test Coverage

Created 24 new unit tests in `tests/unit/search/test_enhanced_search.py`:

- **TestEnhancedSearchResultFields** (6 tests): Verify new dataclass fields
- **TestSearchFilterParameters** (5 tests): Verify filter parameters work
- **TestHybridSearch** (5 tests): Verify hybrid search SQL and results
- **TestBackwardCompatibility** (2 tests): Verify works without enrichment
- **TestEnhancedSearchCaching** (3 tests): Verify cache handles enrichment
- **TestSearchPerformance** (1 test): Verify efficient LEFT JOIN usage
- **TestImplicitKeywordRanking** (2 tests): Verify match_type field

All 72 search-related tests pass (24 new + 48 existing).

## Files Modified

| File | Changes |
|------|---------|
| `src/tnse/search/service.py` | +204 lines: enrichment fields, filter params, hybrid SQL |
| `tests/unit/search/test_enhanced_search.py` | +772 lines: 24 new tests |

## Performance Considerations

- LEFT JOIN with proper indexes should maintain <3 second response time
- GIN indexes on keyword arrays enable efficient overlap matching
- Cache key includes filter parameters to prevent stale cache hits
- `include_enrichment=False` skips JOIN for faster basic searches

## Future Improvements

1. **Match Type Tracking**: Currently match_type is not populated by the SQL query. Would need to use CASE expressions to determine how each result was matched.

2. **Ranking Boost**: Could add ranking boost for implicit keyword matches vs. full-text matches to surface semantically relevant results higher.

3. **Keyword Highlighting**: Could highlight matched keywords in the result preview.

## Related Work Streams

- WS-5.1: Groq Client Integration (provides LLM calls)
- WS-5.2: Database Schema (defines post_enrichments table)
- WS-5.3: Enrichment Service (extracts keywords from posts)
- WS-5.4: Celery Tasks (runs enrichment in background)
- WS-5.6: Bot Integration (next: add filter syntax to bot commands)

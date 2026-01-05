# WS-5.6: Bot Integration (LLM Features)

## Work Stream Details

| Field | Value |
|-------|-------|
| **ID** | WS-5.6 |
| **Name** | Bot Commands for LLM Features |
| **Started** | 2026-01-05 |
| **Completed** | 2026-01-05 |
| **Status** | Complete |

## Summary

Implemented bot commands for LLM features, enabling users to switch between LLM-enhanced and metrics-only search modes, trigger manual enrichment for channels, and view LLM usage statistics. Also enhanced the search command to display enrichment data and support filter syntax for category and sentiment.

## Changes Made

### New Files Created

1. **`src/tnse/bot/llm_handlers.py`** - New handler module for LLM commands:
   - `/mode` (`/m`) - Show/switch between LLM and metrics modes
   - `/enrich @channel` - Trigger LLM enrichment for a channel
   - `/llmstats` - Show LLM usage statistics and costs
   - `get_current_mode()` - Helper to get current mode from bot_data
   - `set_current_mode()` - Helper to set current mode in bot_data
   - `VALID_MODES` and `DEFAULT_MODE` constants

2. **`tests/unit/bot/test_llm_handlers.py`** - Comprehensive tests (21 tests):
   - Mode command existence and functionality
   - Mode switching between llm and metrics
   - Invalid mode rejection
   - Default mode behavior
   - Enrich command with channel argument
   - Stats command with usage display
   - Error handling for missing config/services

3. **`tests/unit/bot/test_search_with_enrichment.py`** - Tests for enhanced search (13 tests):
   - SearchFormatter enrichment display
   - Filter syntax parsing (category:, sentiment:)
   - Search command with filters
   - Mode-aware include_enrichment behavior

### Modified Files

1. **`src/tnse/bot/search_handlers.py`**:
   - Added `parse_search_filters()` function for parsing `category:` and `sentiment:` filters
   - Added `format_enrichment()` method to SearchFormatter
   - Updated `format_result()` to display enrichment indicator
   - Updated `search_command()` to:
     - Parse and apply filter syntax
     - Set `include_enrichment` based on `llm_mode`
     - Show updated usage examples with filters
   - Added `VALID_CATEGORIES` and `VALID_SENTIMENTS` constants

2. **`src/tnse/bot/application.py`**:
   - Imported new LLM handlers
   - Registered `/mode` (with `/m` alias), `/enrich`, and `/llmstats` commands

3. **`src/tnse/bot/handlers.py`**:
   - Updated help text to include:
     - LLM Features section with new commands
     - Search filter syntax examples
     - Sync command in Advanced section

4. **`src/tnse/bot/menu.py`**:
   - Added "LLM" command category with mode, enrich, llmstats
   - Updated search command description to mention filters

## Implementation Decisions

### Mode-Based Search Behavior

The search command respects the current mode setting:
- **LLM mode** (`llm`): Sets `include_enrichment=True`, results include category/sentiment/keywords
- **Metrics mode** (`metrics`): Sets `include_enrichment=False`, faster search without enrichment

### Filter Syntax Design

Chose simple `key:value` syntax for filters:
```
/search corruption category:politics
/search scandal sentiment:negative
/search news category:economics sentiment:positive
```

This is familiar to power users and easy to parse while keeping the search query clean.

### Enrichment Display Format

Added enrichment indicator in result header for visual clarity:
```
1. [Channel Name] - 1.2K views [Politics | -]
```
- Shows category (capitalized) and sentiment indicator (+/-/omitted for neutral)
- Only displayed when enrichment data exists

### Robust MagicMock Handling

The `format_enrichment()` method includes explicit type checking to handle cases where tests pass MagicMock objects as SearchResult attributes, preventing `TypeError` exceptions.

## Testing Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| test_llm_handlers.py | 21 | Pass |
| test_search_with_enrichment.py | 13 | Pass |
| Existing bot tests | 430 | Pass |

All 34 new tests pass, plus all existing tests continue to pass after the changes.

## Commands Reference

### New Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `/mode` | `/m` | Show current mode or switch between llm/metrics |
| `/mode llm` | - | Switch to LLM-enhanced search |
| `/mode metrics` | - | Switch to metrics-only search |
| `/enrich @channel` | - | Trigger LLM enrichment for channel posts |
| `/llmstats` | - | Show LLM usage statistics and costs |

### Enhanced Search Syntax

```
/search <query> [category:<value>] [sentiment:<value>]
```

Valid categories: politics, economics, technology, sports, entertainment, health, military, crime, society, other

Valid sentiments: positive, negative, neutral

## Follow-up Items

None - all planned tasks for WS-5.6 have been completed.

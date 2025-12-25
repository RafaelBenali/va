# WS-2.4: Search Bot Commands - Development Log

## Overview

| Field | Value |
|-------|-------|
| Work Stream | WS-2.4 |
| Name | Search Bot Commands |
| Started | 2025-12-26 |
| Completed | 2025-12-26 |
| Author | Claude Code |

## Summary

Implemented the `/search` command for the Telegram bot with full pagination support, engagement metrics display, and Telegram deep links to original posts.

## What Was Implemented

### 1. SearchFormatter Class

A comprehensive formatter for search results that handles:

- **View count formatting**: Converts raw view counts to human-readable format (e.g., 12500 -> "12.5K", 1500000 -> "1.5M")
- **Relative time display**: Shows "2h ago", "30m ago", etc.
- **Reaction display**: Formats emoji reaction counts with visual indicators
- **Score formatting**: Displays combined ranking score to 2 decimal places
- **Text preview**: Truncates long post content with ellipsis
- **Single result formatting**: Combines all elements into a structured display
- **Page formatting**: Assembles multiple results with header and handles Telegram's 4096 character limit

### 2. Pagination Keyboard

Created `create_pagination_keyboard()` function that generates inline keyboards with:

- "<<Prev" button (when not on first page)
- Page indicator showing "X/Y" (current/total)
- "Next>>" button (when not on last page)
- Callback data encoding query and target page

### 3. Search Command Handler

The `/search <query>` command:

- Accepts multi-word queries (all arguments combined)
- Shows usage message when no query provided
- Integrates with SearchService for database full-text search
- Displays results with formatting and pagination
- Stores results in user_data for efficient pagination
- Handles errors gracefully with user-friendly messages

### 4. Pagination Callback Handler

Handles callback queries for pagination buttons:

- Parses callback data to extract query and target page
- Uses cached results when available for performance
- Re-executes search if cache miss
- Updates message with new page content
- Maintains proper keyboard state

### 5. Bot Application Integration

- Registered `/search` command with access control
- Added CallbackQueryHandler for pagination with pattern matching
- Updated help message to show search as available

## Message Format Example

```
Search: "corruption news"
Found 47 results (showing 1-5)

1. [Channel Name] - 12.5K views
   Preview: Minister caught accepting...
   Reactions: [thumbs_up] 150 | [heart] 89 | [fire] 34
   Score: 0.25 | 2h ago
   [View Post](https://t.me/channel/123)

2. [Another Channel] - 8.2K views
   ...

[<< Prev] [1/10] [Next >>]
```

## Key Decisions

### 1. Page Size of 5 Results

Chose 5 results per page to balance:
- Message readability
- Staying within Telegram's 4096 character limit
- Reasonable pagination experience

### 2. Markdown Formatting with Link Preview Disabled

Used Markdown parse mode for formatting but disabled web page preview to:
- Keep message compact
- Avoid loading unnecessary previews
- Still provide clickable links

### 3. Caching Results in user_data

Stored search results in `context.user_data` to:
- Avoid re-querying database on every pagination click
- Maintain consistent results during pagination
- Enable future export functionality to use same results

### 4. Callback Data Format

Used format `search:query:page` with `:` delimiter because:
- Simple to parse
- Query can be preserved in callback
- Page number easily extracted

## Test Coverage

Created comprehensive test suite with 29 tests covering:

- SearchFormatter methods (view count, time, reactions, score, preview)
- Result and page formatting
- Telegram message length limit handling
- Pagination keyboard generation for all page positions
- search_command handler behavior
- pagination_callback handler behavior
- Link generation

All 545 project tests pass.

## Files Changed

### Created
- `src/tnse/bot/search_handlers.py` (586 lines)
- `tests/unit/bot/test_search_handlers.py` (653 lines)
- `devlog/ws-2.4-search-bot-commands.md` (this file)

### Modified
- `src/tnse/bot/application.py` (added imports and handler registration)
- `src/tnse/bot/handlers.py` (updated help message)
- `roadmap.md` (marked WS-2.4 as complete)

## Integration Points

- **SearchService**: Used for full-text search queries
- **RankingService**: Results come pre-sorted from SearchService
- **Access Control**: Uses existing `require_access` decorator
- **Bot Application**: Integrated via CommandHandler and CallbackQueryHandler

## Future Enhancements

1. **Reaction Counts**: Currently reactions are optional in display. Could integrate with engagement metrics to always show reaction breakdown.

2. **Sort Options**: Could add inline buttons to change sort order (views, recency, engagement).

3. **Search Filters**: Could add time window filters (last hour, last 6 hours, etc.).

4. **Export Integration**: WS-2.5 can use cached results from user_data for export.

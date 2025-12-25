# WS-3.1: Saved Topics - Development Log

## Overview

| Field | Value |
|-------|-------|
| **Work Stream** | WS-3.1 |
| **Name** | Topic Saving and Templates |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |
| **Developer** | Claude Code |

## Summary

Implemented topic management functionality allowing users to save search configurations and use pre-built templates for quick access to common search topics.

## Implemented Features

### 1. TopicService (CRUD Operations)

Created `src/tnse/topics/service.py` with:

- **SavedTopicData dataclass**: Data transfer object for topic information
  - `name`: Unique topic identifier (normalized to lowercase)
  - `keywords`: Comma-separated search keywords
  - `sort_mode`: Optional sort preference
  - `topic_id`: Database UUID
  - `created_at`: Creation timestamp

- **TopicService class**: Database operations for saved topics
  - `save_topic()`: Create new topic from last search
  - `get_topic()`: Retrieve topic by name
  - `list_topics()`: Get all active topics
  - `delete_topic()`: Remove saved topic

- **Custom exceptions**:
  - `TopicNotFoundError`: Raised when requested topic doesn't exist
  - `TopicAlreadyExistsError`: Raised when creating duplicate topic

### 2. Pre-built Templates

Created `src/tnse/topics/templates.py` with 5 required templates:

| Template | Keywords | Category |
|----------|----------|----------|
| corruption | corruption, bribery, scandal, investigation, fraud | politics |
| politics | government, election, parliament, minister, president | politics |
| tech | technology, AI, startup, innovation, software | technology |
| science | science, research, discovery, study, experiment | science |
| business | business, economy, market, finance, investment | business |

Functions provided:
- `get_template_by_name()`: Case-insensitive template lookup
- `get_all_templates()`: List all available templates

### 3. Bot Command Handlers

Created `src/tnse/bot/topic_handlers.py` with:

| Command | Description |
|---------|-------------|
| `/savetopic <name>` | Save current search as named topic |
| `/topics` | List all saved topics |
| `/topic <name>` | Run search with saved topic keywords |
| `/deletetopic <name>` | Delete a saved topic |
| `/templates` | Show all pre-built templates |
| `/usetemplate <name>` | Run search with template keywords |

All handlers include:
- Input validation with helpful usage messages
- Error handling with user-friendly messages
- Logging for debugging and monitoring

### 4. Application Integration

Updated `src/tnse/bot/application.py`:
- Imported all topic command handlers
- Registered 6 new command handlers with access control
- Commands protected with `require_access()` wrapper

Updated `src/tnse/bot/handlers.py`:
- Updated help message to include all topic commands
- Removed "coming soon" note

## Test Coverage

### Unit Tests Created

1. **test_topic_service.py** (12 tests):
   - SavedTopicData creation and serialization
   - Topic CRUD operations with mocked database
   - Error handling for duplicate/missing topics
   - Name normalization to lowercase

2. **test_templates.py** (18 tests):
   - Template data structure validation
   - All 5 required templates present with correct keywords
   - Case-insensitive template lookup
   - Template listing function

3. **test_topic_handlers.py** (15 tests):
   - All command handlers tested
   - Usage message display
   - Success and error scenarios
   - Service integration

**Total: 45 tests, all passing**

## Key Decisions

### 1. Topic Name Normalization
Topic names are normalized to lowercase to avoid confusion:
```python
def _normalize_name(self, name: str) -> str:
    return name.lower()
```

### 2. Keywords Storage
Keywords stored as comma-separated string for simplicity:
- Easy to display in messages
- Compatible with existing search service
- Stored in `keywords` column of `saved_topics` table

### 3. Template Implementation
Templates are hardcoded as immutable constants rather than database entries:
- Ensures templates always available
- No database migration needed
- Fast access without database queries

### 4. Search Integration
Topic searches reuse existing search infrastructure:
- Results stored in `user_data` for pagination
- Same formatting as regular search results
- Full pagination support

## Database Utilization

Uses existing models from WS-1.2:
- `SavedTopic` model for user-saved topics
- `TopicTemplate` model available but not used (templates hardcoded)

## Acceptance Criteria Verification

- [x] Topics saved and retrieved - Implemented via `/savetopic`, `/topic`, `/topics`
- [x] Templates work - 5 pre-built templates accessible via `/templates`, `/usetemplate`
- [x] Quick access via commands - All commands implemented and registered

## Files Modified/Created

### New Files
- `src/tnse/topics/__init__.py` - Module exports
- `src/tnse/topics/service.py` - TopicService implementation
- `src/tnse/topics/templates.py` - Template definitions
- `src/tnse/bot/topic_handlers.py` - Bot command handlers
- `tests/unit/topics/__init__.py` - Test module init
- `tests/unit/topics/test_topic_service.py` - Service tests
- `tests/unit/topics/test_templates.py` - Template tests
- `tests/unit/bot/test_topic_handlers.py` - Handler tests

### Modified Files
- `src/tnse/bot/application.py` - Added handler registrations
- `src/tnse/bot/handlers.py` - Updated help message
- `roadmap.md` - Updated status to In Progress then Complete

## Challenges and Solutions

### Challenge 1: Test Isolation
**Issue**: Tests needed to mock both topic_service and search_service.

**Solution**: Carefully set up mock context with all required services before each test.

### Challenge 2: User Data Persistence
**Issue**: Need to access last search for /savetopic.

**Solution**: Store `last_search_query` in Telegram's `user_data` context, consistent with existing search handlers.

## Future Considerations

1. **Topic Categories**: Could add category support for organizing topics
2. **Topic Sharing**: Could allow users to share topics (requires user identification)
3. **Template Search**: Could add /template shorthand for /usetemplate
4. **Topic Updates**: Could add /updatetopic to modify existing topics

## Commit History

1. `feat: implement TopicService and templates for saved topics` - Core functionality
2. Integration with bot application (included in WS-3.2 commit)

---

*Development completed using TDD methodology. All tests pass.*

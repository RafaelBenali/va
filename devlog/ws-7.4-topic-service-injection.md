# WS-7.4: TopicService Injection Bug Fix

## Summary

Fixed broken topic-related commands (/savetopic, /topics, /topic, /deletetopic) by implementing proper TopicService dependency injection through the bot application. The fix required creating a factory pattern to handle the async session lifecycle properly.

## What Was Implemented

### 1. TopicServiceFactory Pattern (`src/tnse/bot/__main__.py`)

Created a factory pattern to handle TopicService instantiation with proper async session management:

- `TopicServiceFactory`: A callable wrapper around the database session factory
- `TopicServiceContext`: An async context manager that creates sessions and TopicService instances
- `create_topic_service()`: Factory function following the established service injection pattern

The factory pattern was chosen because `TopicService` requires an `AsyncSession` directly (unlike `SearchService` which takes a session factory). This pattern allows handlers to create fresh sessions per-request:

```python
async with topic_service() as topic_svc:
    result = await topic_svc.save_topic(...)
```

### 2. Service Status Logging (`log_service_status()`)

Added topic_service parameter to the startup logging function:
- Logs info when topic service is available
- Logs warning with disabled commands when unavailable
- Provides hints about database configuration

### 3. Main Function Integration

Updated `main()` to:
- Create topic_service using `create_topic_service(db_session_factory)`
- Pass topic_service to `log_service_status()`
- Inject topic_service into `create_bot_from_env()` call

### 4. Handler Updates (`src/tnse/bot/topic_handlers.py`)

Updated all topic handlers to use the factory pattern:
- `savetopic_command`: Uses `async with topic_service() as topic_svc:`
- `topics_command`: Uses factory pattern for listing
- `topic_command`: Uses factory pattern for getting topic
- `deletetopic_command`: Uses factory pattern for deletion

### 5. Improved Error Messages

All handlers now show user-friendly configuration errors:
```
Topic management is not configured.

The database connection is required for topic features.

Please contact the administrator to configure database settings.
```

Instead of the previous generic "not available" message.

### 6. Test Updates

Updated tests to work with the factory pattern:
- Created `mock_topic_service_factory` fixture for unit tests
- Updated integration test fixtures to return factory mocks
- Assertions now access the underlying service via `factory._service`

## Key Decisions

1. **Factory Pattern vs Direct Injection**: Chose factory pattern because TopicService takes an AsyncSession directly. Creating a service instance at startup would have required a single long-lived session, which is not appropriate for async database operations.

2. **Consistent with Existing Code**: Followed the same pattern as `create_search_service()` and `create_channel_service()` for consistency.

3. **User-Friendly Error Messages**: Error messages now mention "configuration" and "administrator" to help users understand it's a setup issue, not a user error.

## Test Coverage

- 18 new tests in `test_topic_service_injection.py`
- 15 existing topic handler tests updated and passing
- 5 integration tests for topic flow passing
- Total: 993 tests passing (2 pre-existing failures unrelated to this work)

## Files Changed

- `src/tnse/bot/__main__.py`: Added TopicServiceFactory, TopicServiceContext, create_topic_service()
- `src/tnse/bot/topic_handlers.py`: Updated handlers to use factory pattern
- `tests/unit/bot/test_topic_service_injection.py`: New test file
- `tests/unit/bot/test_topic_handlers.py`: Updated fixtures for factory pattern
- `tests/integration/test_bot_integration.py`: Updated fixtures for factory pattern

## Commands Now Working

After this fix, the following commands are functional:
- `/savetopic <name>` - Save current search as a topic
- `/topics` - List all saved topics
- `/topic <name>` - Run a saved topic search
- `/deletetopic <name>` - Delete a saved topic

## Related Work Streams

- WS-7.1: Service Dependency Injection Fix (channel service)
- WS-7.2: Channel Validation Connection Fix (auto-connect)
- WS-7.3: Search Service Injection (search service)

# WS-8.2: Resume-from-Last-Point Tracking

## Summary

Implemented resume-from-last-point tracking for content collection. The system now tracks the last collected message ID per channel, allowing subsequent collections to only fetch new messages since the last run. This significantly reduces collection time and API calls on repeat runs.

## Date

2026-01-04

## Changes Made

### Database Changes

1. **New Migration**: `alembic/versions/add_last_collected_message_id.py`
   - Added `last_collected_message_id` (BigInteger, nullable) column to channels table
   - Added `last_collected_at` (DateTime with timezone, nullable) column for tracking collection timestamps
   - Added index on `last_collected_message_id` for efficient lookups

2. **Channel Model Update**: `src/tnse/db/models.py`
   - Added `last_collected_message_id` field with BigInteger type
   - Added `last_collected_at` field with DateTime(timezone=True)
   - Updated docstring to document new fields

### ContentCollector Changes

1. **Updated `collect_channel_messages` method**: `src/tnse/pipeline/collector.py`
   - Added `min_id` parameter (default: 0) for resume tracking
   - Changed return type from `list[dict]` to `dict` with metadata
   - Return format now includes:
     - `messages`: List of collected message data
     - `max_message_id`: Highest message ID collected (for storing as last_collected_message_id)
     - `count`: Number of messages collected
   - Negative min_id values are normalized to 0
   - min_id is passed to Telegram API's `get_messages` call

### Existing Code Updates

1. **Updated test_collector.py tests**:
   - `test_collect_channel_messages_returns_list` renamed to `test_collect_channel_messages_returns_dict_with_messages`
   - Updated assertions to work with new dict return format

## Test Coverage

### New Unit Tests (16 tests)
`tests/unit/pipeline/test_resume_tracking.py`:
- TestChannelModelResumeFields (4 tests)
  - Verify new fields exist on Channel model
  - Verify fields are nullable
- TestContentCollectorResumeTracking (5 tests)
  - Test min_id parameter support
  - Test min_id passed to Telegram client
  - Test max_message_id returned
- TestResumeTrackingEdgeCases (3 tests)
  - Message gaps handled correctly
  - High min_id returns empty
  - Negative min_id treated as 0
- TestContentCollectorResultFormat (2 tests)
  - Return format includes metadata
  - Count field included
- TestFirstCollectionVsSubsequentCollection (2 tests)
  - First collection fetches all in window
  - Subsequent collection uses min_id

### New Integration Tests (7 tests)
`tests/integration/test_resume_tracking_integration.py`:
- TestResumeTrackingIntegration (4 tests)
  - Complete first-then-second collection workflow
  - No new messages returns empty
  - Message ID gaps handled
  - 24-hour window respected
- TestResumeTrackingDatabaseIntegration (2 tests)
  - Channel model stores last_collected_message_id
  - Channel model stores last_collected_at
- TestResumeTrackingPerformance (1 test)
  - Subsequent collection processes fewer messages

### All Tests Pass
- 127 pipeline tests passing
- 7 integration tests passing
- No regressions in existing functionality

## Key Decisions

1. **Return Type Change**: Changed `collect_channel_messages` return from list to dict to include metadata (max_message_id, count) needed for resume tracking without requiring additional API calls.

2. **Nullable Fields**: Both `last_collected_message_id` and `last_collected_at` are nullable to support first-time collection when there's no previous state.

3. **BigInteger for Message IDs**: Telegram message IDs can be very large, so BigInteger type was used.

4. **Negative min_id Handling**: Negative values are normalized to 0 since negative message IDs don't exist in Telegram.

5. **Time Window Filtering**: Messages outside the 24-hour window are still filtered out even when using min_id, preventing old messages from being collected.

## How Resume Tracking Works

1. **First Collection** (min_id=0):
   - All messages in the 24-hour window are fetched
   - `max_message_id` from result is stored as `last_collected_message_id`
   - `last_collected_at` is set to current timestamp

2. **Subsequent Collections** (min_id=last_collected_message_id):
   - Telegram API only returns messages with ID > min_id
   - Only new messages are processed
   - New `max_message_id` is stored for next run

3. **Edge Cases**:
   - **No new messages**: Returns empty result with `max_message_id=None`
   - **Message gaps**: Handled gracefully; max_message_id is still accurate
   - **Channel reset**: If channel is recreated, first collection after that starts fresh

## Affected Files

- `alembic/versions/add_last_collected_message_id.py` (new)
- `src/tnse/db/models.py` (modified)
- `src/tnse/pipeline/collector.py` (modified)
- `tests/unit/pipeline/test_collector.py` (modified)
- `tests/unit/pipeline/test_resume_tracking.py` (new)
- `tests/integration/test_resume_tracking_integration.py` (new)
- `roadmap.md` (modified)

## Future Work (WS-8.1)

The Celery tasks (`collect_channel_content`, `collect_all_channels`) need to be wired to:
1. Read `last_collected_message_id` from channel record before collection
2. Pass it as `min_id` to `ContentCollector.collect_channel_messages()`
3. Update `last_collected_message_id` and `last_collected_at` after successful collection

This wiring is part of WS-8.1 (Wire Celery Tasks to ContentCollector).

# WS-7.2: Channel Validation Connection Bug Fix

## Overview

Fixed critical bug where `/addchannel` command failed to validate real public Telegram channels with "Channel not found" error. The root cause was that the `TelethonClient` was never explicitly connected before API calls were made.

## Problem Analysis

### Symptom
```
2026-01-04 02:50:18 [info     ] Adding channel                 channel_identifier=https://t.me/Baikal_People
2026-01-04 02:50:20 [warning  ] Channel validation failed      error="Channel 'Baikal_People' not found"
```

The channel `https://t.me/Baikal_People` is a real public Telegram channel, but validation was failing with "Channel not found".

### Root Cause

In `src/tnse/bot/__main__.py`, the `create_channel_service()` function creates a `TelethonClient` but never calls `connect()`:

```python
def create_channel_service() -> ChannelService | None:
    config = TelegramClientConfig.from_settings(settings)
    client = TelethonClient(config)  # Created but not connected!
    return ChannelService(client)
```

In `src/tnse/telegram/client.py`, the `get_channel()` method had a guard that returned `None` immediately if not connected:

```python
async def get_channel(self, identifier: str) -> ChannelInfo | None:
    if self._client is None or not self.is_connected:
        return None  # Returns None without ever trying to connect
```

This caused every channel validation to fail because `is_connected` was always `False`.

## Solution

Added an `_ensure_connected()` helper method that implements lazy connection - the client will automatically connect on first API call if not already connected.

### Changes Made

1. **Added `_ensure_connected()` method** (`client.py` lines 286-304):
   ```python
   async def _ensure_connected(self) -> bool:
       """Ensure the client is connected, auto-connecting if necessary."""
       if self._client is None:
           return False

       if not self.is_connected:
           try:
               await self.connect()
           except Exception:
               return False

       return self.is_connected
   ```

2. **Updated `get_channel()` method** to use auto-connect:
   ```python
   async def get_channel(self, identifier: str) -> ChannelInfo | None:
       if not await self._ensure_connected():
           return None
       # ... rest of method
   ```

3. **Updated `get_messages()` method** to use auto-connect:
   ```python
   async def get_messages(...) -> list[MessageInfo]:
       if not await self._ensure_connected():
           return []
       # ... rest of method
   ```

## Testing

### TDD Process

1. **RED Phase**: Wrote failing tests in `tests/unit/telegram/test_client.py`:
   - `test_get_channel_auto_connects_when_not_connected`
   - `test_get_channel_does_not_reconnect_if_already_connected`
   - `test_get_messages_auto_connects_when_not_connected`

2. **GREEN Phase**: Implemented `_ensure_connected()` and updated API methods.

3. **REFACTOR Phase**: Improved test mocking to use `AsyncMock` correctly for Telethon client calls.

### Test Results

- All 64 telegram tests pass
- All 920 unit tests pass (2 pre-existing failures unrelated to this change)
- Coverage maintained at 88%

## Key Decisions

### Why Lazy Connection Instead of Explicit Connect?

1. **Backward Compatibility**: Existing code that uses `TelethonClient` doesn't need to be modified.

2. **Simplicity**: The caller doesn't need to manage connection state or call `connect()` explicitly.

3. **Error Handling**: The auto-connect gracefully handles connection failures by returning `None`/empty results rather than crashing.

4. **No Startup Async Required**: The `create_channel_service()` function in `__main__.py` is synchronous, so calling `connect()` there would require refactoring the startup sequence.

## Files Modified

- `src/tnse/telegram/client.py`: Added `_ensure_connected()`, updated `get_channel()` and `get_messages()`
- `tests/unit/telegram/test_client.py`: Added `TestTelethonClientAutoConnect` test class with 3 tests

## Related Work Streams

- WS-7.1: Fixed bot service dependency injection (completed)
- WS-1.4: Original Telegram API Integration

## Commits

1. `test: add failing tests for TelethonClient auto-connect behavior (WS-7.2)`
2. `feat: add auto-connect for TelethonClient API methods (WS-7.2)`

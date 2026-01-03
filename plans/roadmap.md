# Roadmap

## Batch 7.1 (Current) - Critical Bug Fix

### Phase 7.1.1: Fix Bot Service Dependency Injection Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Investigate why channel_service is None (missing TELEGRAM_API_ID/TELEGRAM_API_HASH)
  - [x] Add startup validation in __main__.py to check required vs optional services
  - [x] Log clear warning at startup if Telegram API credentials are missing
  - [x] Update channel_handlers.py error message to indicate configuration issue
  - [x] Add startup check with helpful error message for missing credentials
  - [x] Add unit tests for service injection scenarios
  - [x] Update docs/BOT_TROUBLESHOOTING.md with this issue and solution
- **Effort:** S
- **Done When:**
  - /addchannel command works when Telegram API credentials are configured
  - Clear error message shown at startup if credentials are missing
  - Helpful error message to user if channel commands used without proper config
  - Bot gracefully handles missing optional services
  - Unit tests verify dependency injection behavior

**Root Cause Analysis:**
```
File: src/tnse/bot/__main__.py

def create_channel_service() -> ChannelService | None:
    settings = get_settings()

    # THIS CHECK CAUSES channel_service TO BE None
    if not settings.telegram.api_id or not settings.telegram.api_hash:
        logger.warning("Telegram API credentials not configured...")
        return None  # <-- Returns None, not injected into bot_data

    config = TelegramClientConfig.from_settings(settings)
    client = TelethonClient(config)
    return ChannelService(client)
```

```
File: src/tnse/bot/application.py

def create_bot_application(...):
    # Only injects if not None - so channel_service is never added
    if channel_service is not None:
        application.bot_data["channel_service"] = channel_service
```

```
File: src/tnse/bot/channel_handlers.py

async def addchannel_command(...):
    channel_service = context.bot_data.get("channel_service")  # Returns None
    db_session_factory = context.bot_data.get("db_session_factory")

    if not channel_service or not db_session_factory:
        # THIS ERROR IS SHOWN
        logger.error("Channel service or database not configured in bot_data")
        return
```

**Solution Approach:**
1. Add startup validation that clearly logs which services are available
2. Improve error messages in channel_handlers.py to explain the configuration requirement
3. Add documentation for required environment variables
4. Consider adding a /status command to show service availability

---

---

## Batch 7.2 (Complete) - Channel Validation Connection Bug

### Phase 7.2.1: Fix TelethonClient Not Connected Bug
- **Status:** Complete
- **Started:** 2026-01-04
- **Completed:** 2026-01-04
- **Tasks:**
  - [x] Write failing test reproducing the connection bug
  - [x] Fix TelethonClient to auto-connect when get_channel is called
  - [x] Fix TelethonClient to auto-connect when get_messages is called
  - [x] Update devlog with fix details
- **Effort:** S
- **Done When:**
  - /addchannel command successfully validates real public channels
  - Client auto-connects when API calls require connection
  - All existing tests pass (920 passed, 2 pre-existing failures unrelated to this fix)

**Root Cause Analysis:**
```
File: src/tnse/telegram/client.py (lines 286-296)

async def get_channel(self, identifier: str) -> ChannelInfo | None:
    if self._client is None or not self.is_connected:
        return None  # <-- RETURNS None IMMEDIATELY IF NOT CONNECTED
```

```
File: src/tnse/bot/__main__.py (lines 89-106)

def create_channel_service() -> ChannelService | None:
    config = TelegramClientConfig.from_settings(settings)
    client = TelethonClient(config)  # <-- CLIENT CREATED BUT NEVER CONNECTED
    return ChannelService(client)
```

The TelethonClient is instantiated but `connect()` is never called. When `get_channel()`
is called, it checks `self.is_connected` which is `False`, so it returns `None` immediately
without ever calling the Telegram API.

**Solution Approach:**
1. Modify `get_channel()` and `get_messages()` to auto-connect if not already connected
2. The client should lazily connect on first API call
3. Alternative: Connect in `create_channel_service()` - but this requires async startup

---

## Backlog

- [ ] Phase 5 LLM Integration (optional)
- [ ] Additional bot UX improvements
- [ ] Performance optimization for large channel lists
- [ ] Add /status command to show service health

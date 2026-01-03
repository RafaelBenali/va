# Roadmap

## Batch 7.1 (Current) - Critical Bug Fix

### Phase 7.1.1: Fix Bot Service Dependency Injection Bug
- **Status:** In Progress
- **Started:** 2026-01-04
- **Tasks:**
  - [ ] Investigate why channel_service is None (missing TELEGRAM_API_ID/TELEGRAM_API_HASH)
  - [ ] Add startup validation in __main__.py to check required vs optional services
  - [ ] Log clear warning at startup if Telegram API credentials are missing
  - [ ] Update channel_handlers.py error message to indicate configuration issue
  - [ ] Add startup check with helpful error message for missing credentials
  - [ ] Add unit tests for service injection scenarios
  - [ ] Update docs/BOT_TROUBLESHOOTING.md with this issue and solution
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

## Backlog

- [ ] Phase 5 LLM Integration (optional)
- [ ] Additional bot UX improvements
- [ ] Performance optimization for large channel lists
- [ ] Add /status command to show service health

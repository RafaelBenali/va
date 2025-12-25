# WS-4.2: Production Environment Configuration

## Work Stream Information

| Field | Value |
|-------|-------|
| **ID** | WS-4.2 |
| **Name** | Production Environment Setup |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |
| **Status** | Complete |

## Summary

Implemented production-ready environment configuration for Render.com deployment. This work stream focused on ensuring the config module properly handles Render's URL-based configuration (DATABASE_URL, REDIS_URL) and added support for webhook-based bot operation.

## Key Decisions

### 1. DATABASE_URL and REDIS_URL Parsing

**Decision**: Parse DATABASE_URL and REDIS_URL at configuration load time, extracting components into individual fields.

**Rationale**: Render provides a single DATABASE_URL connection string for managed PostgreSQL, but the existing codebase used individual POSTGRES_* variables. Rather than refactor all database consumers, the config module now parses the URL and populates the individual fields. This provides:
- Backward compatibility with existing code
- Seamless integration with Render's managed databases
- URL-based config takes precedence over individual variables

**Implementation**: Added `@model_validator(mode="before")` to DatabaseSettings and RedisSettings classes that parse the URL using `urllib.parse.urlparse`.

### 2. TLS Support for Redis

**Decision**: Automatically detect TLS from `rediss://` scheme and add `use_tls` field.

**Rationale**: Render may provide TLS-enabled Redis URLs. The `rediss://` scheme indicates TLS should be used. The config module now:
- Detects `rediss://` scheme and sets `use_tls=True`
- Generates correct URL scheme when building connection strings
- Maintains backward compatibility (defaults to `use_tls=False`)

### 3. Webhook Mode Configuration

**Decision**: Add BOT_POLLING_MODE and TELEGRAM_WEBHOOK_URL to support production webhook operation.

**Rationale**: For production deployment, webhook mode is preferred because:
- Telegram pushes updates to your server (more efficient)
- No continuous polling connection needed
- Better for containerized/serverless environments
- Reduces API calls to Telegram

**Implementation**:
- Added `TELEGRAM_WEBHOOK_URL` to TelegramSettings
- Added `BOT_POLLING_MODE` to main Settings
- Updated `create_bot_config()` to read these settings

## Implementation Details

### Files Modified

1. **src/tnse/core/config.py**
   - Added DATABASE_URL parsing in DatabaseSettings
   - Added REDIS_URL parsing in RedisSettings
   - Added `use_tls` field to RedisSettings
   - Added `webhook_url` to TelegramSettings
   - Added `bot_polling_mode` to Settings

2. **src/tnse/bot/config.py**
   - Updated `create_bot_config()` to read polling_mode and webhook_url from Settings

3. **.env.render.example**
   - Added comprehensive production configuration documentation
   - Added BOT_POLLING_MODE and TELEGRAM_WEBHOOK_URL
   - Added required variables checklist
   - Documented URL parsing behavior

4. **.env.example**
   - Added BOT_POLLING_MODE and TELEGRAM_WEBHOOK_URL for local development

5. **docs/DEPLOYMENT.md**
   - Added Render.com deployment section
   - Added required/auto-provided variable tables
   - Added Render deployment checklist
   - Documented URL parsing behavior

### Tests Added

1. **tests/unit/test_config.py**
   - `test_database_url_parsing_from_environment`
   - `test_database_url_with_render_internal_format`
   - `test_database_url_takes_precedence_over_individual_vars`
   - `test_database_url_with_special_characters_in_password`
   - `test_redis_url_parsing_from_environment`
   - `test_redis_url_with_password`
   - `test_redis_url_with_database_number`
   - `test_redis_url_takes_precedence_over_individual_vars`
   - `test_rediss_url_for_tls`

2. **tests/unit/bot/test_config.py**
   - `test_bot_config_from_env_webhook_mode`
   - `test_bot_config_from_env_polling_mode`
   - `test_bot_config_webhook_url_required_when_not_polling`

## Challenges Encountered

### 1. URL-Encoded Passwords

**Challenge**: DATABASE_URL may contain passwords with special characters that are URL-encoded.

**Solution**: Use `urllib.parse.unquote()` to decode the password after extracting from URL.

### 2. Pydantic Model Validator Timing

**Challenge**: Needed to parse URL before field validation but after environment variables are read.

**Solution**: Used `@model_validator(mode="before")` which runs before field validation, allowing URL components to be set before defaults are applied.

### 3. TLS Detection

**Challenge**: Needed to detect TLS requirement from URL scheme without breaking existing code.

**Solution**: Added optional `use_tls` field that defaults to False, set to True only when `rediss://` scheme is detected.

## Test Coverage

All 669 tests pass after implementation:
- Configuration tests: 24 tests (100% pass)
- Bot config tests: 17 tests (100% pass)
- No regressions in existing tests

## Documentation

- `.env.render.example`: Complete reference for Render deployment
- `docs/DEPLOYMENT.md`: Render.com deployment guide with checklists
- `.env.example`: Updated with new webhook configuration

## Next Steps

WS-4.3: Deployment Documentation will provide a comprehensive step-by-step guide for deploying to Render.com, including:
- Dashboard configuration screenshots/instructions
- Troubleshooting guide for common Render issues
- Scaling and cost estimation notes

# TNSE Bot Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Telegram News Search Engine (TNSE) bot.

## Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Common Error Messages](#common-error-messages)
3. [Connection Issues](#connection-issues)
4. [Search Problems](#search-problems)
5. [Channel Issues](#channel-issues)
6. [Export Problems](#export-problems)
7. [Performance Issues](#performance-issues)
8. [Recovery Procedures](#recovery-procedures)

---

## Quick Diagnostic Commands

Use these commands to quickly diagnose issues:

| Command | What It Checks |
|---------|----------------|
| `/settings` | Access mode, your user ID, connection mode |
| `/health` | Status of all monitored channels |
| `/channels` | List of active channels |
| `/help` | Verify bot is responding |

---

## Common Error Messages

### "Access denied"

**Cause:** Your Telegram user ID is not in the allowed users list.

**Solution:**
1. Use `/settings` to see your user ID
2. Contact your bot administrator to add your ID
3. Administrator adds your ID to `BOT_ALLOWED_USERS` environment variable

### "Search service is not available"

**Cause:** Backend search service is not connected.

**Solutions:**
1. Wait a few minutes and try again
2. Contact administrator to check service status
3. Administrator checks: `docker compose ps` to verify all services are running

### "Channel management is not configured"

**Cause:** Telegram API credentials (TELEGRAM_API_ID and TELEGRAM_API_HASH) are not configured.

**Solutions:**
1. **For administrators:** Set the `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` environment variables
2. Get API credentials from [my.telegram.org](https://my.telegram.org)
3. Restart the bot after setting the environment variables

**How to get Telegram API credentials:**
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram phone number
3. Click on "API development tools"
4. Create a new application (if you don't have one)
5. Copy the `api_id` and `api_hash` values

**Note:** This error appears when trying to use `/addchannel` or `/import` commands. Other bot features like `/search` and `/channels` may still work if the database is configured.

### "Channel service is not available" (legacy message)

**Cause:** Channel validation service is not connected. This is typically due to missing Telegram API credentials.

**Solutions:**
1. Check if `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set
2. Contact administrator to verify Telegram API credentials
3. Check if Telegram is experiencing outages

### "No results found"

**Cause:** No matching content in the last 24 hours.

**Solutions:**
1. Try different or broader keywords
2. Check if channels are being monitored: `/channels`
3. Verify channels are healthy: `/health`
4. Wait for content to be collected (new channels need time)

### "Rate limited. Please try again later."

**Cause:** Too many requests to Telegram API.

**Solutions:**
1. Wait 30-60 seconds before retrying
2. Reduce frequency of operations
3. For bulk imports, space out operations

### "Invalid channel format"

**Cause:** Channel identifier is malformed.

**Valid formats:**
```
@channel_username
https://t.me/channel_username
t.me/channel_username
channel_username
```

**Invalid formats:**
```
channel username (spaces not allowed)
http://t.me/channel (must be https)
@Channel_With_Caps (case sensitive)
```

### "Channel not found"

**Cause:** Channel does not exist or is private.

**Solutions:**
1. Verify the channel username is correct
2. Ensure the channel is public (not private)
3. Check if the channel has been deleted or renamed
4. Try accessing the channel directly in Telegram first

---

## Connection Issues

### Bot Not Responding

**Symptoms:**
- Messages show single checkmark only
- No response to any commands
- Bot appears offline

**Diagnostic Steps:**

1. **Check bot status on Telegram:**
   - Search for your bot
   - Check if it shows "last seen recently"

2. **Administrator checks:**
   ```bash
   # Check if bot container is running
   docker compose ps

   # View recent logs
   docker compose logs --tail=100 bot

   # Restart bot service
   docker compose restart bot
   ```

3. **Common causes:**
   - Bot token revoked or changed
   - Network connectivity issues
   - Container crashed
   - Out of memory

### Delayed Responses

**Symptoms:**
- Commands take 10+ seconds to respond
- Timeout errors

**Solutions:**

1. **Check database connection:**
   ```bash
   docker compose exec db pg_isready -U tnse_user -d tnse
   ```

2. **Check Redis connection:**
   ```bash
   docker compose exec redis redis-cli ping
   ```

3. **Check for high CPU/memory:**
   ```bash
   docker stats
   ```

### Webhook Connection Failed (Webhook Mode)

**Symptoms:**
- Bot works initially then stops
- "Webhook error" in logs

**Solutions:**

1. Verify SSL certificate is valid
2. Check firewall allows incoming connections on webhook port
3. Verify `BOT_WEBHOOK_URL` matches your server's public URL
4. Test webhook endpoint:
   ```bash
   curl -k https://your-domain.com:8443/webhook
   ```

---

## Search Problems

### Empty Search Results

**When expected results exist but none are returned:**

1. **Check keyword matching:**
   - Search is case-insensitive
   - Try single keywords first
   - Try both English and Cyrillic characters

2. **Check time window:**
   - Default search is last 24 hours
   - Content must be within this window

3. **Check channel status:**
   ```
   /health
   ```
   - Channels should show "Healthy" status

4. **Verify content collection:**
   - New channels need time for initial collection
   - Wait 15-30 minutes after adding a channel

### Search Results Not Updating

**Old content appears but new posts are missing:**

1. **Check collection pipeline:**
   ```bash
   docker compose logs --tail=50 worker
   ```

2. **Verify Celery workers are running:**
   ```bash
   docker compose exec worker celery -A src.tnse.core.celery_app status
   ```

3. **Check for collection errors in logs:**
   ```bash
   docker compose logs bot | grep ERROR
   ```

### Pagination Not Working

**Next/Previous buttons don't respond:**

1. **Refresh the search:**
   - Run the search again with `/search`

2. **Check session data:**
   - Session data may have expired
   - Re-run the search to refresh

3. **Report to administrator:**
   - This may indicate a callback handler issue

---

## Channel Issues

### Cannot Add Channel

**"Cannot add channel" or "Validation failed":**

1. **Verify channel is public:**
   - Check channel link in Telegram
   - Private channels cannot be added

2. **Check username spelling:**
   - Usernames are case-sensitive
   - Include the @ symbol

3. **Verify channel exists:**
   - Try opening the channel in Telegram
   - Channel may have been deleted

4. **Rate limit:**
   - Wait 60 seconds between add attempts
   - Bulk import may trigger limits

### Channel Shows Unhealthy Status

**`/health` shows warnings or errors:**

| Status | Meaning | Action |
|--------|---------|--------|
| `rate_limited` | Telegram temporarily blocked access | Wait 1-24 hours |
| `inaccessible` | Channel made private or username changed | Verify and re-add |
| `removed` | Channel was deleted from Telegram | Remove from monitoring |

**Recovery steps:**
1. Check channel status in Telegram
2. If channel is still public, wait for automatic recovery
3. If channel changed username, remove and re-add with new username
4. If channel is gone, remove it: `/removechannel @oldname`

### Duplicate Channel Error

**"Channel already exists":**

1. The channel is already being monitored
2. Check with `/channels` to see current list
3. Use `/channelinfo @name` to verify

---

## Export Problems

### Export File Empty

**Exported file has no content:**

1. **Run a search first:**
   ```
   /search corruption news
   /export csv
   ```

2. **Check search results:**
   - Export uses results from last search
   - If search found nothing, export is empty

### Export Download Failed

**File fails to download:**

1. **Check file size:**
   - Telegram has 50MB file limit
   - Large exports may fail

2. **Retry the export:**
   - Network issues can cause failures
   - Try exporting again

3. **Try different format:**
   - If CSV fails, try JSON: `/export json`

### Invalid File Format

**Exported file is corrupted:**

1. **Check encoding:**
   - Files are UTF-8 encoded
   - Some applications need encoding specified

2. **For CSV in Excel:**
   - Import as data (don't open directly)
   - Specify UTF-8 encoding

3. **For JSON:**
   - Use a JSON viewer/validator
   - Check for truncation

---

## Performance Issues

### Slow Searches

**Searches taking more than 5 seconds:**

1. **Check database performance:**
   ```bash
   docker compose exec db pg_top
   ```

2. **Check index health:**
   - Administrator should run `ANALYZE` on tables

3. **Reduce result set:**
   - More specific keywords = faster search

### High Memory Usage

**Bot or database using too much memory:**

1. **Check container memory:**
   ```bash
   docker stats
   ```

2. **Restart services:**
   ```bash
   docker compose restart
   ```

3. **Increase container memory limits:**
   - Update `docker-compose.yml` memory limits

### Frequent Timeouts

**Operations timing out regularly:**

1. **Check network latency:**
   ```bash
   ping api.telegram.org
   ```

2. **Check database load:**
   - High concurrent queries can cause timeouts
   - Consider scaling database

3. **Check Redis connection:**
   - Task queue issues can cause timeouts

---

## Recovery Procedures

### Complete Bot Restart

```bash
# Stop all services
docker compose down

# Remove old containers
docker compose rm -f

# Rebuild and start
docker compose up -d --build
```

### Database Recovery

**If database is corrupted or slow:**

```bash
# Backup first
docker compose exec db pg_dump -U tnse_user tnse > backup.sql

# Restart database
docker compose restart db

# Check tables
docker compose exec db psql -U tnse_user -d tnse -c "\dt"
```

### Reset Bot State

**If bot is in inconsistent state:**

```bash
# Restart just the bot
docker compose restart bot

# Clear Redis cache (caution: clears all cached data)
docker compose exec redis redis-cli FLUSHALL
```

### Re-sync Channels

**If channel data is out of sync:**

1. Export current channel list (manually or via database)
2. Remove all channels
3. Re-import channels using `/import`

---

## Getting Administrator Help

When contacting your administrator, include:

1. **Your Telegram user ID** (from `/settings`)
2. **Exact error message** (screenshot if possible)
3. **Steps to reproduce** the issue
4. **Timestamp** when the issue occurred

---

## Startup Service Status

When the bot starts, it logs the status of all services. Look for these log messages:

### All Services Available (Normal)
```
INFO  Channel service initialized status=available feature="/addchannel, /channelinfo enabled"
INFO  Database connection initialized status=available
```

### Channel Service Unavailable
```
WARNING  Channel service not available - /addchannel command will not work
         hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH to enable channel management"
         disabled_commands=["/addchannel", "/import"]
```

**Resolution:**
1. Set `TELEGRAM_API_ID` environment variable
2. Set `TELEGRAM_API_HASH` environment variable
3. Restart the bot

### Database Unavailable
```
WARNING  Database not available - channel and search features will not work
         hint="Check database configuration (POSTGRES_* environment variables)"
```

**Resolution:**
1. Verify PostgreSQL is running: `docker compose ps`
2. Check database configuration in `.env` file
3. Verify connectivity: `docker compose exec db pg_isready`

---

## Log Analysis for Administrators

### Finding User Issues

```bash
# Find all activity for a user
docker compose logs bot | grep "user_id.*123456789"

# Find all errors
docker compose logs bot | grep ERROR

# Find rate limit issues
docker compose logs bot | grep -i "rate\|limit\|retry"
```

### Common Log Patterns

| Pattern | Meaning |
|---------|---------|
| `RetryAfter` | Telegram rate limit hit |
| `NetworkError` | Connection to Telegram failed |
| `BadRequest` | Invalid Telegram API request |
| `Unauthorized` | Bot token invalid or revoked |
| `TimedOut` | Request took too long |

### Monitoring Commands

```bash
# Real-time log monitoring
docker compose logs -f bot

# Error summary
docker compose logs bot 2>&1 | grep ERROR | wc -l

# Health check
docker compose ps
```

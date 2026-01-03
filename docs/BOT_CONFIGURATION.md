# TNSE Bot Configuration Guide

This document explains how to configure the Telegram News Search Engine (TNSE) bot.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Access Control](#access-control)
3. [Connection Modes](#connection-modes)
4. [Database Configuration](#database-configuration)
5. [Rate Limiting](#rate-limiting)
6. [Logging](#logging)
7. [Best Practices](#best-practices)

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather (required for bot to start) | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |

### Required for Channel Management

The following variables are **required for `/addchannel` and `/import` commands**. Without these, the bot will start but channel management features will be disabled:

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_API_ID` | Telegram API ID from my.telegram.org | `12345678` |
| `TELEGRAM_API_HASH` | Telegram API hash from my.telegram.org | `abcdef1234567890abcdef1234567890` |

**Note:** If these are not set, the bot will log a warning at startup and channel management commands will show a configuration error message to users.

**How to get Telegram API credentials:**
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram phone number
3. Click on "API development tools"
4. Create a new application (if needed)
5. Copy the `api_id` and `api_hash` values

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment: `development`, `staging`, `production` |
| `DEBUG` | `true` | Enable debug mode (set to `false` in production) |
| `LOG_LEVEL` | `DEBUG` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL server hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL server port |
| `POSTGRES_DB` | `tnse` | Database name |
| `POSTGRES_USER` | `tnse_user` | Database username |
| `POSTGRES_PASSWORD` | - | Database password (required) |
| `DATABASE_URL` | - | Full database URL (overrides individual settings) |

### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_URL` | - | Full Redis URL (overrides individual settings) |

### Bot-Specific Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_ALLOWED_USERS` | - | Comma-separated list of allowed Telegram user IDs |
| `BOT_POLLING_MODE` | `true` | Use polling mode (`true`) or webhook mode (`false`) |
| `BOT_WEBHOOK_URL` | - | Webhook URL (required if polling mode is false) |
| `BOT_WEBHOOK_PORT` | `8443` | Port for webhook server |

---

## Access Control

### Restricting Bot Access

By default, the bot is open to all users. To restrict access to specific users:

1. Get the Telegram user IDs of authorized users
2. Set the `BOT_ALLOWED_USERS` environment variable

```bash
# Single user
BOT_ALLOWED_USERS=123456789

# Multiple users
BOT_ALLOWED_USERS=123456789,987654321,555555555
```

### Finding Your Telegram User ID

Users can find their Telegram user ID by:

1. Messaging the TNSE bot and using `/settings`
2. Using a third-party bot like @userinfobot
3. Checking the bot logs when they send a message

### Access Control Behavior

When access control is enabled:
- Unauthorized users receive "Access denied" message
- All command attempts are logged with user ID
- The `/settings` command shows access mode status

---

## Connection Modes

### Polling Mode (Default)

Polling mode is simpler to set up and works behind firewalls:

```bash
BOT_POLLING_MODE=true
```

**Advantages:**
- No incoming firewall rules needed
- Works on any server
- Simpler to deploy

**Disadvantages:**
- Slightly higher latency
- More API calls to Telegram

### Webhook Mode

Webhook mode is more efficient for high-traffic bots:

```bash
BOT_POLLING_MODE=false
BOT_WEBHOOK_URL=https://your-domain.com/webhook
BOT_WEBHOOK_PORT=8443
```

**Requirements:**
- Valid SSL certificate
- Public domain or IP address
- Incoming port open (8443, 443, 80, or 88)

**Advantages:**
- Lower latency
- More efficient resource usage
- Better for high-traffic bots

---

## Database Configuration

### Local Development

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tnse_dev
POSTGRES_USER=tnse_user
POSTGRES_PASSWORD=your_dev_password
```

### Production (Using DATABASE_URL)

```bash
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
```

### Connection Pool Settings

The application uses SQLAlchemy with connection pooling. Default settings:

- Pool size: 5 connections
- Max overflow: 10 connections
- Pool timeout: 30 seconds
- Pool recycle: 1800 seconds (30 minutes)

---

## Rate Limiting

### Telegram API Rate Limits

The bot respects Telegram's rate limits automatically:

| Operation | Limit |
|-----------|-------|
| Messages per second | ~30 per second per bot |
| Bulk operations | 20 requests per minute |
| Channel info requests | 20 per minute |

### Bot Rate Limiting Behavior

When rate limited:

1. Bot catches `RetryAfter` error from Telegram
2. User receives friendly message about temporary delay
3. Operation can be retried after the specified wait time
4. All rate limit events are logged

### Handling Rate Limits

If you encounter frequent rate limits:

1. Reduce the number of concurrent operations
2. Space out bulk imports over time
3. Consider using fewer channels

---

## Logging

### Log Levels

| Level | When to Use |
|-------|-------------|
| `DEBUG` | Development - verbose output |
| `INFO` | Production - normal operations |
| `WARNING` | Potential issues |
| `ERROR` | Errors that need attention |
| `CRITICAL` | System failures |

### Log Format

Logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2025-12-26T10:30:00.000Z",
  "level": "INFO",
  "logger": "tnse.bot.handlers",
  "message": "Search completed",
  "user_id": 123456789,
  "query": "corruption news",
  "result_count": 47
}
```

### Viewing Logs

```bash
# View all logs
docker compose logs -f bot

# View only error logs
docker compose logs bot | grep ERROR

# View logs for specific user
docker compose logs bot | grep "user_id.*123456789"
```

---

## Best Practices

### Security

1. **Never commit `.env` files** to version control
2. **Use strong passwords** for database and Redis
3. **Rotate API keys** periodically
4. **Restrict access** using `BOT_ALLOWED_USERS` in production
5. **Use SSL** for webhook mode

### Performance

1. **Use connection pooling** (enabled by default)
2. **Monitor rate limits** in logs
3. **Scale horizontally** by running multiple workers
4. **Use Redis** for caching and task queue

### Monitoring

1. **Check `/health`** command regularly
2. **Monitor logs** for errors
3. **Set up alerts** for critical errors
4. **Review rate limit warnings**

### Backup

1. **Backup PostgreSQL** daily
2. **Export channel list** periodically using `/export`
3. **Keep configuration** in version control (without secrets)

---

## Example Configurations

### Development Environment

```bash
# .env.development
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

TELEGRAM_BOT_TOKEN=your_dev_bot_token
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tnse_dev
POSTGRES_USER=tnse_user
POSTGRES_PASSWORD=dev_password

REDIS_HOST=localhost
REDIS_PORT=6379

BOT_POLLING_MODE=true
```

### Production Environment

```bash
# .env.production
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

TELEGRAM_BOT_TOKEN=your_prod_bot_token
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

DATABASE_URL=postgresql://user:password@db.example.com:5432/tnse?sslmode=require
REDIS_URL=redis://user:password@redis.example.com:6379

BOT_ALLOWED_USERS=123456789,987654321
BOT_POLLING_MODE=false
BOT_WEBHOOK_URL=https://bot.example.com/webhook
BOT_WEBHOOK_PORT=8443
```

---

## Troubleshooting Configuration Issues

### Bot Not Responding

1. Check `TELEGRAM_BOT_TOKEN` is correct
2. Verify bot is not blocked or deactivated
3. Check logs for connection errors

### Database Connection Failed

1. Verify PostgreSQL is running
2. Check credentials in configuration
3. Ensure database exists
4. Check network connectivity

### Rate Limit Errors

1. Reduce concurrent operations
2. Check for runaway loops in code
3. Review operation frequency

### Access Denied Errors

1. Verify user ID is in `BOT_ALLOWED_USERS`
2. Check for typos in user ID list
3. Use `/settings` to confirm your user ID

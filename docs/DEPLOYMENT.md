# TNSE Deployment Guide

This guide covers deploying the Telegram News Search Engine (TNSE) bot to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Configuration](#environment-configuration)
4. [Docker Deployment](#docker-deployment)
5. [Manual Deployment](#manual-deployment)
6. [Database Setup](#database-setup)
7. [Running the Bot](#running-the-bot)
8. [Production Considerations](#production-considerations)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- Python 3.10 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Docker and Docker Compose (for containerized deployment)

### Telegram Credentials

1. **Bot Token** from [@BotFather](https://t.me/BotFather) (see [BOTFATHER_SETUP.md](BOTFATHER_SETUP.md))
2. **API ID and Hash** from [my.telegram.org](https://my.telegram.org) for MTProto access

---

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd va

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# (At minimum, set TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH)

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

### Using Make Commands

```bash
# Setup environment
make setup

# Start infrastructure (PostgreSQL, Redis)
make docker-up

# Run database migrations
make db-migrate

# Start the bot
make run-dev
```

---

## Environment Configuration

### Required Variables

Copy `.env.example` to `.env` and configure these essential variables:

```bash
# Application
APP_NAME=tnse
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Telegram MTProto (for channel access)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tnse
POSTGRES_USER=tnse
POSTGRES_PASSWORD=secure_password_here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Optional Variables

```bash
# Access Control (comma-separated Telegram user IDs)
ALLOWED_TELEGRAM_USERS=123456789,987654321

# Bot Mode
BOT_POLLING_MODE=true  # Use false for webhook mode
BOT_WEBHOOK_URL=https://your-domain.com/webhook

# Celery (Background Tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# LLM Mode (Optional)
LLM_ENABLED=false
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
```

---

## Docker Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-tnse}
      POSTGRES_USER: ${POSTGRES_USER:-tnse}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tnse}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env
    restart: unless-stopped
    command: python -m src.tnse.bot

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env
    restart: unless-stopped
    command: celery -A src.tnse.core.celery_app worker -l info

  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      - worker
    env_file:
      - .env
    restart: unless-stopped
    command: celery -A src.tnse.core.celery_app beat -l info

volumes:
  postgres_data:
  redis_data:
```

### Deployment Commands

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=3

# Stop services
docker-compose -f docker-compose.prod.yml down
```

---

## Manual Deployment

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Set Up Database

```bash
# Create database
createdb tnse

# Run migrations
alembic upgrade head
```

### 5. Start Services

```bash
# Start the bot
python -m src.tnse.bot

# In separate terminals:

# Start Celery worker
celery -A src.tnse.core.celery_app worker -l info

# Start Celery beat scheduler
celery -A src.tnse.core.celery_app beat -l info
```

---

## Database Setup

### PostgreSQL Configuration

1. Create database and user:

```sql
CREATE USER tnse WITH PASSWORD 'your_secure_password';
CREATE DATABASE tnse OWNER tnse;
GRANT ALL PRIVILEGES ON DATABASE tnse TO tnse;
```

2. Enable full-text search dictionaries (for Russian/Ukrainian support):

```sql
-- Check available dictionaries
SELECT cfgname FROM pg_ts_config;

-- The application uses 'russian', 'english', and 'simple' configurations
```

### Run Migrations

```bash
# Using Alembic
alembic upgrade head

# Or using Make
make db-migrate
```

### Backup and Restore

```bash
# Backup
pg_dump -U tnse tnse > backup.sql

# Restore
psql -U tnse tnse < backup.sql
```

---

## Running the Bot

### Polling Mode (Default)

Best for development and simple deployments:

```bash
# Set in .env
BOT_POLLING_MODE=true

# Run bot
python -m src.tnse.bot
```

### Webhook Mode

Better for high-traffic production deployments:

```bash
# Set in .env
BOT_POLLING_MODE=false
BOT_WEBHOOK_URL=https://your-domain.com/webhook

# Run with a reverse proxy (nginx/caddy) handling HTTPS
```

---

## Production Considerations

### Security

1. **Secure Secrets:**
   - Never commit `.env` to version control
   - Use secrets management (Vault, AWS Secrets Manager)
   - Rotate tokens periodically

2. **Access Control:**
   - Set `ALLOWED_TELEGRAM_USERS` to restrict access
   - Monitor bot usage logs

3. **Network Security:**
   - Use HTTPS for webhooks
   - Configure firewall rules
   - Keep PostgreSQL and Redis internal

### Performance

1. **Database Indexes:**
   - Migrations include indexes for common queries
   - Monitor slow queries and add indexes as needed

2. **Redis Caching:**
   - Search results are cached for 5 minutes
   - Adjust `CACHE_TTL` in configuration

3. **Worker Scaling:**
   - Scale Celery workers based on load
   - Monitor queue depth

### High Availability

1. **Database:**
   - Use PostgreSQL replication
   - Regular backups
   - Consider managed database (RDS, Cloud SQL)

2. **Redis:**
   - Use Redis Sentinel or Redis Cluster
   - Or managed Redis (ElastiCache, Memorystore)

3. **Bot:**
   - Run multiple instances (with polling mode disabled)
   - Use load balancer with webhook mode

---

## Monitoring

### Health Checks

```bash
# Check PostgreSQL
docker exec tnse-postgres pg_isready -U tnse

# Check Redis
docker exec tnse-redis redis-cli ping

# Check bot logs
docker logs tnse-bot --tail 100
```

### Logging

Logs are written to stdout in JSON format:

```json
{
  "timestamp": "2025-12-26T10:30:00.000Z",
  "level": "INFO",
  "logger": "src.tnse.bot.handlers",
  "message": "User started bot",
  "user_id": 123456789,
  "username": "example_user"
}
```

### Metrics to Monitor

- Bot response time
- Search query count
- Database connection pool
- Redis memory usage
- Celery queue depth
- Channel health status

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Bot not responding | Check logs, verify TELEGRAM_BOT_TOKEN |
| Database connection failed | Verify POSTGRES_* environment variables |
| Channel validation fails | Check TELEGRAM_API_ID and TELEGRAM_API_HASH |
| Search returns no results | Ensure content collection is running (Celery) |
| Rate limiting errors | Reduce request frequency, check Telegram limits |

### Debug Mode

Enable debug logging:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Checking Component Status

```bash
# Bot status
curl http://localhost:8000/health  # If health endpoint is enabled

# Database connection
python -c "from src.tnse.db.base import get_engine; engine = get_engine(); print(engine.connect())"

# Redis connection
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

### Resetting the System

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart fresh
docker-compose up -d
```

---

## Render.com Deployment

### Overview

Render.com provides a simple platform for deploying TNSE with managed PostgreSQL and Redis. The project includes a `render.yaml` Blueprint for automated deployment.

### Quick Start with Render

1. **Fork/Connect Repository**: Connect your repository to Render.com
2. **Create Blueprint**: Use `render.yaml` to create all services
3. **Configure Secrets**: Set required environment variables in Dashboard

### Required Environment Variables

These must be set manually in the Render Dashboard:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `TELEGRAM_BOT_TOKEN` | Bot API token | Create bot with @BotFather |
| `TELEGRAM_API_ID` | Telegram API ID | https://my.telegram.org |
| `TELEGRAM_API_HASH` | Telegram API Hash | https://my.telegram.org |
| `TELEGRAM_WEBHOOK_URL` | Webhook endpoint | Your Render app URL + `/webhook` |

### Automatically Provided Variables

These are set automatically by Render's Blueprint:

| Variable | Source |
|----------|--------|
| `DATABASE_URL` | Managed PostgreSQL |
| `REDIS_URL` | Managed Redis |
| `SECRET_KEY` | Auto-generated |
| `PORT` | Assigned by Render |
| `CELERY_BROKER_URL` | From Redis |
| `CELERY_RESULT_BACKEND` | From Redis |

### Production Settings

The following are already configured in `render.yaml`:

```bash
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
WORKERS=2
```

### Webhook vs Polling Mode

For Render.com deployment, **webhook mode is recommended**:

```bash
BOT_POLLING_MODE=false
TELEGRAM_WEBHOOK_URL=https://tnse-web.onrender.com/webhook
```

Webhooks are more efficient because:
- Telegram pushes updates to your server
- No continuous polling connection needed
- Better for serverless/container environments

### URL Parsing

The config module automatically parses Render's URL-based configuration:

- `DATABASE_URL` is parsed into host, port, user, password, database
- `REDIS_URL` is parsed into host, port, password, database number
- `rediss://` scheme automatically enables TLS for Redis

### Render Deployment Checklist

- [ ] Repository connected to Render
- [ ] Blueprint created from `render.yaml`
- [ ] PostgreSQL database provisioned
- [ ] Redis service provisioned
- [ ] `TELEGRAM_BOT_TOKEN` set in Dashboard
- [ ] `TELEGRAM_API_ID` set in Dashboard
- [ ] `TELEGRAM_API_HASH` set in Dashboard
- [ ] `TELEGRAM_WEBHOOK_URL` set (your-app.onrender.com/webhook)
- [ ] `BOT_POLLING_MODE` set to `false`
- [ ] `ALLOWED_TELEGRAM_USERS` set (optional)
- [ ] All services showing "Live" in Dashboard
- [ ] Bot responds to /start command

See `.env.render.example` for a complete reference of all environment variables.

---

## Deployment Checklist

### General Deployment

- [ ] PostgreSQL configured and accessible
- [ ] Redis configured and accessible
- [ ] Environment variables set in `.env`
- [ ] Database migrations run
- [ ] Bot token validated with BotFather
- [ ] API ID/Hash configured for MTProto
- [ ] Access control configured (ALLOWED_TELEGRAM_USERS)
- [ ] Celery worker and beat scheduler running
- [ ] Logging configured for production
- [ ] Backup strategy in place
- [ ] Monitoring set up
- [ ] SSL/HTTPS configured (for webhook mode)

---

## Support

For issues or questions:

1. Check the logs: `docker logs tnse-bot` (or Render Dashboard logs)
2. Review this guide and troubleshooting section
3. Check the GitHub issues
4. Contact the maintainers

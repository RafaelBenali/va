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

- Python 3.12 or higher (Python 3.13 recommended)
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
```

### Groq API Configuration (LLM Features)

To enable LLM-based post enrichment and enhanced search:

```bash
# Groq API (Required for LLM features)
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=qwen-qwq-32b
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.1
GROQ_ENABLED=true
GROQ_RATE_LIMIT_RPM=30
GROQ_TIMEOUT_SECONDS=30.0
GROQ_MAX_RETRIES=3

# Enrichment Settings
ENRICHMENT_BATCH_SIZE=10
ENRICHMENT_RATE_LIMIT=10
```

**Obtaining Groq API Key:**

1. Go to [console.groq.com](https://console.groq.com)
2. Create an account or sign in
3. Navigate to API Keys section
4. Click "Create API Key"
5. Copy the key (starts with `gsk_`)
6. Add to your `.env` file as `GROQ_API_KEY`

**Free Tier Limits:**
- 30 requests per minute
- 14,400 requests per day
- Variable token limits by model

**Production Considerations:**
- Monitor usage via `/stats llm` command
- Set `ENRICHMENT_RATE_LIMIT=10` to stay well under limits
- Consider paid tier for high-volume deployments

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

Render.com provides a simple platform for deploying TNSE with managed PostgreSQL and Redis. This section provides a comprehensive guide to deploying your TNSE bot on Render.

### Table of Contents (Render)

1. [Overview](#overview-1)
2. [Prerequisites](#prerequisites-1)
3. [Step 1: Prepare Your Repository](#step-1-prepare-your-repository)
4. [Step 2: Create Render Account](#step-2-create-render-account)
5. [Step 3: Deploy with Blueprint](#step-3-deploy-with-blueprint)
6. [Step 4: Configure Environment Variables](#step-4-configure-environment-variables)
7. [Step 5: Run Database Migrations](#step-5-run-database-migrations)
8. [Step 6: Verify Deployment](#step-6-verify-deployment)
9. [Render Dashboard Guide](#render-dashboard-guide)
10. [Cost Estimation](#cost-estimation)
11. [Scaling Options](#scaling-options)
12. [Render Troubleshooting](#render-troubleshooting)

---

### Overview

The TNSE project includes a `render.yaml` Blueprint file that defines all required infrastructure:

| Service | Type | Purpose |
|---------|------|---------|
| `tnse-postgres` | Managed Database | Primary data storage |
| `tnse-redis` | Managed Redis | Cache and Celery broker |
| `tnse-web` | Web Service | FastAPI health endpoints |
| `tnse-bot` | Background Worker | Telegram bot process |
| `tnse-celery-worker` | Background Worker | Background task processing |
| `tnse-celery-beat` | Background Worker | Scheduled task scheduler |

### Prerequisites

Before deploying to Render, ensure you have:

1. **Telegram Bot Credentials**
   - Bot Token from [@BotFather](https://t.me/BotFather) (see [BOTFATHER_SETUP.md](BOTFATHER_SETUP.md))
   - API ID and API Hash from [my.telegram.org](https://my.telegram.org)

2. **Repository Access**
   - Your code pushed to GitHub, GitLab, or Bitbucket
   - The repository must contain `render.yaml` in the root directory

3. **Render Account**
   - Free tier available, but paid tier recommended for production

---

### Step 1: Prepare Your Repository

Ensure your repository contains these files:

```
your-repo/
├── render.yaml          # Blueprint specification
├── Dockerfile           # Container build instructions
├── requirements.txt     # Python dependencies
├── alembic/             # Database migrations
├── alembic.ini          # Alembic configuration
└── src/tnse/            # Application source code
```

Verify the `render.yaml` is valid:

```bash
# The file should define databases, services for redis, web, and workers
cat render.yaml
```

---

### Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Click "Get Started Free"
3. Sign up with GitHub, GitLab, or email
4. Verify your email address
5. Add a payment method (required for databases, even on free tier)

---

### Step 3: Deploy with Blueprint

#### Option A: One-Click Deploy (Recommended)

1. Go to **Dashboard** > **Blueprints** > **New Blueprint Instance**
2. Connect your Git provider if not already connected
3. Select your repository containing TNSE
4. Render will detect `render.yaml` automatically
5. Review the services to be created
6. Click **Apply** to start deployment

#### Option B: Manual Blueprint Deploy

1. In Render Dashboard, click **New** > **Blueprint**
2. Connect to your repository
3. Select the branch (usually `main`)
4. Render parses `render.yaml` and shows planned resources
5. Click **Apply**

#### What Happens Next

Render will automatically:
- Create a PostgreSQL database (`tnse-postgres`)
- Create a Redis instance (`tnse-redis`)
- Build your Docker image
- Deploy all four services (web, bot, celery-worker, celery-beat)
- Connect services to databases using internal URLs
- Generate a `SECRET_KEY`

This process takes approximately 5-10 minutes.

---

### Step 4: Configure Environment Variables

After the Blueprint deploys, you must configure Telegram credentials manually.

#### Required Variables (Must Set Manually)

| Variable | Description | How to Obtain |
|----------|-------------|---------------|
| `TELEGRAM_BOT_TOKEN` | Your bot's API token | Create bot with [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_ID` | Telegram API ID (integer) | [my.telegram.org](https://my.telegram.org) > API Development Tools |
| `TELEGRAM_API_HASH` | Telegram API Hash (string) | [my.telegram.org](https://my.telegram.org) > API Development Tools |
| `TELEGRAM_WEBHOOK_URL` | Webhook URL for bot | `https://tnse-web.onrender.com/webhook` |
| `BOT_POLLING_MODE` | Set to `false` for webhooks | `false` |

#### Setting Variables in Render Dashboard

1. Go to **Dashboard** > Select `tnse-bot` service
2. Click **Environment** tab
3. Click **Add Environment Variable**
4. Add each variable:

   ```
   Key: TELEGRAM_BOT_TOKEN
   Value: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
   ```

5. Repeat for each required variable
6. Click **Save Changes**
7. The service will automatically redeploy

**Important**: Add the same Telegram variables to:
- `tnse-bot` (required)
- `tnse-celery-worker` (required for content collection)
- `tnse-web` (for webhook endpoint)

#### Using Environment Groups (Recommended)

For easier management, use Render's Environment Groups:

1. Go to **Dashboard** > **Env Groups** > **New Environment Group**
2. Name it `tnse-secrets`
3. Add all Telegram variables to the group
4. Go to each service and link the environment group:
   - Select service > **Environment** > **Link Environment Group**
   - Choose `tnse-secrets`

This ensures all services share the same credentials.

#### Automatically Provided Variables

These are set automatically by Render - do not modify:

| Variable | Source | Notes |
|----------|--------|-------|
| `DATABASE_URL` | Managed PostgreSQL | Full connection string |
| `REDIS_URL` | Managed Redis | Full connection string |
| `POSTGRES_HOST` | From database | Individual component |
| `POSTGRES_PORT` | From database | Usually 5432 |
| `POSTGRES_DB` | From database | Database name |
| `POSTGRES_USER` | From database | Username |
| `POSTGRES_PASSWORD` | From database | Password |
| `REDIS_HOST` | From Redis | Redis hostname |
| `REDIS_PORT` | From Redis | Usually 6379 |
| `SECRET_KEY` | Auto-generated | For session security |
| `PORT` | Render runtime | Dynamic port assignment |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_TELEGRAM_USERS` | (empty) | Comma-separated user IDs to restrict access |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `CONTENT_WINDOW_HOURS` | `24` | Hours of content to collect |
| `COLLECTION_INTERVAL_MINUTES` | `15` | Content collection frequency |

#### LLM Enhancement Variables (Optional)

To enable Groq-powered LLM enrichment on Render:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes (for LLM) | Groq API key from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | No | Model ID (default: `qwen-qwq-32b`) |
| `GROQ_ENABLED` | No | Set to `true` to enable LLM features |
| `ENRICHMENT_RATE_LIMIT` | No | Requests per minute (default: `10`) |

**Important:** Add `GROQ_API_KEY` to these services:
- `tnse-celery-worker` (processes enrichment tasks)
- `tnse-bot` (for `/enrich` and `/stats llm` commands)

**Cost Considerations for Render:**
- Groq free tier is sufficient for most deployments
- Estimated cost: ~$0.01 per 100 posts enriched
- Monitor usage with `/stats llm` command
- Set `ENRICHMENT_RATE_LIMIT=10` to avoid rate limits

---

### Step 5: Run Database Migrations

After initial deployment, run database migrations to create tables.

#### Using Render Shell

1. Go to **Dashboard** > Select `tnse-web` service
2. Click **Shell** tab
3. Run:

   ```bash
   alembic upgrade head
   ```

4. Verify migrations applied:

   ```bash
   alembic current
   ```

#### Alternative: One-Time Job

You can also create a one-time job:

1. Go to **Dashboard** > **New** > **Job**
2. Select your repository
3. Configure:
   - Name: `tnse-migrate`
   - Command: `alembic upgrade head`
   - Link to same environment variables
4. Run the job

---

### Step 6: Verify Deployment

#### Check Service Status

1. Go to Render Dashboard
2. All services should show **Live** status:
   - `tnse-postgres`: Live
   - `tnse-redis`: Live
   - `tnse-web`: Live
   - `tnse-bot`: Live
   - `tnse-celery-worker`: Live
   - `tnse-celery-beat`: Live

#### Check Health Endpoint

```bash
curl https://tnse-web.onrender.com/health
```

Expected response:
```json
{"status": "healthy", "database": "connected", "redis": "connected"}
```

#### Test the Bot

1. Open Telegram
2. Search for your bot's username
3. Send `/start`
4. You should receive a welcome message

#### Check Logs

1. Select a service in Dashboard
2. Click **Logs** tab
3. Look for:
   - `Bot started successfully`
   - `Connected to database`
   - `Celery worker ready`

---

### Render Dashboard Guide

#### Navigating the Dashboard

**Main Dashboard View:**
- Lists all services, databases, and Redis instances
- Shows status indicators (Live, Deploying, Failed)
- Quick access to logs and settings

**Service Details:**
- **Overview**: Deployment status, URL, last deploy time
- **Logs**: Real-time and historical logs
- **Environment**: Environment variables
- **Shell**: Interactive terminal access
- **Settings**: Service configuration, auto-deploy settings
- **Events**: Deployment history

**Database Details:**
- **Info**: Connection details, size, version
- **Connections**: Connection string and credentials
- **Backups**: Automatic backup schedule
- **Logs**: Database logs

#### Managing Deployments

**Manual Deploy:**
1. Select service
2. Click **Manual Deploy** > **Deploy latest commit**

**Rollback:**
1. Go to **Events** tab
2. Find previous successful deploy
3. Click the three dots menu > **Rollback to this deploy**

**Auto-Deploy Settings:**
1. Go to **Settings** tab
2. Toggle **Auto-Deploy** on/off
3. Configure branch to deploy from

---

### Cost Estimation

Render pricing is based on compute resources and managed services. Here are estimates as of 2025:

#### Starter Tier (Recommended for Personal/Small Teams)

| Service | Plan | Monthly Cost (USD) |
|---------|------|-------------------|
| PostgreSQL | Starter | $7 |
| Redis | Starter | $7 |
| Web Service | Starter | $7 |
| Bot Worker | Starter | $7 |
| Celery Worker | Starter | $7 |
| Celery Beat | Starter | $7 |
| **Total** | | **~$42/month** |

#### Free Tier Limitations

- Web services: 750 hours/month (then hibernates)
- Databases: Not available on free tier
- Workers: Not available on free tier

**Note**: Free tier is not suitable for production bots as services hibernate after inactivity.

#### Standard Tier (Production)

| Service | Plan | Monthly Cost (USD) |
|---------|------|-------------------|
| PostgreSQL | Standard | $25 |
| Redis | Standard | $25 |
| Web Service | Standard | $25 |
| Bot Worker | Standard | $25 |
| Celery Worker | Standard | $25 |
| Celery Beat | Standard | $25 |
| **Total** | | **~$150/month** |

#### Cost Optimization Tips

1. **Combine Beat with Worker**: Modify Celery worker to run beat scheduler too:
   ```bash
   celery -A src.tnse.core.celery_app worker --beat --loglevel=info
   ```
   Saves one worker ($7-25/month).

2. **Use Starter PostgreSQL**: Starter tier (256MB storage) is often sufficient for small deployments.

3. **Scale Workers Only When Needed**: Start with one Celery worker and scale if queue backs up.

4. **Monitor Database Size**: Render charges for storage over plan limits.

---

### Scaling Options

#### Horizontal Scaling

**Scale Web Service:**
1. Go to `tnse-web` service
2. **Settings** > **Instance Count**
3. Increase to 2+ instances
4. Note: Increases cost proportionally

**Scale Celery Workers:**
1. Go to `tnse-celery-worker` service
2. **Settings** > **Instance Count**
3. Increase based on queue depth

#### Vertical Scaling

**Upgrade Service Plan:**
1. Go to service **Settings**
2. Change **Plan** from Starter to Standard/Pro
3. Provides more CPU and RAM

**Upgrade Database:**
1. Go to `tnse-postgres` in Dashboard
2. **Settings** > **Plan**
3. Upgrade for more storage and connections

#### Database Connection Pooling

For high-concurrency scenarios, consider using PgBouncer:

1. Render provides connection pooling URLs
2. Use the pooled connection string for web workers
3. Use direct connection for migrations

---

### Render Troubleshooting

#### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Bot not responding | No response to /start | Check `tnse-bot` logs, verify TELEGRAM_BOT_TOKEN |
| Database connection failed | "Connection refused" errors | Verify service is linked to database in render.yaml |
| Webhook not working | Bot works locally but not on Render | Set BOT_POLLING_MODE=false, configure TELEGRAM_WEBHOOK_URL |
| Service stuck deploying | Spinner for >15 minutes | Check build logs for errors, verify Dockerfile |
| Redis connection failed | Celery tasks not running | Check REDIS_URL is set, verify Redis service is Live |
| Migrations failed | "Table does not exist" errors | Run `alembic upgrade head` via Shell |
| Out of memory | Service crashes repeatedly | Upgrade plan or optimize code memory usage |
| Rate limiting | Telegram API errors | Reduce content collection frequency |

#### Debugging Steps

**1. Check Service Logs:**
```bash
# In Render Dashboard, go to service > Logs
# Look for ERROR or WARNING messages
```

**2. Test Database Connection:**
```bash
# In Shell tab of any service
python -c "from src.tnse.db.base import get_engine; e = get_engine(); print(e.connect())"
```

**3. Test Redis Connection:**
```bash
# In Shell tab
python -c "import redis; import os; r = redis.from_url(os.environ['REDIS_URL']); print(r.ping())"
```

**4. Verify Environment Variables:**
```bash
# In Shell tab
env | grep TELEGRAM
env | grep POSTGRES
env | grep REDIS
```

**5. Check Celery Status:**
```bash
# Look in celery-worker logs for:
# - "celery@... ready" = Worker running
# - "Received task" = Tasks being processed
```

#### Webhook Configuration Issues

If the bot does not respond to messages:

1. Verify webhook URL is accessible:
   ```bash
   curl -I https://tnse-web.onrender.com/webhook
   ```

2. Check Telegram webhook is set:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
   ```

3. If webhook not set, set it manually:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://tnse-web.onrender.com/webhook"
   ```

#### Cold Start Issues

Render's Starter tier services may experience cold starts after periods of inactivity. To mitigate:

1. **Use Health Checks**: Configured in `render.yaml` to keep services warm
2. **Consider Standard Tier**: No hibernation on paid plans
3. **External Ping Service**: Use UptimeRobot or similar to ping `/health` endpoint

#### Database Migration Errors

If migrations fail:

1. Check current migration state:
   ```bash
   alembic current
   ```

2. View migration history:
   ```bash
   alembic history --verbose
   ```

3. If stuck, try stamping the current head:
   ```bash
   alembic stamp head
   ```

4. For fresh start (WARNING: deletes all data):
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

#### Getting Help

1. **Render Documentation**: [render.com/docs](https://render.com/docs)
2. **Render Status**: [status.render.com](https://status.render.com)
3. **Render Community**: [community.render.com](https://community.render.com)
4. **TNSE Issues**: Check the GitHub repository issues

---

### Render Deployment Checklist

Use this checklist for a complete deployment:

**Pre-Deployment:**
- [ ] Repository contains `render.yaml`, `Dockerfile`, and `requirements.txt`
- [ ] Bot token obtained from @BotFather
- [ ] API ID and Hash obtained from my.telegram.org
- [ ] Render account created with payment method

**Blueprint Deployment:**
- [ ] Repository connected to Render
- [ ] Blueprint applied from `render.yaml`
- [ ] All services created (postgres, redis, web, bot, worker, beat)
- [ ] Build completed successfully

**Configuration:**
- [ ] `TELEGRAM_BOT_TOKEN` set in tnse-bot service
- [ ] `TELEGRAM_API_ID` set in tnse-bot and tnse-celery-worker
- [ ] `TELEGRAM_API_HASH` set in tnse-bot and tnse-celery-worker
- [ ] `TELEGRAM_WEBHOOK_URL` set to `https://tnse-web.onrender.com/webhook`
- [ ] `BOT_POLLING_MODE` set to `false`
- [ ] `ALLOWED_TELEGRAM_USERS` set (optional, for restricted access)

**Database:**
- [ ] PostgreSQL database provisioned and Live
- [ ] Migrations run via Shell: `alembic upgrade head`
- [ ] Tables created successfully

**Verification:**
- [ ] All services showing "Live" in Dashboard
- [ ] Health endpoint responds: `curl https://tnse-web.onrender.com/health`
- [ ] Bot responds to `/start` command in Telegram
- [ ] `/help` command shows available commands
- [ ] Logs show no critical errors

**Post-Deployment:**
- [ ] Add first channel with `/addchannel @channelname`
- [ ] Verify content collection in celery-worker logs
- [ ] Test search with `/search keyword`
- [ ] Monitor for 24 hours for stability

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

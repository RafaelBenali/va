# Telegram News Search Engine (TNSE)

A Telegram bot for monitoring public Telegram channels, aggregating news content, and providing ranked search results based on engagement metrics.

## Overview

TNSE is a **Telegram-bot-first** application that helps you:

- **Monitor** public Telegram channels for news content
- **Search** posts using keywords (supports Russian, English, Ukrainian)
- **Rank** results by engagement metrics (views, reactions, relative engagement)
- **Export** results to CSV or JSON
- **Save** search configurations as topics for quick access

No web frontend needed - the Telegram bot is the entire user interface.

## Features

### Core Features

- **Channel Management:** Add, remove, and monitor public Telegram channels
- **Keyword Search:** Full-text search with support for Cyrillic languages
- **Engagement Ranking:** Results ranked by views, reactions, and relative engagement
- **Pagination:** Navigate search results with inline buttons
- **Export:** Download results as CSV or JSON files
- **Saved Topics:** Save and rerun search configurations
- **Templates:** Pre-built search templates for common topics

### Performance

- Search response time: < 3 seconds
- 24-hour content window
- Automatic content collection every 15-30 minutes

### Security

- Optional user whitelist (Telegram user ID based)
- Secure token storage
- No external authentication required

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

### Setup

1. **Clone and configure:**

   ```bash
   git clone <repository-url>
   cd va
   cp .env.example .env
   ```

2. **Edit `.env`** with your Telegram credentials:

   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   ```

3. **Start services:**

   ```bash
   # Using Make
   make docker-up
   make setup
   make run-dev

   # Or using Docker Compose
   docker-compose up -d
   ```

4. **Start using the bot:**
   - Open Telegram
   - Search for your bot
   - Send `/start`

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show all commands |
| `/addchannel @name` | Add channel to monitor |
| `/removechannel @name` | Stop monitoring channel |
| `/channels` | List monitored channels |
| `/search <query>` | Search for posts |
| `/export [csv\|json]` | Export search results |
| `/savetopic <name>` | Save current search |
| `/topics` | List saved topics |
| `/topic <name>` | Run saved topic |
| `/templates` | Show pre-built templates |
| `/import` | Bulk import channels (with file) |
| `/health` | Show channel health status |

See the full [User Guide](docs/USER_GUIDE.md) for detailed usage.

## Architecture

```
+------------------+
|   Telegram Bot   |  <-- The entire user interface
|   (python-tg)    |
+--------+---------+
         |
+--------+---------+
|   Bot Service    |
|  (Commands/UI)   |
+--------+---------+
         |
+--------+---------+
|  Search Service  |
|  (Query/Rank)    |
+--------+---------+
         |
+--------+---------+
| Content Pipeline |
| (Collection/NLP) |
+--------+---------+
         |
+--------+------------------------+
         |                        |
+--------+---------+   +----------+----------+
|   PostgreSQL     |   |       Redis         |
|   (Primary DB)   |   |   (Cache/Queue)     |
+------------------+   +---------------------+
```

## Development

### Running Tests

```bash
make test          # Run all tests
make test-cov      # Run tests with coverage report
make test-unit     # Run only unit tests
```

### Code Quality

```bash
make lint          # Run linters
make format        # Format code
make type-check    # Run type checker
make ci            # Run all CI checks
```

### Docker Commands

```bash
make docker-up     # Start PostgreSQL and Redis
make docker-down   # Stop all services
make docker-logs   # View service logs
```

## Project Structure

```
va/
├── src/tnse/                 # Application source code
│   ├── bot/                  # Telegram bot handlers
│   ├── core/                 # Core modules (config, logging)
│   ├── db/                   # Database models and base
│   ├── engagement/           # Engagement metrics service
│   ├── export/               # Export functionality
│   ├── pipeline/             # Content collection pipeline
│   ├── ranking/              # Ranking algorithm
│   ├── search/               # Search service
│   ├── telegram/             # Telegram API client
│   └── topics/               # Topic management
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── performance/          # Performance benchmarks
├── docs/                     # Documentation
│   ├── USER_GUIDE.md         # Bot usage guide
│   ├── DEPLOYMENT.md         # Deployment instructions
│   └── BOTFATHER_SETUP.md    # Bot registration guide
├── devlog/                   # Development logs
├── docker-compose.yml        # Docker services
├── Makefile                  # Development commands
└── .env.example              # Environment template
```

## Configuration

Key environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_API_ID` | API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | API Hash from my.telegram.org |
| `POSTGRES_*` | Database connection settings |
| `REDIS_*` | Redis connection settings |
| `ALLOWED_TELEGRAM_USERS` | Comma-separated user IDs for access control |

See `.env.example` for all available options.

## Documentation

- [User Guide](docs/USER_GUIDE.md) - How to use the bot
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [BotFather Setup](docs/BOTFATHER_SETUP.md) - Bot registration

## Testing

The project includes comprehensive tests:

- **Unit Tests:** 600+ tests covering all modules
- **Integration Tests:** End-to-end bot command testing
- **Performance Tests:** Benchmarks ensuring < 3 second response time

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test types
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/performance/ -v
```

## License

MIT

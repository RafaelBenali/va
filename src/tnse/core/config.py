"""
TNSE Configuration Module

Provides configuration management using pydantic-settings.
All configuration is externalized via environment variables.

Requirements addressed:
- NFR-M-005: Configuration MUST be externalized and environment-specific

Render.com Compatibility:
- Supports DATABASE_URL for PostgreSQL connection string
- Supports REDIS_URL for Redis connection string
- URL-based configuration takes precedence over individual variables

Python 3.10+ Modernization (WS-6.3):
- Uses X | None instead of Optional[X] for union types
"""

import os
from functools import lru_cache
from urllib.parse import urlparse, unquote

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration.

    Supports two configuration modes:
    1. DATABASE_URL: Single connection string (Render.com style)
    2. Individual POSTGRES_* variables (traditional style)

    DATABASE_URL takes precedence when set.
    """

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore", populate_by_name=True)

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    db: str = Field(default="tnse", validation_alias="database", description="Database name")
    user: str = Field(default="tnse_user", description="Database user")
    password: str = Field(default="", description="Database password")

    @model_validator(mode="before")
    @classmethod
    def parse_database_url(cls, values: dict) -> dict:
        """Parse DATABASE_URL if present and extract components.

        DATABASE_URL takes precedence over individual POSTGRES_* variables.
        Supports standard PostgreSQL URL format:
        postgresql://user:password@host:port/database
        """
        database_url = os.environ.get("DATABASE_URL")

        if database_url:
            parsed = urlparse(database_url)

            # Extract components from URL
            if parsed.hostname:
                values["host"] = parsed.hostname
            if parsed.port:
                values["port"] = parsed.port
            if parsed.username:
                values["user"] = parsed.username
            if parsed.password:
                # Decode URL-encoded password
                values["password"] = unquote(parsed.password)
            if parsed.path and len(parsed.path) > 1:
                # Remove leading slash from path to get database name
                values["db"] = parsed.path[1:]

        return values

    @property
    def url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        """Generate async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """Redis configuration.

    Supports two configuration modes:
    1. REDIS_URL: Single connection string (Render.com style)
    2. Individual REDIS_* variables (traditional style)

    REDIS_URL takes precedence when set.
    Supports both redis:// and rediss:// (TLS) schemes.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")
    use_tls: bool = Field(default=False, description="Use TLS for Redis connection")

    @model_validator(mode="before")
    @classmethod
    def parse_redis_url(cls, values: dict) -> dict:
        """Parse REDIS_URL if present and extract components.

        REDIS_URL takes precedence over individual REDIS_* variables.
        Supports standard Redis URL formats:
        - redis://host:port/db
        - redis://:password@host:port/db
        - rediss://host:port/db (TLS)
        """
        redis_url = os.environ.get("REDIS_URL")

        if redis_url:
            parsed = urlparse(redis_url)

            # Check for TLS (rediss:// scheme)
            if parsed.scheme == "rediss":
                values["use_tls"] = True

            # Extract components from URL
            if parsed.hostname:
                values["host"] = parsed.hostname
            if parsed.port:
                values["port"] = parsed.port
            if parsed.password:
                # Decode URL-encoded password
                values["password"] = unquote(parsed.password)

            # Extract database number from path (e.g., /0, /1, /2)
            if parsed.path and len(parsed.path) > 1:
                try:
                    values["db"] = int(parsed.path[1:])
                except ValueError:
                    pass  # Keep default if path is not a valid integer

        return values

    @property
    def url(self) -> str:
        """Generate Redis connection URL."""
        scheme = "rediss" if self.use_tls else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseSettings):
    """Celery task queue configuration."""

    model_config = SettingsConfigDict(env_prefix="CELERY_")

    broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )


class TelegramSettings(BaseSettings):
    """Telegram API configuration.

    Supports both polling and webhook modes for the Telegram bot.
    For production (Render.com), webhook mode is recommended.
    """

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", extra="ignore")

    bot_token: str | None = Field(default=None, description="Telegram bot token")
    api_id: str | None = Field(default=None, description="Telegram API ID")
    api_hash: str | None = Field(default=None, description="Telegram API hash")
    phone: str | None = Field(default=None, description="Telegram phone number")
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for production (e.g., https://tnse-web.onrender.com/webhook)"
    )


class LLMSettings(BaseSettings):
    """LLM API configuration."""

    enabled: bool = Field(default=False, alias="LLM_ENABLED", description="Enable LLM mode")
    provider: str = Field(
        default="openai", alias="LLM_PROVIDER", description="LLM provider (openai, anthropic)"
    )
    openai_api_key: str | None = Field(
        default=None, alias="OPENAI_API_KEY", description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview", alias="OPENAI_MODEL", description="OpenAI model"
    )
    anthropic_api_key: str | None = Field(
        default=None, alias="ANTHROPIC_API_KEY", description="Anthropic API key"
    )
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229",
        alias="ANTHROPIC_MODEL",
        description="Anthropic model",
    )


class ReactionWeightSettings(BaseSettings):
    """Reaction score weight configuration for metrics-only mode."""

    model_config = SettingsConfigDict(env_prefix="REACTION_WEIGHT_")

    heart: float = Field(default=2.0, description="Weight for heart reaction")
    thumbs_up: float = Field(default=1.0, description="Weight for thumbs up reaction")
    fire: float = Field(default=1.5, description="Weight for fire reaction")
    clap: float = Field(default=1.0, description="Weight for clap reaction")
    thinking: float = Field(default=0.5, description="Weight for thinking reaction")
    thumbs_down: float = Field(default=-1.0, description="Weight for thumbs down reaction")
    default: float = Field(default=1.0, description="Default weight for unknown reactions")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        validate_default=True,
    )

    # Application
    app_name: str = Field(default="tnse", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")

    # Security
    secret_key: str = Field(
        default="change-me-in-production", alias="SECRET_KEY"
    )

    # Content Processing
    content_window_hours: int = Field(
        default=24, alias="CONTENT_WINDOW_HOURS"
    )
    collection_interval_minutes: int = Field(
        default=15, alias="COLLECTION_INTERVAL_MINUTES"
    )
    max_channels_per_batch: int = Field(
        default=50, alias="MAX_CHANNELS_PER_BATCH"
    )

    # Search
    max_search_results: int = Field(default=100, alias="MAX_SEARCH_RESULTS")
    search_cache_ttl: int = Field(default=300, alias="SEARCH_CACHE_TTL")

    # Allowed Telegram users (comma-separated list)
    allowed_telegram_users: str | None = Field(
        default=None, validation_alias="ALLOWED_TELEGRAM_USERS"
    )

    # Bot mode
    bot_polling_mode: bool = Field(
        default=True,
        alias="BOT_POLLING_MODE",
        description="Use polling mode (True) or webhook mode (False)"
    )

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    reaction_weights: ReactionWeightSettings = Field(
        default_factory=ReactionWeightSettings
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Validate log level is one of the allowed values."""
        if not isinstance(value, str):
            raise ValueError("log_level must be a string")
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_value = value.upper()
        if upper_value not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper_value

    @property
    def allowed_user_ids(self) -> list[int]:
        """Parse allowed Telegram user IDs from comma-separated string."""
        if not self.allowed_telegram_users:
            return []
        return [
            int(user_id.strip())
            for user_id in self.allowed_telegram_users.split(",")
            if user_id.strip().isdigit()
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance loaded from environment.

    Example:
        >>> settings = get_settings()
        >>> print(settings.database.url)
    """
    return Settings()

"""
TNSE Configuration Module

Provides configuration management using pydantic-settings.
All configuration is externalized via environment variables.

Requirements addressed:
- NFR-M-005: Configuration MUST be externalized and environment-specific
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore", populate_by_name=True)

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    db: str = Field(default="tnse", validation_alias="database", description="Database name")
    user: str = Field(default="tnse_user", description="Database user")
    password: str = Field(default="", description="Database password")

    @property
    def url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        """Generate async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")

    @property
    def url(self) -> str:
        """Generate Redis connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


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
    """Telegram API configuration."""

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    api_id: Optional[str] = Field(default=None, description="Telegram API ID")
    api_hash: Optional[str] = Field(default=None, description="Telegram API hash")
    phone: Optional[str] = Field(default=None, description="Telegram phone number")


class LLMSettings(BaseSettings):
    """LLM API configuration."""

    enabled: bool = Field(default=False, alias="LLM_ENABLED", description="Enable LLM mode")
    provider: str = Field(
        default="openai", alias="LLM_PROVIDER", description="LLM provider (openai, anthropic)"
    )
    openai_api_key: Optional[str] = Field(
        default=None, alias="OPENAI_API_KEY", description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview", alias="OPENAI_MODEL", description="OpenAI model"
    )
    anthropic_api_key: Optional[str] = Field(
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
    allowed_telegram_users: Optional[str] = Field(
        default=None, validation_alias="ALLOWED_TELEGRAM_USERS"
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

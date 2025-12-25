"""
Tests for TNSE configuration module.

Following TDD methodology: these tests validate configuration loading and validation.
"""

import os
from unittest.mock import patch

import pytest


class TestDatabaseSettings:
    """Tests for database configuration."""

    def test_default_database_settings(self):
        """Test that database settings have sensible defaults."""
        from src.tnse.core.config import DatabaseSettings

        settings = DatabaseSettings()

        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.db == "tnse"
        assert settings.user == "tnse_user"

    def test_database_url_generation(self):
        """Test that database URL is correctly generated."""
        from src.tnse.core.config import DatabaseSettings

        settings = DatabaseSettings(
            host="db.example.com",
            port=5433,
            db="mydb",
            user="admin",
            password="secret123",
        )

        assert settings.url == "postgresql://admin:secret123@db.example.com:5433/mydb"

    def test_database_async_url_generation(self):
        """Test that async database URL is correctly generated."""
        from src.tnse.core.config import DatabaseSettings

        settings = DatabaseSettings(
            host="db.example.com",
            port=5433,
            db="mydb",
            user="admin",
            password="secret123",
        )

        assert settings.async_url == "postgresql+asyncpg://admin:secret123@db.example.com:5433/mydb"


class TestRedisSettings:
    """Tests for Redis configuration."""

    def test_default_redis_settings(self):
        """Test that Redis settings have sensible defaults."""
        from src.tnse.core.config import RedisSettings

        settings = RedisSettings()

        assert settings.host == "localhost"
        assert settings.port == 6379
        assert settings.db == 0
        assert settings.password is None

    def test_redis_url_without_password(self):
        """Test Redis URL generation without password."""
        from src.tnse.core.config import RedisSettings

        settings = RedisSettings(host="redis.example.com", port=6380, db=1)

        assert settings.url == "redis://redis.example.com:6380/1"

    def test_redis_url_with_password(self):
        """Test Redis URL generation with password."""
        from src.tnse.core.config import RedisSettings

        settings = RedisSettings(
            host="redis.example.com", port=6380, db=1, password="secret"
        )

        assert settings.url == "redis://:secret@redis.example.com:6380/1"


class TestSettings:
    """Tests for main application settings."""

    def test_default_settings(self):
        """Test that main settings have sensible defaults."""
        from src.tnse.core.config import Settings

        # Clear cache to ensure fresh settings
        from src.tnse.core.config import get_settings
        get_settings.cache_clear()

        settings = Settings()

        assert settings.app_name == "tnse"
        assert settings.app_env == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.port == 8000

    def test_settings_from_environment(self):
        """Test that settings can be loaded from environment variables."""
        from src.tnse.core.config import Settings

        with patch.dict(
            os.environ,
            {
                "APP_NAME": "test-app",
                "APP_ENV": "production",
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
                "PORT": "9000",
            },
        ):
            settings = Settings()

            assert settings.app_name == "test-app"
            assert settings.app_env == "production"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.port == 9000

    def test_log_level_validation(self):
        """Test that invalid log levels are rejected."""
        from pydantic import ValidationError

        from src.tnse.core.config import Settings

        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")

    def test_allowed_user_ids_parsing(self):
        """Test parsing of allowed Telegram user IDs."""
        from src.tnse.core.config import Settings

        settings = Settings(allowed_telegram_users="123, 456, 789")

        assert settings.allowed_user_ids == [123, 456, 789]

    def test_allowed_user_ids_empty(self):
        """Test that empty allowed users returns empty list."""
        from src.tnse.core.config import Settings

        settings = Settings(allowed_telegram_users=None)

        assert settings.allowed_user_ids == []

    def test_nested_settings(self):
        """Test that nested settings are properly initialized."""
        from src.tnse.core.config import Settings

        settings = Settings()

        assert settings.database is not None
        assert settings.redis is not None
        assert settings.celery is not None
        assert settings.telegram is not None
        assert settings.llm is not None
        assert settings.reaction_weights is not None


class TestReactionWeightSettings:
    """Tests for reaction weight configuration."""

    def test_default_reaction_weights(self):
        """Test default reaction weight values."""
        from src.tnse.core.config import ReactionWeightSettings

        settings = ReactionWeightSettings()

        assert settings.heart == 2.0
        assert settings.thumbs_up == 1.0
        assert settings.fire == 1.5
        assert settings.clap == 1.0
        assert settings.thinking == 0.5
        assert settings.thumbs_down == -1.0
        assert settings.default == 1.0

    def test_custom_reaction_weights(self):
        """Test custom reaction weight configuration."""
        from src.tnse.core.config import ReactionWeightSettings

        with patch.dict(
            os.environ,
            {
                "REACTION_WEIGHT_HEART": "3.0",
                "REACTION_WEIGHT_FIRE": "2.5",
            },
        ):
            settings = ReactionWeightSettings()

            assert settings.heart == 3.0
            assert settings.fire == 2.5


class TestGetSettings:
    """Tests for settings caching."""

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        from src.tnse.core.config import Settings, get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        """Test that get_settings returns cached instance."""
        from src.tnse.core.config import get_settings

        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

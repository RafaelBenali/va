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

    def test_database_url_parsing_from_environment(self):
        """Test that DATABASE_URL environment variable is parsed correctly."""
        from src.tnse.core.config import DatabaseSettings

        # Render provides DATABASE_URL in this format
        database_url = "postgresql://tnse_user:secretpass@oregon-postgres.render.com:5432/tnse_db"

        with patch.dict(
            os.environ,
            {"DATABASE_URL": database_url},
            clear=False,
        ):
            settings = DatabaseSettings()

            assert settings.host == "oregon-postgres.render.com"
            assert settings.port == 5432
            assert settings.db == "tnse_db"
            assert settings.user == "tnse_user"
            assert settings.password == "secretpass"

    def test_database_url_with_render_internal_format(self):
        """Test parsing DATABASE_URL with Render's internal hostname format."""
        from src.tnse.core.config import DatabaseSettings

        # Render internal URLs use different format
        database_url = "postgresql://user:pass@dpg-abc123-a.oregon-postgres.render.com:5432/mydb"

        with patch.dict(
            os.environ,
            {"DATABASE_URL": database_url},
            clear=False,
        ):
            settings = DatabaseSettings()

            assert settings.host == "dpg-abc123-a.oregon-postgres.render.com"
            assert settings.user == "user"
            assert settings.password == "pass"
            assert settings.db == "mydb"

    def test_database_url_takes_precedence_over_individual_vars(self):
        """Test that DATABASE_URL takes precedence over individual POSTGRES_* vars."""
        from src.tnse.core.config import DatabaseSettings

        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://url_user:url_pass@url-host:5433/url_db",
                "POSTGRES_HOST": "individual_host",
                "POSTGRES_USER": "individual_user",
            },
            clear=False,
        ):
            settings = DatabaseSettings()

            # DATABASE_URL should take precedence
            assert settings.host == "url-host"
            assert settings.user == "url_user"
            assert settings.db == "url_db"
            assert settings.port == 5433

    def test_database_url_with_special_characters_in_password(self):
        """Test DATABASE_URL parsing with special characters in password."""
        from src.tnse.core.config import DatabaseSettings
        from urllib.parse import quote

        # Password with special characters needs URL encoding
        password = "p@ss:word/test"
        encoded_password = quote(password, safe="")
        database_url = f"postgresql://user:{encoded_password}@host:5432/db"

        with patch.dict(
            os.environ,
            {"DATABASE_URL": database_url},
            clear=False,
        ):
            settings = DatabaseSettings()

            assert settings.password == password

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

    def test_redis_url_parsing_from_environment(self):
        """Test that REDIS_URL environment variable is parsed correctly."""
        from src.tnse.core.config import RedisSettings

        # Render provides REDIS_URL in this format
        redis_url = "redis://red-abc123.oregon-redis.render.com:6379"

        with patch.dict(
            os.environ,
            {"REDIS_URL": redis_url},
            clear=False,
        ):
            settings = RedisSettings()

            assert settings.host == "red-abc123.oregon-redis.render.com"
            assert settings.port == 6379
            assert settings.db == 0  # Default when not specified

    def test_redis_url_with_password(self):
        """Test parsing REDIS_URL with password."""
        from src.tnse.core.config import RedisSettings

        redis_url = "redis://:secretpassword@redis.render.com:6379/0"

        with patch.dict(
            os.environ,
            {"REDIS_URL": redis_url},
            clear=False,
        ):
            settings = RedisSettings()

            assert settings.host == "redis.render.com"
            assert settings.port == 6379
            assert settings.password == "secretpassword"
            assert settings.db == 0

    def test_redis_url_with_database_number(self):
        """Test parsing REDIS_URL with database number."""
        from src.tnse.core.config import RedisSettings

        redis_url = "redis://redis.render.com:6379/2"

        with patch.dict(
            os.environ,
            {"REDIS_URL": redis_url},
            clear=False,
        ):
            settings = RedisSettings()

            assert settings.db == 2

    def test_redis_url_takes_precedence_over_individual_vars(self):
        """Test that REDIS_URL takes precedence over individual REDIS_* vars."""
        from src.tnse.core.config import RedisSettings

        with patch.dict(
            os.environ,
            {
                "REDIS_URL": "redis://url-host:6380/3",
                "REDIS_HOST": "individual_host",
                "REDIS_PORT": "6379",
            },
            clear=False,
        ):
            settings = RedisSettings()

            # REDIS_URL should take precedence
            assert settings.host == "url-host"
            assert settings.port == 6380
            assert settings.db == 3

    def test_rediss_url_for_tls(self):
        """Test parsing REDIS_URL with rediss:// scheme (TLS)."""
        from src.tnse.core.config import RedisSettings

        # Render may provide TLS-enabled Redis URLs
        redis_url = "rediss://:pass@redis.render.com:6379/0"

        with patch.dict(
            os.environ,
            {"REDIS_URL": redis_url},
            clear=False,
        ):
            settings = RedisSettings()

            assert settings.host == "redis.render.com"
            assert settings.password == "pass"
            # TLS flag should be captured
            assert settings.use_tls is True


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

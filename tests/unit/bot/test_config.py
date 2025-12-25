"""
Tests for TNSE Telegram bot configuration.

Following TDD methodology: these tests are written BEFORE the implementation.
"""

import pytest
from unittest.mock import patch


class TestBotConfig:
    """Tests for bot configuration and settings."""

    def test_bot_config_has_token_attribute(self):
        """Test that BotConfig has a token attribute."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test_token")
        assert hasattr(config, "token")
        assert config.token == "test_token"

    def test_bot_config_from_env_webhook_mode(self):
        """Test that BotConfig reads webhook URL from environment."""
        from src.tnse.bot.config import create_bot_config

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "123456789:TestToken",
                "BOT_POLLING_MODE": "false",
                "TELEGRAM_WEBHOOK_URL": "https://tnse-web.onrender.com/webhook",
            },
        ):
            config = create_bot_config()
            assert config.polling_mode is False
            assert config.webhook_url == "https://tnse-web.onrender.com/webhook"

    def test_bot_config_from_env_polling_mode(self):
        """Test that BotConfig defaults to polling mode."""
        from src.tnse.bot.config import create_bot_config

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "123456789:TestToken",
                "BOT_POLLING_MODE": "true",
            },
        ):
            config = create_bot_config()
            assert config.polling_mode is True
            assert config.webhook_url is None

    def test_bot_config_webhook_url_required_when_not_polling(self):
        """Test that webhook_url is read when polling mode is disabled."""
        from src.tnse.bot.config import create_bot_config

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "123456789:TestToken",
                "BOT_POLLING_MODE": "false",
                "TELEGRAM_WEBHOOK_URL": "https://example.com/webhook",
            },
        ):
            config = create_bot_config()
            assert config.webhook_url == "https://example.com/webhook"

    def test_bot_config_validates_token_format(self):
        """Test that BotConfig validates token format."""
        from src.tnse.bot.config import BotConfig

        # Valid token format: <bot_id>:<hash>
        valid_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
        config = BotConfig(token=valid_token)
        assert config.token == valid_token

    def test_bot_config_rejects_empty_token(self):
        """Test that BotConfig rejects empty token."""
        from src.tnse.bot.config import BotConfig

        with pytest.raises(ValueError):
            BotConfig(token="")

    def test_bot_config_has_allowed_users_list(self):
        """Test that BotConfig has allowed_users attribute as list."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(
            token="123456789:ABCdef", allowed_users=[123, 456]
        )
        assert hasattr(config, "allowed_users")
        assert config.allowed_users == [123, 456]

    def test_bot_config_allowed_users_defaults_to_empty(self):
        """Test that allowed_users defaults to empty list (open access)."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdef")
        assert config.allowed_users == []

    def test_bot_config_has_polling_mode(self):
        """Test that BotConfig has polling_mode attribute."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdef", polling_mode=True)
        assert hasattr(config, "polling_mode")
        assert config.polling_mode is True

    def test_bot_config_polling_mode_defaults_to_true(self):
        """Test that polling_mode defaults to True."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdef")
        assert config.polling_mode is True

    def test_bot_config_has_webhook_url(self):
        """Test that BotConfig has webhook_url attribute."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(
            token="123456789:ABCdef",
            polling_mode=False,
            webhook_url="https://example.com/webhook",
        )
        assert hasattr(config, "webhook_url")
        assert config.webhook_url == "https://example.com/webhook"

    def test_bot_config_webhook_url_defaults_to_none(self):
        """Test that webhook_url defaults to None."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdef")
        assert config.webhook_url is None


class TestBotConfigFromSettings:
    """Tests for creating bot config from application settings."""

    def test_create_bot_config_from_settings(self):
        """Test creating BotConfig from application Settings."""
        from src.tnse.bot.config import BotConfig, create_bot_config

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "123456789:TestToken",
                "ALLOWED_TELEGRAM_USERS": "111,222,333",
            },
        ):
            config = create_bot_config()
            assert isinstance(config, BotConfig)
            assert config.token == "123456789:TestToken"
            assert config.allowed_users == [111, 222, 333]

    def test_create_bot_config_raises_without_token(self):
        """Test that create_bot_config raises error when token is missing."""
        from src.tnse.bot.config import create_bot_config, BotTokenMissingError

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": ""}, clear=True):
            with pytest.raises(BotTokenMissingError):
                create_bot_config()

    def test_create_bot_config_empty_allowed_users(self):
        """Test that empty ALLOWED_TELEGRAM_USERS results in empty list."""
        from src.tnse.bot.config import create_bot_config

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "123456789:TestToken", "ALLOWED_TELEGRAM_USERS": ""},
        ):
            config = create_bot_config()
            assert config.allowed_users == []


class TestBotConfigSecurity:
    """Tests for bot configuration security aspects."""

    def test_token_not_exposed_in_repr(self):
        """Test that token is not exposed in string representation."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:SecretToken")
        repr_str = repr(config)
        assert "SecretToken" not in repr_str
        assert "***" in repr_str or "REDACTED" in repr_str or "token" not in repr_str.lower()

    def test_token_not_exposed_in_str(self):
        """Test that token is not exposed in str representation."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:SecretToken")
        str_repr = str(config)
        assert "SecretToken" not in str_repr

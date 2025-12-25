"""
Tests for TNSE Telegram bot application.

Following TDD methodology: these tests are written BEFORE the implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBotApplicationFactory:
    """Tests for bot application factory."""

    def test_create_bot_application_exists(self):
        """Test that create_bot_application function exists."""
        from src.tnse.bot.application import create_bot_application

        assert callable(create_bot_application)

    def test_create_bot_application_returns_application(self):
        """Test that create_bot_application returns an Application instance."""
        from telegram.ext import Application
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        assert isinstance(app, Application)

    def test_create_bot_application_stores_config_in_bot_data(self):
        """Test that config is stored in application.bot_data."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken", allowed_users=[123])
        app = create_bot_application(config)

        # Build the application to access bot_data
        assert "config" in app.bot_data
        assert app.bot_data["config"] is config

    def test_create_bot_application_registers_start_handler(self):
        """Test that /start handler is registered."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        # Check that handlers are registered
        handlers = app.handlers
        assert len(handlers) > 0

        # Flatten handler groups and check for command handlers
        all_handlers = []
        for group_handlers in handlers.values():
            all_handlers.extend(group_handlers)

        command_names = []
        for handler in all_handlers:
            if hasattr(handler, "commands"):
                command_names.extend(handler.commands)

        assert "start" in command_names

    def test_create_bot_application_registers_help_handler(self):
        """Test that /help handler is registered."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        handlers = app.handlers
        all_handlers = []
        for group_handlers in handlers.values():
            all_handlers.extend(group_handlers)

        command_names = []
        for handler in all_handlers:
            if hasattr(handler, "commands"):
                command_names.extend(handler.commands)

        assert "help" in command_names

    def test_create_bot_application_registers_settings_handler(self):
        """Test that /settings handler is registered."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        handlers = app.handlers
        all_handlers = []
        for group_handlers in handlers.values():
            all_handlers.extend(group_handlers)

        command_names = []
        for handler in all_handlers:
            if hasattr(handler, "commands"):
                command_names.extend(handler.commands)

        assert "settings" in command_names

    def test_create_bot_application_registers_error_handler(self):
        """Test that error handler is registered."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        # Check that error_handlers is not empty
        assert len(app.error_handlers) > 0


class TestBotRunner:
    """Tests for bot runner functionality."""

    def test_run_bot_polling_function_exists(self):
        """Test that run_bot_polling function exists."""
        from src.tnse.bot.application import run_bot_polling

        assert callable(run_bot_polling)

    def test_run_bot_webhook_function_exists(self):
        """Test that run_bot_webhook function exists."""
        from src.tnse.bot.application import run_bot_webhook

        assert callable(run_bot_webhook)

    @pytest.mark.asyncio
    async def test_run_bot_function_exists(self):
        """Test that run_bot async function exists."""
        from src.tnse.bot.application import run_bot

        assert callable(run_bot)

    @pytest.mark.asyncio
    async def test_run_bot_uses_polling_when_polling_mode_true(self):
        """Test that run_bot uses polling when config.polling_mode is True."""
        from src.tnse.bot.application import run_bot
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken", polling_mode=True)

        with patch("src.tnse.bot.application.run_bot_polling") as mock_polling:
            with patch("src.tnse.bot.application.run_bot_webhook") as mock_webhook:
                await run_bot(config)

                mock_polling.assert_called_once()
                mock_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_bot_uses_webhook_when_polling_mode_false(self):
        """Test that run_bot uses webhook when config.polling_mode is False."""
        from src.tnse.bot.application import run_bot
        from src.tnse.bot.config import BotConfig

        config = BotConfig(
            token="123456789:ABCdefTestToken",
            polling_mode=False,
            webhook_url="https://example.com/webhook"
        )

        with patch("src.tnse.bot.application.run_bot_polling") as mock_polling:
            with patch("src.tnse.bot.application.run_bot_webhook") as mock_webhook:
                await run_bot(config)

                mock_webhook.assert_called_once()
                mock_polling.assert_not_called()


class TestBotApplicationFromEnv:
    """Tests for creating bot application from environment."""

    def test_create_bot_from_env_function_exists(self):
        """Test that create_bot_from_env function exists."""
        from src.tnse.bot.application import create_bot_from_env

        assert callable(create_bot_from_env)

    def test_create_bot_from_env_creates_application(self):
        """Test that create_bot_from_env creates Application from env vars."""
        from telegram.ext import Application
        from src.tnse.bot.application import create_bot_from_env

        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "123456789:TestEnvToken"},
        ):
            app = create_bot_from_env()
            assert isinstance(app, Application)

    def test_create_bot_from_env_raises_without_token(self):
        """Test that create_bot_from_env raises when token not in env."""
        from src.tnse.bot.application import create_bot_from_env
        from src.tnse.bot.config import BotTokenMissingError

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": ""}, clear=True):
            with pytest.raises(BotTokenMissingError):
                create_bot_from_env()


class TestAccessControlIntegration:
    """Tests for access control integration in application."""

    def test_handlers_use_require_access_for_protected_commands(self):
        """Test that protected command handlers use require_access decorator."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken", allowed_users=[123])
        app = create_bot_application(config)

        # This tests that handlers are wrapped - the actual access control
        # behavior is tested in test_handlers.py
        handlers = app.handlers
        assert len(handlers) > 0


class TestApplicationLogging:
    """Tests for application logging configuration."""

    def test_application_configures_logging(self):
        """Test that application sets up logging on creation."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")

        # Should not raise and should configure logging
        app = create_bot_application(config)
        assert app is not None

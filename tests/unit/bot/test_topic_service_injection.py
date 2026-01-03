"""
Tests for TNSE Telegram Bot Topic Service Dependency Injection (WS-7.4).

Following TDD methodology: these tests are written BEFORE implementation.

This test module covers:
1. Topic service creation factory function
2. Topic service status logging at startup
3. Handler behavior when db_session_factory is missing
4. Clear error messages for configuration issues
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: Topic Service Factory Function
# =============================================================================


class TestTopicServiceFactory:
    """Tests for topic service factory function in __main__.py."""

    def test_create_topic_service_function_exists(self):
        """Test that a create_topic_service function exists in __main__."""
        try:
            from src.tnse.bot.__main__ import create_topic_service
            assert callable(create_topic_service)
        except ImportError:
            pytest.fail("create_topic_service function should exist in __main__.py")

    def test_create_topic_service_returns_factory_when_db_available(self):
        """Test that create_topic_service returns a factory when db is available."""
        mock_session_factory = MagicMock()

        from src.tnse.bot.__main__ import create_topic_service

        result = create_topic_service(mock_session_factory)
        assert result is not None
        # Result should be callable (factory pattern)
        assert callable(result)

    def test_create_topic_service_returns_none_when_no_db_factory(self):
        """Test that create_topic_service returns None when db_session_factory is None."""
        from src.tnse.bot.__main__ import create_topic_service

        result = create_topic_service(None)
        assert result is None

    def test_create_topic_service_factory_creates_topic_service(self):
        """Test that the factory creates a TopicService with a session."""
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        from src.tnse.bot.__main__ import create_topic_service
        from src.tnse.topics.service import TopicService

        factory = create_topic_service(mock_session_factory)
        assert factory is not None

        # The factory should be usable to get TopicService instances
        # This is an async context manager pattern


# =============================================================================
# Test: Topic Service Status Logging
# =============================================================================


class TestTopicServiceStatusLogging:
    """Tests for topic service status logging at bot startup."""

    def test_log_service_status_accepts_topic_service_parameter(self):
        """Test that log_service_status accepts topic_service parameter."""
        from src.tnse.bot.__main__ import log_service_status

        # Should not raise an error when topic_service is provided
        with patch("src.tnse.bot.__main__.logger"):
            log_service_status(topic_service=MagicMock())

    def test_log_service_status_logs_topic_service_available(self):
        """Test that log_service_status logs when topic service is available."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            mock_topic_service = MagicMock()

            log_service_status(topic_service=mock_topic_service)

            # Should log info about available topic service
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("topic" in str(call).lower() for call in info_calls), \
                f"Expected info about topic service. Got: {info_calls}"

    def test_log_service_status_logs_warning_when_topic_service_unavailable(self):
        """Test that log_service_status logs warning when topic service is None."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            log_service_status(topic_service=None)

            # Should log warning about missing topic service
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "topic" in str(call).lower()
                for call in warning_calls
            ), f"Expected warning about topic service. Got: {warning_calls}"


# =============================================================================
# Test: Topic Service Injection in Application
# =============================================================================


class TestTopicServiceInjectionInApplication:
    """Tests for topic service injection behavior in application.py."""

    def test_application_bot_data_contains_topic_service_when_provided(self):
        """Test that topic_service is properly stored in bot_data when provided."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        mock_topic_service = MagicMock()
        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            topic_service=mock_topic_service,
        )

        assert app.bot_data.get("topic_service") is mock_topic_service

    def test_application_bot_data_excludes_topic_service_when_none(self):
        """Test that topic_service is NOT in bot_data when None."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            topic_service=None,
        )

        # Should not have topic_service key at all
        assert "topic_service" not in app.bot_data


# =============================================================================
# Test: Handler Error Messages
# =============================================================================


class TestTopicHandlerErrorMessages:
    """Tests for clear error messages in topic handlers when service not configured."""

    @pytest.mark.asyncio
    async def test_savetopic_shows_configuration_error_when_service_missing(self):
        """Test that savetopic shows helpful message when topic_service is missing."""
        from src.tnse.bot.topic_handlers import savetopic_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["my_topic"]
        context.user_data = {"last_search_query": "test query"}
        context.bot_data = {
            # topic_service is missing
        }

        await savetopic_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        # Error message should mention configuration or be actionable
        error_message_lower = call_args.lower()
        assert (
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "administrator" in error_message_lower or
            "database" in error_message_lower or
            "not available" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_topics_shows_configuration_error_when_service_missing(self):
        """Test that topics shows helpful message when topic_service is missing."""
        from src.tnse.bot.topic_handlers import topics_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            # topic_service is missing
        }

        await topics_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "administrator" in error_message_lower or
            "database" in error_message_lower or
            "not available" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_topic_shows_configuration_error_when_service_missing(self):
        """Test that topic shows helpful message when topic_service is missing."""
        from src.tnse.bot.topic_handlers import topic_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["my_topic"]
        context.bot_data = {
            # topic_service is missing
        }

        await topic_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "administrator" in error_message_lower or
            "database" in error_message_lower or
            "not available" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_deletetopic_shows_configuration_error_when_service_missing(self):
        """Test that deletetopic shows helpful message when topic_service is missing."""
        from src.tnse.bot.topic_handlers import deletetopic_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["my_topic"]
        context.bot_data = {
            # topic_service is missing
        }

        await deletetopic_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "administrator" in error_message_lower or
            "database" in error_message_lower or
            "not available" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_usetemplate_shows_configuration_error_when_search_missing(self):
        """Test that usetemplate shows helpful message when search_service is missing."""
        from src.tnse.bot.topic_handlers import use_template_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["corruption"]
        context.bot_data = {
            # search_service is missing
        }

        await use_template_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called()
        # May have multiple calls - get the last one
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "administrator" in error_message_lower or
            "database" in error_message_lower or
            "not available" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"


# =============================================================================
# Test: Error Message User-Friendliness
# =============================================================================


class TestTopicErrorMessageUserFriendliness:
    """Tests for user-friendly error messages in topic handlers."""

    @pytest.mark.asyncio
    async def test_savetopic_error_does_not_expose_internal_details(self):
        """Test that savetopic error does not expose internal implementation details."""
        from src.tnse.bot.topic_handlers import savetopic_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["my_topic"]
        context.user_data = {"last_search_query": "test"}
        context.bot_data = {}

        await savetopic_command(update, context)

        call_args = update.message.reply_text.call_args[0][0]
        error_message_lower = call_args.lower()

        # Should NOT expose internal details
        assert "bot_data" not in error_message_lower
        assert "context" not in error_message_lower
        assert "traceback" not in error_message_lower
        assert "exception" not in error_message_lower

    @pytest.mark.asyncio
    async def test_topics_error_suggests_administrator_contact(self):
        """Test that topics error suggests contacting administrator."""
        from src.tnse.bot.topic_handlers import topics_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {}

        await topics_command(update, context)

        call_args = update.message.reply_text.call_args[0][0]
        error_message_lower = call_args.lower()

        # Should provide actionable guidance
        assert (
            "administrator" in error_message_lower or
            "admin" in error_message_lower or
            "contact" in error_message_lower or
            "configure" in error_message_lower or
            "configuration" in error_message_lower
        ), f"Expected actionable guidance in error message. Got: {call_args}"


# =============================================================================
# Test: Main Function Integration
# =============================================================================


class TestMainFunctionTopicServiceIntegration:
    """Tests for topic service integration in main() function."""

    def test_main_creates_topic_service(self):
        """Test that main() creates and injects topic service."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123456:ABC",
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            with patch("src.tnse.bot.__main__.create_db_session_factory") as mock_db_factory:
                with patch("src.tnse.bot.__main__.create_topic_service") as mock_create_topic:
                    with patch("src.tnse.bot.__main__.create_bot_from_env") as mock_create_bot:
                        mock_app = MagicMock()
                        mock_app.run_polling = MagicMock(side_effect=KeyboardInterrupt)
                        mock_create_bot.return_value = mock_app

                        mock_db_factory.return_value = MagicMock()
                        mock_create_topic.return_value = MagicMock()

                        from src.tnse.bot.__main__ import main

                        main()

                        # Should have called create_topic_service
                        mock_create_topic.assert_called_once()

    def test_main_passes_topic_service_to_create_bot(self):
        """Test that main() passes topic service to create_bot_from_env."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123456:ABC",
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            with patch("src.tnse.bot.__main__.create_db_session_factory") as mock_db_factory:
                with patch("src.tnse.bot.__main__.create_topic_service") as mock_create_topic:
                    with patch("src.tnse.bot.__main__.create_bot_from_env") as mock_create_bot:
                        mock_app = MagicMock()
                        mock_app.run_polling = MagicMock(side_effect=KeyboardInterrupt)
                        mock_create_bot.return_value = mock_app

                        mock_db = MagicMock()
                        mock_db_factory.return_value = mock_db

                        mock_topic = MagicMock()
                        mock_create_topic.return_value = mock_topic

                        from src.tnse.bot.__main__ import main

                        main()

                        # Check that create_bot_from_env was called with topic_service
                        mock_create_bot.assert_called_once()
                        call_kwargs = mock_create_bot.call_args[1]
                        assert "topic_service" in call_kwargs
                        assert call_kwargs["topic_service"] is mock_topic

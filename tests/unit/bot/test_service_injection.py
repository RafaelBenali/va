"""
Tests for TNSE Telegram Bot Service Dependency Injection (WS-7.1).

Following TDD methodology: these tests are written BEFORE implementation.

This test module covers:
1. Service availability reporting at startup
2. Clear error messages when services are not configured
3. Handler behavior when channel_service is None
4. Handler behavior when db_session_factory is None
5. Environment variable validation
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: Service Availability at Startup
# =============================================================================


class TestServiceAvailabilityAtStartup:
    """Tests for service availability detection and reporting at startup."""

    def test_create_channel_service_returns_none_without_api_id(self):
        """Test that create_channel_service returns None when TELEGRAM_API_ID is missing."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "valid_hash",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            from src.tnse.bot.__main__ import create_channel_service

            result = create_channel_service()
            assert result is None

    def test_create_channel_service_returns_none_without_api_hash(self):
        """Test that create_channel_service returns None when TELEGRAM_API_HASH is missing."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            from src.tnse.bot.__main__ import create_channel_service

            result = create_channel_service()
            assert result is None

    def test_create_channel_service_logs_warning_when_credentials_missing(self):
        """Test that a clear warning is logged when Telegram API credentials are missing."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            with patch("src.tnse.bot.__main__.logger") as mock_logger:
                from src.tnse.bot.__main__ import create_channel_service

                create_channel_service()

                # Should log a warning with helpful hint
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert "not configured" in call_args[0][0].lower() or "credentials" in call_args[0][0].lower()


class TestServiceStatusLogging:
    """Tests for service status logging at bot startup."""

    def test_main_logs_available_services(self):
        """Test that main() logs which services are available at startup."""
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

            with patch("src.tnse.bot.__main__.logger") as mock_logger:
                with patch("src.tnse.bot.__main__.create_db_session_factory"):
                    with patch("src.tnse.bot.__main__.create_bot_from_env") as mock_create_bot:
                        # Mock the application to prevent actual run
                        mock_app = MagicMock()
                        mock_app.run_polling = MagicMock(side_effect=KeyboardInterrupt)
                        mock_create_bot.return_value = mock_app

                        from src.tnse.bot.__main__ import main

                        main()

                        # Should log service availability status
                        info_calls = [str(call) for call in mock_logger.info.call_args_list]
                        # Check that startup logs mention service availability
                        assert any("channel" in str(call).lower() or "service" in str(call).lower()
                                   for call in info_calls)

    def test_main_logs_channel_commands_disabled_when_service_unavailable(self):
        """Test that main() logs a clear message when channel commands will be disabled."""
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

            with patch("src.tnse.bot.__main__.logger") as mock_logger:
                with patch("src.tnse.bot.__main__.create_db_session_factory"):
                    with patch("src.tnse.bot.__main__.create_bot_from_env") as mock_create_bot:
                        mock_app = MagicMock()
                        mock_app.run_polling = MagicMock(side_effect=KeyboardInterrupt)
                        mock_create_bot.return_value = mock_app

                        from src.tnse.bot.__main__ import main

                        main()

                        # Should log warning about disabled features
                        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        assert any(
                            "disabled" in str(call).lower() or
                            "not available" in str(call).lower() or
                            "will not work" in str(call).lower()
                            for call in warning_calls
                        ), f"Expected warning about disabled features. Got warnings: {warning_calls}"


# =============================================================================
# Test: Handler Error Messages
# =============================================================================


class TestHandlerErrorMessages:
    """Tests for clear error messages in handlers when services are not configured."""

    @pytest.mark.asyncio
    async def test_addchannel_shows_configuration_error_message(self):
        """Test that addchannel shows a helpful message when channel_service is not configured."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            # channel_service is missing (None)
            "db_session_factory": MagicMock(),
        }
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        # Should show a helpful configuration error message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        # Error message should mention configuration or environment variables
        error_message_lower = call_args.lower()
        assert (
            "telegram_api_id" in error_message_lower or
            "telegram_api_hash" in error_message_lower or
            "not configured" in error_message_lower or
            "configuration" in error_message_lower or
            "environment" in error_message_lower
        ), f"Expected configuration hint in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_addchannel_shows_database_error_when_db_missing(self):
        """Test that addchannel shows a helpful message when db_session_factory is missing."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_channel_service = MagicMock()
        validation_result = MagicMock()
        validation_result.is_valid = True
        validation_result.channel_info = MagicMock(
            telegram_id=123,
            username="testchannel",
            title="Test Channel",
            description="",
            subscriber_count=1000,
            photo_url=None,
            invite_link=None,
        )
        mock_channel_service.validate_channel = AsyncMock(return_value=validation_result)

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            "channel_service": mock_channel_service,
            # db_session_factory is missing (None)
        }
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        # Should show an error message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]

        # Error message should mention database configuration
        error_message_lower = call_args.lower()
        assert (
            "database" in error_message_lower or
            "not configured" in error_message_lower or
            "configuration" in error_message_lower
        ), f"Expected database configuration hint. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_channels_shows_database_error_when_db_missing(self):
        """Test that channels command shows helpful message when db_session_factory is missing."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            # db_session_factory is missing
        }

        await channels_command(update, context)

        # Should show an error message about database
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "database" in error_message_lower or
            "not available" in error_message_lower or
            "not configured" in error_message_lower
        ), f"Expected database error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_channelinfo_shows_database_error_when_db_missing(self):
        """Test that channelinfo shows helpful message when db_session_factory is missing."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            # db_session_factory is missing
        }

        await channelinfo_command(update, context)

        # Should show an error message about database
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "database" in error_message_lower or
            "not available" in error_message_lower or
            "not configured" in error_message_lower
        ), f"Expected database error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_removechannel_shows_database_error_when_db_missing(self):
        """Test that removechannel shows helpful message when db_session_factory is missing."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            # db_session_factory is missing
        }

        await removechannel_command(update, context)

        # Should show an error message about database
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]

        error_message_lower = call_args.lower()
        assert (
            "database" in error_message_lower or
            "not available" in error_message_lower or
            "not configured" in error_message_lower
        ), f"Expected database error message. Got: {call_args}"


# =============================================================================
# Test: Service Injection in Application
# =============================================================================


class TestServiceInjectionInApplication:
    """Tests for service injection behavior in application.py."""

    def test_application_bot_data_contains_channel_service_when_provided(self):
        """Test that channel_service is properly stored in bot_data when provided."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        mock_channel_service = MagicMock()
        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            channel_service=mock_channel_service,
        )

        assert app.bot_data.get("channel_service") is mock_channel_service

    def test_application_bot_data_excludes_channel_service_when_none(self):
        """Test that channel_service is NOT in bot_data when None."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            channel_service=None,
        )

        # Should not have channel_service key at all
        assert "channel_service" not in app.bot_data

    def test_application_bot_data_contains_db_session_when_provided(self):
        """Test that db_session_factory is properly stored in bot_data when provided."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        mock_db_session_factory = MagicMock()
        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            db_session_factory=mock_db_session_factory,
        )

        assert app.bot_data.get("db_session_factory") is mock_db_session_factory

    def test_application_bot_data_excludes_db_session_when_none(self):
        """Test that db_session_factory is NOT in bot_data when None."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            db_session_factory=None,
        )

        # Should not have db_session_factory key at all
        assert "db_session_factory" not in app.bot_data


# =============================================================================
# Test: Startup Service Summary
# =============================================================================


class TestStartupServiceSummary:
    """Tests for the service summary displayed at bot startup."""

    def test_log_service_status_function_exists(self):
        """Test that a log_service_status function exists in __main__."""
        try:
            from src.tnse.bot.__main__ import log_service_status
            assert callable(log_service_status)
        except ImportError:
            pytest.fail("log_service_status function should exist in __main__.py")

    def test_log_service_status_logs_channel_service_available(self):
        """Test that log_service_status logs when channel service is available."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            mock_channel_service = MagicMock()
            mock_db_factory = MagicMock()

            log_service_status(
                channel_service=mock_channel_service,
                db_session_factory=mock_db_factory,
            )

            # Should log info about available services
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("channel" in str(call).lower() for call in info_calls)

    def test_log_service_status_logs_warning_when_channel_service_unavailable(self):
        """Test that log_service_status logs warning when channel service is None."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            mock_db_factory = MagicMock()

            log_service_status(
                channel_service=None,
                db_session_factory=mock_db_factory,
            )

            # Should log warning about missing channel service
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "channel" in str(call).lower() or
                "addchannel" in str(call).lower()
                for call in warning_calls
            ), f"Expected warning about channel service. Got: {warning_calls}"

    def test_log_service_status_logs_warning_when_db_unavailable(self):
        """Test that log_service_status logs warning when database is unavailable."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            mock_channel_service = MagicMock()

            log_service_status(
                channel_service=mock_channel_service,
                db_session_factory=None,
            )

            # Should log warning about missing database
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "database" in str(call).lower()
                for call in warning_calls
            ), f"Expected warning about database. Got: {warning_calls}"


# =============================================================================
# Test: Environment Variable Validation
# =============================================================================


class TestEnvironmentVariableValidation:
    """Tests for environment variable validation."""

    def test_validate_telegram_credentials_returns_valid_when_both_present(self):
        """Test credential validation returns valid when both API_ID and API_HASH are set."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "abcdef123456",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            try:
                from src.tnse.bot.__main__ import validate_telegram_credentials
                result = validate_telegram_credentials()
                assert result is True
            except ImportError:
                # Function doesn't exist yet - this is expected in TDD
                pytest.fail("validate_telegram_credentials function should exist")

    def test_validate_telegram_credentials_returns_invalid_when_id_missing(self):
        """Test credential validation returns invalid when API_ID is missing."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "",
            "TELEGRAM_API_HASH": "abcdef123456",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            try:
                from src.tnse.bot.__main__ import validate_telegram_credentials
                result = validate_telegram_credentials()
                assert result is False
            except ImportError:
                pytest.fail("validate_telegram_credentials function should exist")

    def test_validate_telegram_credentials_returns_invalid_when_hash_missing(self):
        """Test credential validation returns invalid when API_HASH is missing."""
        with patch.dict(os.environ, {
            "TELEGRAM_API_ID": "12345",
            "TELEGRAM_API_HASH": "",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            try:
                from src.tnse.bot.__main__ import validate_telegram_credentials
                result = validate_telegram_credentials()
                assert result is False
            except ImportError:
                pytest.fail("validate_telegram_credentials function should exist")


# =============================================================================
# Test: Error Message User-Friendliness
# =============================================================================


class TestErrorMessageUserFriendliness:
    """Tests for user-friendly error messages."""

    @pytest.mark.asyncio
    async def test_addchannel_error_mentions_admin_contact(self):
        """Test that addchannel error suggests contacting administrator."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {}  # No services configured
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        call_args = update.message.reply_text.call_args[0][0]
        error_message_lower = call_args.lower()

        # Should provide actionable guidance
        assert (
            "administrator" in error_message_lower or
            "admin" in error_message_lower or
            "contact" in error_message_lower or
            "configure" in error_message_lower or
            "set" in error_message_lower
        ), f"Expected actionable guidance in error message. Got: {call_args}"

    @pytest.mark.asyncio
    async def test_addchannel_error_does_not_expose_internal_details(self):
        """Test that addchannel error does not expose internal implementation details."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {}  # No services configured
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        call_args = update.message.reply_text.call_args[0][0]
        error_message_lower = call_args.lower()

        # Should NOT expose internal details
        assert "bot_data" not in error_message_lower
        assert "context" not in error_message_lower
        assert "traceback" not in error_message_lower
        assert "exception" not in error_message_lower


# =============================================================================
# Test: Search Service Injection (WS-7.3)
# =============================================================================


class TestSearchServiceInjection:
    """Tests for search service dependency injection (WS-7.3)."""

    def test_create_search_service_function_exists(self):
        """Test that a create_search_service function exists in __main__."""
        try:
            from src.tnse.bot.__main__ import create_search_service
            assert callable(create_search_service)
        except ImportError:
            pytest.fail("create_search_service function should exist in __main__.py")

    def test_create_search_service_returns_search_service_when_db_available(self):
        """Test that create_search_service returns a SearchService when db is available."""
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
        }, clear=False):
            from src.tnse.core.config import get_settings
            get_settings.cache_clear()

            mock_session_factory = MagicMock()

            from src.tnse.bot.__main__ import create_search_service
            from src.tnse.search.service import SearchService

            result = create_search_service(mock_session_factory)
            assert result is not None
            assert isinstance(result, SearchService)

    def test_create_search_service_returns_none_when_no_db_factory(self):
        """Test that create_search_service returns None when db_session_factory is None."""
        try:
            from src.tnse.bot.__main__ import create_search_service

            result = create_search_service(None)
            assert result is None
        except ImportError:
            pytest.fail("create_search_service function should exist in __main__.py")


class TestSearchServiceInjectionInApplication:
    """Tests for search service injection behavior in application.py."""

    def test_application_bot_data_contains_search_service_when_provided(self):
        """Test that search_service is properly stored in bot_data when provided."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        mock_search_service = MagicMock()
        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            search_service=mock_search_service,
        )

        assert app.bot_data.get("search_service") is mock_search_service

    def test_application_bot_data_excludes_search_service_when_none(self):
        """Test that search_service is NOT in bot_data when None."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456:ABC-DEF")

        app = create_bot_application(
            config=config,
            search_service=None,
        )

        # Should not have search_service key at all
        assert "search_service" not in app.bot_data


class TestSearchServiceStatusLogging:
    """Tests for search service status logging at bot startup."""

    def test_log_service_status_logs_search_service_available(self):
        """Test that log_service_status logs when search service is available."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:
            mock_search_service = MagicMock()

            log_service_status(
                search_service=mock_search_service,
            )

            # Should log info about available search service
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("search" in str(call).lower() for call in info_calls), \
                f"Expected info about search service. Got: {info_calls}"

    def test_log_service_status_logs_warning_when_search_service_unavailable(self):
        """Test that log_service_status logs warning when search service is None."""
        from src.tnse.bot.__main__ import log_service_status

        with patch("src.tnse.bot.__main__.logger") as mock_logger:

            log_service_status(
                search_service=None,
            )

            # Should log warning about missing search service
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "search" in str(call).lower()
                for call in warning_calls
            ), f"Expected warning about search service. Got: {warning_calls}"


class TestSearchHandlerErrorMessages:
    """Tests for clear error messages in search handlers when service not configured."""

    @pytest.mark.asyncio
    async def test_search_shows_configuration_error_message(self):
        """Test that search shows a helpful message when search_service is not configured."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["test", "query"]
        context.bot_data = {
            # search_service is missing (None)
        }
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

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
    async def test_search_error_does_not_expose_internal_details(self):
        """Test that search error does not expose internal implementation details."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["test"]
        context.bot_data = {}  # No services configured
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        call_args = update.message.reply_text.call_args[0][0]
        error_message_lower = call_args.lower()

        # Should NOT expose internal details
        assert "bot_data" not in error_message_lower
        assert "context" not in error_message_lower
        assert "traceback" not in error_message_lower
        assert "exception" not in error_message_lower

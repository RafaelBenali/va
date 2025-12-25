"""
Tests for TNSE Telegram bot command handlers.

Following TDD methodology: these tests are written BEFORE the implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStartCommand:
    """Tests for the /start command handler."""

    @pytest.mark.asyncio
    async def test_start_command_exists(self):
        """Test that start_command handler function exists."""
        from src.tnse.bot.handlers import start_command

        assert callable(start_command)

    @pytest.mark.asyncio
    async def test_start_command_sends_welcome_message(self):
        """Test that /start sends a welcome message."""
        from src.tnse.bot.handlers import start_command

        update = MagicMock()
        update.effective_user.first_name = "TestUser"
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await start_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Welcome message should contain greeting and user name
        assert "TestUser" in message or "Welcome" in message or "TNSE" in message

    @pytest.mark.asyncio
    async def test_start_command_mentions_help(self):
        """Test that /start mentions the /help command."""
        from src.tnse.bot.handlers import start_command

        update = MagicMock()
        update.effective_user.first_name = "TestUser"
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await start_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        assert "/help" in message


class TestHelpCommand:
    """Tests for the /help command handler."""

    @pytest.mark.asyncio
    async def test_help_command_exists(self):
        """Test that help_command handler function exists."""
        from src.tnse.bot.handlers import help_command

        assert callable(help_command)

    @pytest.mark.asyncio
    async def test_help_command_lists_available_commands(self):
        """Test that /help lists all available commands."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Help should mention core commands
        assert "/start" in message
        assert "/help" in message
        assert "/settings" in message

    @pytest.mark.asyncio
    async def test_help_command_includes_command_descriptions(self):
        """Test that /help includes descriptions for commands."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Check for some descriptive text (not just command names)
        assert len(message) > 50  # Should have some substance


class TestSettingsCommand:
    """Tests for the /settings command handler."""

    @pytest.mark.asyncio
    async def test_settings_command_exists(self):
        """Test that settings_command handler function exists."""
        from src.tnse.bot.handlers import settings_command

        assert callable(settings_command)

    @pytest.mark.asyncio
    async def test_settings_command_shows_current_settings(self):
        """Test that /settings shows current bot settings."""
        from src.tnse.bot.handlers import settings_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": MagicMock(polling_mode=True, allowed_users=[])}

        await settings_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Settings message should mention settings
        assert "settings" in message.lower() or "Settings" in message

    @pytest.mark.asyncio
    async def test_settings_command_shows_access_mode(self):
        """Test that /settings shows access mode (open or restricted)."""
        from src.tnse.bot.handlers import settings_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": MagicMock(polling_mode=True, allowed_users=[123, 456])}

        await settings_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should mention access mode
        assert "access" in message.lower() or "restricted" in message.lower() or "whitelist" in message.lower()


class TestUserWhitelist:
    """Tests for user whitelist access control."""

    @pytest.mark.asyncio
    async def test_check_user_access_function_exists(self):
        """Test that check_user_access function exists."""
        from src.tnse.bot.handlers import check_user_access

        assert callable(check_user_access)

    @pytest.mark.asyncio
    async def test_check_user_access_allows_when_no_whitelist(self):
        """Test that access is allowed when whitelist is empty."""
        from src.tnse.bot.handlers import check_user_access

        config = MagicMock()
        config.allowed_users = []

        result = await check_user_access(user_id=123456, config=config)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_user_access_allows_whitelisted_user(self):
        """Test that access is allowed for whitelisted user."""
        from src.tnse.bot.handlers import check_user_access

        config = MagicMock()
        config.allowed_users = [123456, 789012]

        result = await check_user_access(user_id=123456, config=config)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_user_access_denies_non_whitelisted_user(self):
        """Test that access is denied for non-whitelisted user."""
        from src.tnse.bot.handlers import check_user_access

        config = MagicMock()
        config.allowed_users = [123456, 789012]

        result = await check_user_access(user_id=999999, config=config)
        assert result is False

    @pytest.mark.asyncio
    async def test_access_denied_handler_exists(self):
        """Test that access_denied_handler function exists."""
        from src.tnse.bot.handlers import access_denied_handler

        assert callable(access_denied_handler)

    @pytest.mark.asyncio
    async def test_access_denied_handler_sends_message(self):
        """Test that access_denied_handler sends denial message."""
        from src.tnse.bot.handlers import access_denied_handler

        update = MagicMock()
        update.message.reply_text = AsyncMock()

        await access_denied_handler(update)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        assert "denied" in message.lower() or "authorized" in message.lower() or "access" in message.lower()


class TestAccessControlDecorator:
    """Tests for access control decorator/wrapper."""

    @pytest.mark.asyncio
    async def test_require_access_decorator_exists(self):
        """Test that require_access decorator exists."""
        from src.tnse.bot.handlers import require_access

        assert callable(require_access)

    @pytest.mark.asyncio
    async def test_require_access_allows_authorized_user(self):
        """Test that decorator allows authorized users through."""
        from src.tnse.bot.handlers import require_access

        # Create a mock handler
        mock_handler = AsyncMock(return_value="success")
        wrapped = require_access(mock_handler)

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": MagicMock(allowed_users=[])}  # Open access

        result = await wrapped(update, context)

        mock_handler.assert_called_once_with(update, context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_access_blocks_unauthorized_user(self):
        """Test that decorator blocks unauthorized users."""
        from src.tnse.bot.handlers import require_access

        # Create a mock handler
        mock_handler = AsyncMock(return_value="success")
        wrapped = require_access(mock_handler)

        update = MagicMock()
        update.effective_user.id = 999999  # Not in whitelist
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": MagicMock(allowed_users=[123456])}  # Restricted access

        result = await wrapped(update, context)

        # Handler should NOT be called
        mock_handler.assert_not_called()
        # Denial message should be sent
        update.message.reply_text.assert_called_once()


class TestErrorHandler:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_error_handler_exists(self):
        """Test that error_handler function exists."""
        from src.tnse.bot.handlers import error_handler

        assert callable(error_handler)

    @pytest.mark.asyncio
    async def test_error_handler_logs_error(self):
        """Test that error_handler logs the error."""
        from src.tnse.bot.handlers import error_handler

        update = MagicMock()
        context = MagicMock()
        context.error = Exception("Test error")

        with patch("src.tnse.bot.handlers.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            await error_handler(update, context)

            # Should have logged an error
            assert mock_logger.error.called or mock_logger.exception.called

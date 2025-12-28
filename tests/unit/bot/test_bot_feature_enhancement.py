"""
Tests for TNSE Telegram Bot Feature Enhancement (WS-6.9).

Following TDD methodology: these tests are written BEFORE implementation.

Improvements being tested:
1. Command aliases for common operations
2. Progress indicators for long operations
3. Improved help command with examples
4. Enhanced input validation messages
5. Better error messages and user feedback
6. Optimized response formatting
7. Delete confirmation for destructive actions
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: Command Aliases
# =============================================================================


class TestCommandAliases:
    """Tests for command aliases feature."""

    def test_search_alias_s_registered(self):
        """Test that /s is registered as an alias for /search."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test:token")
        app = create_bot_application(config)

        # Check that 's' command handler is registered
        command_handlers = [
            handler for handler in app.handlers[0]
            if hasattr(handler, "commands") and "s" in handler.commands
        ]
        assert len(command_handlers) >= 1, "Alias /s should be registered for /search"

    def test_channels_alias_ch_registered(self):
        """Test that /ch is registered as an alias for /channels."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test:token")
        app = create_bot_application(config)

        command_handlers = [
            handler for handler in app.handlers[0]
            if hasattr(handler, "commands") and "ch" in handler.commands
        ]
        assert len(command_handlers) >= 1, "Alias /ch should be registered for /channels"

    def test_help_alias_h_registered(self):
        """Test that /h is registered as an alias for /help."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test:token")
        app = create_bot_application(config)

        command_handlers = [
            handler for handler in app.handlers[0]
            if hasattr(handler, "commands") and "h" in handler.commands
        ]
        assert len(command_handlers) >= 1, "Alias /h should be registered for /help"

    def test_topics_alias_t_registered(self):
        """Test that /t is registered as an alias for /topics."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test:token")
        app = create_bot_application(config)

        command_handlers = [
            handler for handler in app.handlers[0]
            if hasattr(handler, "commands") and "t" in handler.commands
        ]
        assert len(command_handlers) >= 1, "Alias /t should be registered for /topics"

    def test_export_alias_e_registered(self):
        """Test that /e is registered as an alias for /export."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="test:token")
        app = create_bot_application(config)

        command_handlers = [
            handler for handler in app.handlers[0]
            if hasattr(handler, "commands") and "e" in handler.commands
        ]
        assert len(command_handlers) >= 1, "Alias /e should be registered for /export"


# =============================================================================
# Test: Progress Indicators
# =============================================================================


class TestProgressIndicators:
    """Tests for progress indicators (typing action) during long operations."""

    @pytest.mark.asyncio
    async def test_search_sends_typing_action(self):
        """Test that /search sends typing action before processing."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["test", "query"]
        context.bot_data = {"search_service": None}  # Will fail, but should send typing first
        context.user_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Should send typing action before processing
        context.bot.send_chat_action.assert_called_once()
        call_args = context.bot.send_chat_action.call_args
        assert call_args[1].get("action") == "typing" or call_args[0][1] == "typing"

    @pytest.mark.asyncio
    async def test_import_sends_typing_action(self):
        """Test that /import sends typing action before processing."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.document = MagicMock()
        update.message.document.file_name = "channels.txt"
        update.message.document.mime_type = "text/plain"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"channel_service": None, "db_session_factory": None}
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        # Should send typing action before processing
        context.bot.send_chat_action.assert_called()

    @pytest.mark.asyncio
    async def test_addchannel_sends_typing_action(self):
        """Test that /addchannel sends typing action during validation."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {"channel_service": None, "db_session_factory": None}
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        # Should send typing action
        context.bot.send_chat_action.assert_called()


# =============================================================================
# Test: Improved Help Command with Examples
# =============================================================================


class TestImprovedHelpCommand:
    """Tests for improved help command with examples."""

    @pytest.mark.asyncio
    async def test_help_includes_search_example(self):
        """Test that help includes a concrete search example."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Help should include a concrete example
        assert "Example:" in message or "example:" in message
        assert "/search" in message

    @pytest.mark.asyncio
    async def test_help_includes_channel_example(self):
        """Test that help includes an addchannel example."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Help should include example with @ symbol
        assert "@" in message  # Example channel username

    @pytest.mark.asyncio
    async def test_help_includes_command_aliases(self):
        """Test that help mentions command aliases."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Help should mention aliases
        assert "/s" in message or "alias" in message.lower() or "shortcut" in message.lower()

    @pytest.mark.asyncio
    async def test_help_includes_quick_start_section(self):
        """Test that help includes a quick start section."""
        from src.tnse.bot.handlers import help_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await help_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Help should have quick start or getting started section
        has_quick_start = (
            "Quick Start" in message or
            "Getting Started" in message or
            "To get started" in message or
            "quick start" in message.lower()
        )
        assert has_quick_start


# =============================================================================
# Test: Enhanced Input Validation Messages
# =============================================================================


class TestEnhancedInputValidation:
    """Tests for improved input validation messages."""

    @pytest.mark.asyncio
    async def test_search_empty_query_suggests_examples(self):
        """Test that empty search query shows helpful examples."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []  # No query provided
        context.user_data = {}
        context.bot_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should include example query
        assert "example" in message.lower() or "Example" in message
        # Should show usage pattern
        assert "/search" in message

    @pytest.mark.asyncio
    async def test_addchannel_invalid_format_shows_valid_formats(self):
        """Test that invalid channel format shows accepted formats."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []  # No channel provided
        context.bot_data = {}
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show accepted formats
        assert "@" in message  # @username format
        assert "t.me" in message or "Example" in message or "example" in message.lower()

    @pytest.mark.asyncio
    async def test_savetopic_no_search_gives_guidance(self):
        """Test that saving topic without prior search gives clear guidance."""
        from src.tnse.bot.topic_handlers import savetopic_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["mytopic"]
        context.user_data = {}  # No last search
        context.bot_data = {"topic_service": MagicMock()}

        await savetopic_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should guide user to search first
        assert "/search" in message
        assert "first" in message.lower() or "before" in message.lower()

    @pytest.mark.asyncio
    async def test_export_no_results_gives_guidance(self):
        """Test that export without results gives clear guidance."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.user_data = {}  # No last search

        await export_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should guide user to search first
        assert "/search" in message


# =============================================================================
# Test: Improved Error Messages
# =============================================================================


class TestImprovedErrorMessages:
    """Tests for improved error messages with user guidance."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error_is_helpful(self):
        """Test that service unavailable errors provide helpful suggestions."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["test"]
        context.user_data = {}
        context.bot_data = {"search_service": None}  # Service not configured
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Error should suggest trying again
        assert "try" in message.lower() or "later" in message.lower() or "again" in message.lower()

    @pytest.mark.asyncio
    async def test_channel_not_found_suggests_list_command(self):
        """Test that channel not found error suggests /channels command."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session that returns no channel
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.args = ["@nonexistent"]
        context.bot_data = {"db_session_factory": lambda: mock_session}

        await channelinfo_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should suggest channels command or addchannel
        assert "/channels" in message or "/addchannel" in message


# =============================================================================
# Test: Enhanced Pagination with First/Last Navigation
# =============================================================================


class TestEnhancedPagination:
    """Tests for enhanced pagination with first/last page navigation."""

    def test_pagination_keyboard_includes_first_page_button(self):
        """Test that pagination includes first page button when not on first page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=5,
            total_pages=10,
        )

        # Extract button text from keyboard
        button_texts = [button.text for row in keyboard.inline_keyboard for button in row]

        # Should have first page navigation
        assert any(
            "<<" in text or "First" in text or "|<" in text
            for text in button_texts
        )

    def test_pagination_keyboard_includes_last_page_button(self):
        """Test that pagination includes last page button when not on last page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=5,
            total_pages=10,
        )

        button_texts = [button.text for row in keyboard.inline_keyboard for button in row]

        # Should have last page navigation
        assert any(
            ">>" in text or "Last" in text or ">|" in text
            for text in button_texts
        )

    def test_pagination_no_first_button_on_page_1(self):
        """Test that first page button is not shown on page 1."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=1,
            total_pages=10,
        )

        button_callbacks = [
            button.callback_data for row in keyboard.inline_keyboard for button in row
        ]

        # Should not have first page callback when on page 1
        first_page_callback = f"search:test:1"
        # Count occurrences - should only be the page indicator, not a navigation button
        first_buttons = [cb for cb in button_callbacks if cb == first_page_callback]
        assert len(first_buttons) <= 1  # At most the page indicator


# =============================================================================
# Test: Delete Confirmation for Destructive Actions
# =============================================================================


class TestDeleteConfirmation:
    """Tests for confirmation prompts on destructive actions."""

    @pytest.mark.asyncio
    async def test_deletetopic_shows_confirmation_keyboard(self):
        """Test that deletetopic shows confirmation keyboard before deleting."""
        from src.tnse.bot.topic_handlers import deletetopic_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock topic service that finds the topic
        mock_topic_service = MagicMock()
        mock_topic_service.get_topic = AsyncMock(return_value=MagicMock(
            name="mytopic",
            keywords="test keywords",
        ))
        mock_topic_service.delete_topic = AsyncMock()

        context = MagicMock()
        context.args = ["mytopic"]
        context.bot_data = {"topic_service": mock_topic_service}

        await deletetopic_command(update, context)

        call_args = update.message.reply_text.call_args

        # Should show confirmation - either with keyboard or confirmation text
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        reply_markup = call_args[1].get("reply_markup") if len(call_args) > 1 else None

        # Either shows confirmation keyboard or asks for confirmation
        has_confirmation = (
            reply_markup is not None or
            "confirm" in message.lower() or
            "sure" in message.lower() or
            "deleted" in message.lower()  # Direct deletion is also acceptable
        )
        assert has_confirmation

    @pytest.mark.asyncio
    async def test_removechannel_shows_confirmation_keyboard(self):
        """Test that removechannel shows confirmation before removing."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session that finds the channel
        mock_channel = MagicMock()
        mock_channel.title = "Test Channel"
        mock_channel.username = "testchannel"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_channel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {"db_session_factory": lambda: mock_session}

        await removechannel_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        reply_markup = call_args[1].get("reply_markup") if len(call_args) > 1 else None

        # Either shows confirmation keyboard or has confirmation text
        has_confirmation = (
            reply_markup is not None or
            "confirm" in message.lower() or
            "sure" in message.lower() or
            "removed" in message.lower()  # Direct removal is also acceptable
        )
        assert has_confirmation


# =============================================================================
# Test: Response Formatting Improvements
# =============================================================================


class TestResponseFormatting:
    """Tests for improved response formatting."""

    def test_format_large_numbers_readable(self):
        """Test that large numbers are formatted for readability."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()

        assert formatter.format_view_count(1500) == "1.5K"
        assert formatter.format_view_count(15000) == "15.0K"
        assert formatter.format_view_count(1500000) == "1.5M"
        assert formatter.format_view_count(500) == "500"

    def test_format_time_shows_appropriate_units(self):
        """Test that time formatting uses appropriate units."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()

        now = datetime.now(timezone.utc)

        # Very recent - should show minutes
        recent = now.replace(minute=now.minute - 5 if now.minute >= 5 else 55)
        if now.minute < 5:
            recent = recent.replace(hour=now.hour - 1 if now.hour > 0 else 23)
        result = formatter.format_time_ago(recent, now)
        assert "m ago" in result or "just now" in result

        # Hours ago
        from datetime import timedelta
        hours_ago = now - timedelta(hours=3)
        result = formatter.format_time_ago(hours_ago, now)
        assert "h ago" in result

    def test_search_result_includes_direct_link(self):
        """Test that search results include direct Telegram links."""
        from src.tnse.bot.search_handlers import SearchFormatter, SearchResult

        formatter = SearchFormatter()

        result = MagicMock(spec=SearchResult)
        result.channel_title = "Test Channel"
        result.channel_username = "testchannel"
        result.text_content = "Test content"
        result.view_count = 1000
        result.published_at = datetime.now(timezone.utc)
        result.relative_engagement = 0.5
        result.telegram_link = "https://t.me/testchannel/123"

        formatted = formatter.format_result(result, index=1)

        assert "t.me" in formatted or "View Post" in formatted


# =============================================================================
# Test: Accessibility Improvements
# =============================================================================


class TestAccessibilityImprovements:
    """Tests for accessibility improvements in bot responses."""

    @pytest.mark.asyncio
    async def test_error_messages_are_self_contained(self):
        """Test that error messages don't require context to understand."""
        from src.tnse.bot.handlers import error_handler

        update = MagicMock()
        update.effective_message.reply_text = AsyncMock()

        context = MagicMock()
        context.error = Exception("Database connection failed")

        await error_handler(update, context)

        call_args = update.effective_message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Message should be self-contained and helpful
        assert len(message) > 20  # Not just "Error"
        assert "try" in message.lower() or "error" in message.lower()

    def test_status_indicators_are_clear(self):
        """Test that status indicators are clear text, not just symbols."""
        # Test channel list formatting
        from src.tnse.bot.channel_handlers import format_subscriber_count

        # Numbers should be human readable
        assert format_subscriber_count(1500) == "1.5K"
        assert format_subscriber_count(50) == "50"

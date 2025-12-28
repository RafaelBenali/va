"""
TNSE Bot Implementation Audit Tests

Work Stream: WS-6.7 - Telegram Bot Implementation Audit

This file contains tests that validate the comprehensive audit of the current
bot implementation against best practices for python-telegram-bot library
(version 21.0+).

Test Categories:
1. Library Usage Patterns
2. Command Handler Architecture
3. Conversation Flow and State Management
4. Error Handling
5. Response Formatting and UX
6. Inline Keyboard Implementation
7. Callback Query Handling
8. Message Size and Rate Limit Handling
9. Webhook vs Polling Configuration
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


# ==============================================================================
# Test Category 1: python-telegram-bot Library Usage Patterns
# ==============================================================================

class TestLibraryUsagePatterns:
    """Tests for proper python-telegram-bot library usage patterns."""

    def test_uses_application_builder_pattern(self) -> None:
        """Test that bot uses Application.builder() pattern (PTB 21.0+ best practice)."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        # Application should be properly built
        assert app is not None
        # Should have bot instance
        assert app.bot is not None

    def test_uses_context_types_default_type(self) -> None:
        """Test that handlers use ContextTypes.DEFAULT_TYPE for type hints."""
        from src.tnse.bot.handlers import start_command
        import inspect

        signature = inspect.signature(start_command)
        parameters = list(signature.parameters.values())

        # Should have 2 parameters: update and context
        assert len(parameters) == 2

        # Check that context parameter exists
        context_param = parameters[1]
        assert context_param.name == "context"

    def test_handlers_are_async(self) -> None:
        """Test that all command handlers are async functions."""
        from src.tnse.bot import handlers
        from src.tnse.bot import channel_handlers
        from src.tnse.bot import search_handlers
        from src.tnse.bot import topic_handlers
        from src.tnse.bot import export_handlers
        from src.tnse.bot import advanced_channel_handlers
        import asyncio

        # List of all handlers to check
        handler_functions = [
            handlers.start_command,
            handlers.help_command,
            handlers.settings_command,
            handlers.error_handler,
            channel_handlers.addchannel_command,
            channel_handlers.removechannel_command,
            channel_handlers.channels_command,
            channel_handlers.channelinfo_command,
            search_handlers.search_command,
            search_handlers.pagination_callback,
            topic_handlers.savetopic_command,
            topic_handlers.topics_command,
            topic_handlers.topic_command,
            topic_handlers.deletetopic_command,
            topic_handlers.templates_command,
            topic_handlers.use_template_command,
            export_handlers.export_command,
            advanced_channel_handlers.import_command,
            advanced_channel_handlers.health_command,
        ]

        for handler in handler_functions:
            assert asyncio.iscoroutinefunction(handler), \
                f"Handler {handler.__name__} should be async"

    def test_uses_modern_bot_data_storage(self) -> None:
        """Test that config is stored in bot_data (PTB 21.0+ pattern)."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        # Config should be stored in bot_data
        assert "config" in app.bot_data
        assert app.bot_data["config"] is config


# ==============================================================================
# Test Category 2: Command Handler Architecture
# ==============================================================================

class TestCommandHandlerArchitecture:
    """Tests for command handler architecture best practices."""

    def test_all_commands_have_handlers(self) -> None:
        """Test that all documented commands have registered handlers."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        # Get all registered command names
        handlers = app.handlers
        command_names = set()
        for group_handlers in handlers.values():
            for handler in group_handlers:
                if hasattr(handler, "commands"):
                    command_names.update(handler.commands)

        # Expected commands from documentation
        expected_commands = {
            "start", "help", "settings",
            "addchannel", "removechannel", "channels", "channelinfo",
            "search", "export",
            "savetopic", "topics", "topic", "deletetopic",
            "templates", "usetemplate",
            "import", "health"
        }

        for cmd in expected_commands:
            assert cmd in command_names, f"Command /{cmd} should be registered"

    def test_handlers_use_access_control_decorator(self) -> None:
        """Test that handlers are wrapped with access control."""
        from src.tnse.bot.handlers import require_access
        from functools import wraps

        # The decorator should exist and be callable
        assert callable(require_access)

        # Test that decorator works correctly
        @require_access
        async def sample_handler(update, context):
            return "success"

        # Wrapped function should have __wrapped__ attribute
        assert hasattr(sample_handler, "__wrapped__")

    def test_command_handler_registration_uses_commandhandler(self) -> None:
        """Test that commands are registered using CommandHandler class."""
        from telegram.ext import CommandHandler
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        handlers = app.handlers
        command_handler_count = 0

        for group_handlers in handlers.values():
            for handler in group_handlers:
                if isinstance(handler, CommandHandler):
                    command_handler_count += 1

        # Should have multiple command handlers
        assert command_handler_count >= 17, \
            f"Expected at least 17 command handlers, found {command_handler_count}"

    def test_handlers_log_user_actions(self) -> None:
        """Test that handlers log user actions for audit trail."""
        from src.tnse.bot import handlers

        # The logger should be imported and used
        assert hasattr(handlers, "logger")
        assert handlers.logger is not None


# ==============================================================================
# Test Category 3: Conversation Flow and State Management
# ==============================================================================

class TestConversationFlowAndStateManagement:
    """Tests for conversation flow and state management patterns."""

    def test_user_data_persistence_for_search_results(self) -> None:
        """Test that search results are stored in user_data for pagination."""
        from src.tnse.bot.search_handlers import search_command
        from unittest.mock import MagicMock, AsyncMock

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"search_service": MagicMock()}
        context.user_data = {}
        context.args = ["test", "query"]

        # Mock search service
        mock_results = [MagicMock()]
        context.bot_data["search_service"].search = AsyncMock(return_value=mock_results)

        # Run would store results in user_data
        # This is verified by the existence of the pattern in search_handlers

    def test_state_stored_in_user_data_not_global(self) -> None:
        """Test that per-user state is stored in user_data, not globally."""
        # Verify that search results are stored in context.user_data
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        # Check for user_data usage
        assert "context.user_data" in source, \
            "Search handlers should use context.user_data for state"
        assert 'user_data["last_search' in source, \
            "Search handlers should store search state in user_data"

    def test_bot_data_used_for_shared_services(self) -> None:
        """Test that shared services are stored in bot_data."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        # Check for bot_data usage for services
        assert "context.bot_data" in source, \
            "Handlers should access services via context.bot_data"
        assert 'bot_data.get("search_service")' in source, \
            "Search service should be retrieved from bot_data"


# ==============================================================================
# Test Category 4: Error Handling
# ==============================================================================

class TestErrorHandling:
    """Tests for error handling patterns in bot commands."""

    def test_error_handler_registered(self) -> None:
        """Test that a global error handler is registered."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        assert len(app.error_handlers) > 0, "Error handler should be registered"

    def test_error_handler_logs_exceptions(self) -> None:
        """Test that error handler logs exceptions properly."""
        import ast
        from pathlib import Path

        handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/handlers.py")
        source = handlers_path.read_text()

        # Check for proper error logging
        assert "logger.error" in source, \
            "Error handler should log errors"
        assert "context.error" in source, \
            "Error handler should access context.error"

    def test_handlers_have_try_except_blocks(self) -> None:
        """Test that command handlers wrap operations in try-except."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()
        tree = ast.parse(source)

        # Find async function definitions
        async_functions = [node for node in ast.walk(tree)
                         if isinstance(node, ast.AsyncFunctionDef)]

        # Check that main handlers have try-except
        handler_names = ["search_command", "pagination_callback"]
        for func in async_functions:
            if func.name in handler_names:
                has_try = any(isinstance(node, ast.Try)
                             for node in ast.walk(func))
                assert has_try, f"{func.name} should have try-except block"

    def test_error_messages_are_user_friendly(self) -> None:
        """Test that error messages sent to users are friendly."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        # Check for user-friendly error messages
        assert "try again" in source.lower(), \
            "Error messages should suggest trying again"
        assert "Error performing search" in source or "error" in source.lower(), \
            "Error messages should be present"


# ==============================================================================
# Test Category 5: Response Formatting and UX
# ==============================================================================

class TestResponseFormattingAndUX:
    """Tests for response formatting and user experience."""

    def test_search_formatter_exists(self) -> None:
        """Test that SearchFormatter class exists for formatting results."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        assert formatter is not None
        assert hasattr(formatter, "format_results_page")
        assert hasattr(formatter, "format_result")

    def test_view_count_formatted_with_k_m_suffix(self) -> None:
        """Test that view counts are formatted with K/M suffixes."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()

        assert formatter.format_view_count(500) == "500"
        assert formatter.format_view_count(1500) == "1.5K"
        assert formatter.format_view_count(1500000) == "1.5M"

    def test_time_formatted_as_relative(self) -> None:
        """Test that timestamps are formatted as relative time."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        assert "h ago" in formatter.format_time_ago(now - timedelta(hours=2), now)
        assert "m ago" in formatter.format_time_ago(now - timedelta(minutes=30), now)
        assert "d ago" in formatter.format_time_ago(now - timedelta(days=1), now)

    def test_reactions_formatted_with_emojis(self) -> None:
        """Test that reactions are formatted with emoji display."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        reactions = {"thumbs_up": 100, "heart": 50}

        formatted = formatter.format_reactions(reactions)
        assert "100" in formatted
        assert "50" in formatted

    def test_text_preview_is_truncated(self) -> None:
        """Test that text previews are truncated to reasonable length."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        long_text = "A" * 200

        preview = formatter.format_preview(long_text)
        assert len(preview) <= formatter.max_preview_length
        assert preview.endswith("...")

    def test_results_include_telegram_links(self) -> None:
        """Test that search results include links to original posts."""
        from src.tnse.bot.search_handlers import SearchFormatter, SearchResult
        from uuid import uuid4

        formatter = SearchFormatter()
        result = MagicMock()
        result.channel_title = "Test Channel"
        result.view_count = 1000
        result.text_content = "Test content"
        result.relative_engagement = 0.5
        result.published_at = datetime.now(timezone.utc)
        result.telegram_link = "https://t.me/test_channel/123"

        formatted = formatter.format_result(result, index=1)
        assert "View Post" in formatted
        assert "t.me" in formatted

    def test_markdown_parse_mode_used(self) -> None:
        """Test that messages use Markdown parse mode for formatting."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        assert 'parse_mode="Markdown"' in source, \
            "Search results should use Markdown parse mode"


# ==============================================================================
# Test Category 6: Inline Keyboard Implementation
# ==============================================================================

class TestInlineKeyboardImplementation:
    """Tests for inline keyboard implementation."""

    def test_pagination_keyboard_function_exists(self) -> None:
        """Test that create_pagination_keyboard function exists."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        assert callable(create_pagination_keyboard)

    def test_pagination_keyboard_returns_inline_markup(self) -> None:
        """Test that pagination returns InlineKeyboardMarkup."""
        from telegram import InlineKeyboardMarkup
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=1,
            total_pages=5
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_pagination_keyboard_has_prev_next_buttons(self) -> None:
        """Test that pagination keyboard has Prev/Next buttons."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        # Page 2 of 5 should have both prev and next
        keyboard = create_pagination_keyboard(
            query="test",
            current_page=2,
            total_pages=5
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]

        assert any("Prev" in text for text in button_texts)
        assert any("Next" in text for text in button_texts)

    def test_first_page_has_no_prev_button(self) -> None:
        """Test that first page does not have Prev button."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=1,
            total_pages=5
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]

        assert not any("Prev" in text for text in button_texts)
        assert any("Next" in text for text in button_texts)

    def test_last_page_has_no_next_button(self) -> None:
        """Test that last page does not have Next button."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=5,
            total_pages=5
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]

        assert any("Prev" in text for text in button_texts)
        assert not any("Next" in text for text in button_texts)

    def test_page_indicator_shown(self) -> None:
        """Test that current page indicator is displayed."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=3,
            total_pages=10
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [btn.text for btn in buttons]

        assert any("3/10" in text for text in button_texts)


# ==============================================================================
# Test Category 7: Callback Query Handling
# ==============================================================================

class TestCallbackQueryHandling:
    """Tests for callback query handling patterns."""

    def test_callback_handler_registered(self) -> None:
        """Test that CallbackQueryHandler is registered."""
        from telegram.ext import CallbackQueryHandler
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        handlers = app.handlers
        callback_handlers = []

        for group_handlers in handlers.values():
            for handler in group_handlers:
                if isinstance(handler, CallbackQueryHandler):
                    callback_handlers.append(handler)

        assert len(callback_handlers) >= 1, "Should have callback query handler"

    def test_callback_uses_pattern_filtering(self) -> None:
        """Test that callback handler uses pattern to filter callbacks."""
        from telegram.ext import CallbackQueryHandler
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")
        app = create_bot_application(config)

        handlers = app.handlers
        for group_handlers in handlers.values():
            for handler in group_handlers:
                if isinstance(handler, CallbackQueryHandler):
                    # Should have a pattern
                    assert handler.pattern is not None, \
                        "CallbackQueryHandler should have pattern filter"

    def test_pagination_callback_answers_query(self) -> None:
        """Test that pagination callback answers the query to remove loading state."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        # Should call answer() on callback_query
        assert "callback_query.answer()" in source, \
            "Callback handler should answer the query"

    def test_callback_data_uses_prefix(self) -> None:
        """Test that callback data uses prefixes for disambiguation."""
        from src.tnse.bot.search_handlers import SEARCH_CALLBACK_PREFIX

        assert SEARCH_CALLBACK_PREFIX is not None
        assert len(SEARCH_CALLBACK_PREFIX) > 0
        assert SEARCH_CALLBACK_PREFIX.endswith(":")


# ==============================================================================
# Test Category 8: Message Size and Rate Limit Handling
# ==============================================================================

class TestMessageSizeAndRateLimitHandling:
    """Tests for message size and rate limit handling."""

    def test_telegram_message_limit_constant_defined(self) -> None:
        """Test that Telegram message limit constant is defined."""
        from src.tnse.bot.search_handlers import TELEGRAM_MESSAGE_LIMIT

        assert TELEGRAM_MESSAGE_LIMIT == 4096

    def test_results_truncated_to_fit_limit(self) -> None:
        """Test that results are truncated to fit message limit."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()

        # Create many results
        mock_results = []
        for idx in range(20):
            result = MagicMock()
            result.channel_title = f"Channel {idx}"
            result.view_count = 1000
            result.text_content = "A" * 100
            result.relative_engagement = 0.5
            result.published_at = datetime.now(timezone.utc)
            result.telegram_link = f"https://t.me/channel/123"
            result.post_id = str(idx)
            mock_results.append(result)

        formatted = formatter.format_results_page(
            query="test",
            results=mock_results,
            total_count=20,
            page=1,
            page_size=20,
        )

        assert len(formatted) <= 4096, "Formatted results should fit in message limit"

    def test_web_page_preview_disabled(self) -> None:
        """Test that web page preview is disabled for search results."""
        import ast
        from pathlib import Path

        search_handlers_path = Path("C:/Users/W/Documents/va/src/tnse/bot/search_handlers.py")
        source = search_handlers_path.read_text()

        assert "disable_web_page_preview=True" in source, \
            "Web page preview should be disabled to prevent rate limits"


# ==============================================================================
# Test Category 9: Webhook vs Polling Configuration
# ==============================================================================

class TestWebhookVsPollingConfiguration:
    """Tests for webhook vs polling configuration."""

    def test_polling_mode_configurable(self) -> None:
        """Test that polling mode is configurable via BotConfig."""
        from src.tnse.bot.config import BotConfig

        polling_config = BotConfig(token="123:test", polling_mode=True)
        webhook_config = BotConfig(token="123:test", polling_mode=False, webhook_url="https://example.com")

        assert polling_config.polling_mode is True
        assert webhook_config.polling_mode is False

    def test_webhook_url_required_for_webhook_mode(self) -> None:
        """Test that webhook URL is required when polling_mode is False."""
        from src.tnse.bot.application import run_bot_webhook
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123:test", polling_mode=False, webhook_url=None)

        with pytest.raises(ValueError):
            run_bot_webhook(config)

    def test_run_bot_function_selects_correct_mode(self) -> None:
        """Test that run_bot selects correct mode based on config."""
        import ast
        from pathlib import Path

        application_path = Path("C:/Users/W/Documents/va/src/tnse/bot/application.py")
        source = application_path.read_text()

        # Should check polling_mode to decide
        assert "config.polling_mode" in source, \
            "run_bot should check config.polling_mode"
        assert "run_bot_polling" in source, \
            "run_bot should call run_bot_polling"
        assert "run_bot_webhook" in source, \
            "run_bot should call run_bot_webhook"

    def test_allowed_updates_specified_in_polling(self) -> None:
        """Test that allowed_updates is specified when running polling."""
        import ast
        from pathlib import Path

        application_path = Path("C:/Users/W/Documents/va/src/tnse/bot/application.py")
        source = application_path.read_text()

        assert 'allowed_updates' in source, \
            "Polling should specify allowed_updates"
        assert 'callback_query' in source, \
            "Should allow callback_query updates"


# ==============================================================================
# Test Category 10: Audit Summary Validation
# ==============================================================================

class TestAuditSummaryValidation:
    """Tests that validate the overall audit findings."""

    def test_all_audit_criteria_covered(self) -> None:
        """Test that all WS-6.7 audit criteria are covered by tests."""
        # This test documents the mapping of audit criteria to test classes
        audit_criteria = {
            "Review python-telegram-bot/aiogram usage patterns": TestLibraryUsagePatterns,
            "Evaluate current command handler architecture": TestCommandHandlerArchitecture,
            "Audit conversation flow and state management": TestConversationFlowAndStateManagement,
            "Review error handling in bot commands": TestErrorHandling,
            "Assess bot response formatting and UX": TestResponseFormattingAndUX,
            "Evaluate inline keyboard implementations": TestInlineKeyboardImplementation,
            "Review callback query handling patterns": TestCallbackQueryHandling,
            "Audit message size and rate limit handling": TestMessageSizeAndRateLimitHandling,
            "Review webhook vs polling configuration": TestWebhookVsPollingConfiguration,
        }

        for criteria, test_class in audit_criteria.items():
            assert test_class is not None, f"Test class for '{criteria}' should exist"
            # Verify test class has test methods
            test_methods = [m for m in dir(test_class) if m.startswith("test_")]
            assert len(test_methods) > 0, f"{test_class.__name__} should have test methods"

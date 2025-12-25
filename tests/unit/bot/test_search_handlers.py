"""
Tests for TNSE Telegram bot search command handlers.

Work Stream: WS-2.4 - Search Bot Commands

Following TDD methodology: these tests are written BEFORE the implementation.

Requirements tested:
- /search <query> command implementation
- Result formatting with metrics display
- Emoji reaction breakdown display
- Inline keyboard pagination
- Telegram message length limits (4096 chars)
- Telegram links to original posts
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestSearchFormatter:
    """Tests for the SearchFormatter class that formats search results."""

    def test_search_formatter_exists(self):
        """Test that SearchFormatter class exists."""
        from src.tnse.bot.search_handlers import SearchFormatter

        assert SearchFormatter is not None

    def test_format_view_count_thousands(self):
        """Test formatting view count as K for thousands."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        assert formatter.format_view_count(1500) == "1.5K"
        assert formatter.format_view_count(12500) == "12.5K"
        assert formatter.format_view_count(999) == "999"

    def test_format_view_count_millions(self):
        """Test formatting view count as M for millions."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        assert formatter.format_view_count(1500000) == "1.5M"
        assert formatter.format_view_count(12500000) == "12.5M"

    def test_format_time_ago(self):
        """Test formatting relative time."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        # 30 minutes ago
        time_30m = now - timedelta(minutes=30)
        assert "30m" in formatter.format_time_ago(time_30m, now)

        # 2 hours ago
        time_2h = now - timedelta(hours=2)
        assert "2h" in formatter.format_time_ago(time_2h, now)

        # 12 hours ago
        time_12h = now - timedelta(hours=12)
        assert "12h" in formatter.format_time_ago(time_12h, now)

    def test_format_reactions_with_emojis(self):
        """Test formatting reaction counts with emoji labels."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        reactions = {"thumbs_up": 150, "heart": 89, "fire": 34}

        formatted = formatter.format_reactions(reactions)

        # Should contain reaction counts with appropriate indicators
        assert "150" in formatted
        assert "89" in formatted
        assert "34" in formatted

    def test_format_reactions_empty(self):
        """Test formatting empty reactions."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        formatted = formatter.format_reactions({})

        # Should return something indicating no reactions
        assert formatted == "" or "No reactions" in formatted or formatted is None

    def test_format_score(self):
        """Test formatting combined score."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        assert formatter.format_score(0.2567) == "0.26"
        assert formatter.format_score(1.234) == "1.23"
        assert formatter.format_score(0.0) == "0.00"

    def test_format_preview_truncates(self):
        """Test that preview text is truncated at reasonable length."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        long_text = "A" * 500
        preview = formatter.format_preview(long_text)

        # Preview should be truncated
        assert len(preview) < 200
        assert preview.endswith("...")

    def test_format_preview_short_text(self):
        """Test that short text is not truncated."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()
        short_text = "Short message"
        preview = formatter.format_preview(short_text)

        assert preview == short_text
        assert "..." not in preview


class TestSearchResultFormatting:
    """Tests for formatting complete search results."""

    def test_format_single_result(self):
        """Test formatting a single search result."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Minister caught accepting bribes in corruption scandal",
            published_at=now - timedelta(hours=2),
            view_count=12500,
            reaction_score=273.0,
            relative_engagement=0.25,
            telegram_message_id=123,
        )

        formatted = formatter.format_result(result, index=1, reference_time=now)

        # Should contain essential elements
        assert "Test Channel" in formatted
        assert "12.5K" in formatted or "12500" in formatted
        assert "View Post" in formatted or "t.me" in formatted
        assert "Minister caught" in formatted

    def test_format_results_page(self):
        """Test formatting a page of search results."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username=f"channel_{index}",
                channel_title=f"Channel {index}",
                text_content=f"Post content {index}",
                published_at=now - timedelta(hours=index),
                view_count=1000 * index,
                reaction_score=100.0 * index,
                relative_engagement=0.1 * index,
                telegram_message_id=index * 10,
            )
            for index in range(1, 6)
        ]

        formatted = formatter.format_results_page(
            query="test query",
            results=results,
            total_count=47,
            page=1,
            page_size=5,
            reference_time=now,
        )

        # Should contain header with query and result count
        assert "test query" in formatted
        assert "47" in formatted
        assert "1-5" in formatted or "showing 1" in formatted

        # Should contain all results
        assert "Channel 1" in formatted
        assert "Channel 5" in formatted

    def test_format_results_respects_message_limit(self):
        """Test that formatted results respect Telegram's 4096 char limit."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        # Create many results with long content
        results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username=f"very_long_channel_name_{index}",
                channel_title=f"Very Long Channel Name Number {index}",
                text_content="A" * 200,  # Long content
                published_at=now - timedelta(hours=index),
                view_count=1000 * index,
                reaction_score=100.0 * index,
                relative_engagement=0.1 * index,
                telegram_message_id=index * 10,
            )
            for index in range(1, 20)
        ]

        formatted = formatter.format_results_page(
            query="test query",
            results=results,
            total_count=100,
            page=1,
            page_size=20,
            reference_time=now,
        )

        # Must be under Telegram's limit
        assert len(formatted) <= 4096


class TestPaginationKeyboard:
    """Tests for pagination inline keyboard generation."""

    def test_create_pagination_keyboard_first_page(self):
        """Test pagination keyboard on first page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=1,
            total_pages=10,
        )

        # Should be an InlineKeyboardMarkup
        from telegram import InlineKeyboardMarkup
        assert isinstance(keyboard, InlineKeyboardMarkup)

        # Should have navigation buttons
        buttons = keyboard.inline_keyboard[0]
        button_texts = [button.text for button in buttons]

        # First page should not have "Prev" or it should be disabled
        # Should have page indicator and Next
        assert any("1/10" in text or "1" in text for text in button_texts)
        assert any("Next" in text or ">>" in text for text in button_texts)

    def test_create_pagination_keyboard_middle_page(self):
        """Test pagination keyboard on middle page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=5,
            total_pages=10,
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [button.text for button in buttons]

        # Middle page should have both Prev and Next
        assert any("Prev" in text or "<<" in text for text in button_texts)
        assert any("Next" in text or ">>" in text for text in button_texts)
        assert any("5/10" in text or "5" in text for text in button_texts)

    def test_create_pagination_keyboard_last_page(self):
        """Test pagination keyboard on last page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=10,
            total_pages=10,
        )

        buttons = keyboard.inline_keyboard[0]
        button_texts = [button.text for button in buttons]

        # Last page should have Prev but not Next (or Next disabled)
        assert any("Prev" in text or "<<" in text for text in button_texts)
        assert any("10/10" in text or "10" in text for text in button_texts)

    def test_create_pagination_keyboard_single_page(self):
        """Test pagination keyboard with only one page."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="test",
            current_page=1,
            total_pages=1,
        )

        # Single page might have no navigation or just page indicator
        # The keyboard should still be valid
        from telegram import InlineKeyboardMarkup
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_pagination_callback_data_format(self):
        """Test that pagination buttons have proper callback data."""
        from src.tnse.bot.search_handlers import create_pagination_keyboard

        keyboard = create_pagination_keyboard(
            query="corruption",
            current_page=1,
            total_pages=10,
        )

        buttons = keyboard.inline_keyboard[0]

        # Find the Next button
        next_button = None
        for button in buttons:
            if "Next" in button.text or ">>" in button.text:
                next_button = button
                break

        if next_button:
            # Callback data should encode query and target page
            assert "corruption" in next_button.callback_data or "2" in next_button.callback_data


class TestSearchCommand:
    """Tests for the /search command handler."""

    @pytest.mark.asyncio
    async def test_search_command_exists(self):
        """Test that search_command handler function exists."""
        from src.tnse.bot.search_handlers import search_command

        assert callable(search_command)

    @pytest.mark.asyncio
    async def test_search_command_without_query_shows_usage(self):
        """Test /search without query shows usage message."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []

        await search_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        assert "Usage" in message or "/search" in message

    @pytest.mark.asyncio
    async def test_search_command_executes_search(self):
        """Test /search with query executes search service."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        now = datetime.now(timezone.utc)
        mock_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="test_channel",
                channel_title="Test Channel",
                text_content="Test content",
                published_at=now - timedelta(hours=1),
                view_count=1000,
                reaction_score=100.0,
                relative_engagement=0.5,
                telegram_message_id=123,
            )
        ]

        mock_search_service = AsyncMock()
        mock_search_service.search.return_value = mock_results

        context = MagicMock()
        context.args = ["corruption", "news"]
        context.bot_data = {
            "search_service": mock_search_service,
        }

        await search_command(update, context)

        # Search service should have been called
        mock_search_service.search.assert_called_once()
        call_args = mock_search_service.search.call_args
        # Query should combine all args
        assert "corruption" in call_args[1].get("query", "") or "corruption" in str(call_args)

    @pytest.mark.asyncio
    async def test_search_command_shows_results_with_keyboard(self):
        """Test /search shows results with pagination keyboard."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult
        from telegram import InlineKeyboardMarkup

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        now = datetime.now(timezone.utc)
        mock_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username=f"channel_{index}",
                channel_title=f"Channel {index}",
                text_content=f"Content {index}",
                published_at=now - timedelta(hours=index),
                view_count=1000 * index,
                reaction_score=100.0,
                relative_engagement=0.5,
                telegram_message_id=index * 10,
            )
            for index in range(1, 11)  # 10 results
        ]

        mock_search_service = AsyncMock()
        mock_search_service.search.return_value = mock_results

        context = MagicMock()
        context.args = ["test"]
        context.bot_data = {
            "search_service": mock_search_service,
        }

        await search_command(update, context)

        # Should have called reply_text with reply_markup
        update.message.reply_text.assert_called()
        call_kwargs = update.message.reply_text.call_args[1]

        # If there are multiple pages, should have keyboard
        if len(mock_results) > 5:  # Assuming 5 per page
            assert "reply_markup" in call_kwargs
            assert isinstance(call_kwargs["reply_markup"], InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_search_command_no_results(self):
        """Test /search with no results shows appropriate message."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        mock_search_service = AsyncMock()
        mock_search_service.search.return_value = []

        context = MagicMock()
        context.args = ["nonexistent"]
        context.bot_data = {
            "search_service": mock_search_service,
        }

        await search_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        assert "No results" in message or "no results" in message or "found 0" in message.lower()

    @pytest.mark.asyncio
    async def test_search_command_service_unavailable(self):
        """Test /search when search service is not available."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["test"]
        context.bot_data = {}  # No search service

        await search_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        assert "not available" in message.lower() or "unavailable" in message.lower() or "try again" in message.lower()


class TestPaginationCallback:
    """Tests for pagination callback handler."""

    @pytest.mark.asyncio
    async def test_pagination_callback_handler_exists(self):
        """Test that pagination_callback handler function exists."""
        from src.tnse.bot.search_handlers import pagination_callback

        assert callable(pagination_callback)

    @pytest.mark.asyncio
    async def test_pagination_callback_updates_message(self):
        """Test pagination callback updates the message with new page."""
        from src.tnse.bot.search_handlers import pagination_callback
        from src.tnse.search.service import SearchResult

        now = datetime.now(timezone.utc)
        mock_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username=f"channel_{index}",
                channel_title=f"Channel {index}",
                text_content=f"Content {index}",
                published_at=now - timedelta(hours=index),
                view_count=1000 * index,
                reaction_score=100.0,
                relative_engagement=0.5,
                telegram_message_id=index * 10,
            )
            for index in range(1, 11)
        ]

        mock_search_service = AsyncMock()
        mock_search_service.search.return_value = mock_results

        update = MagicMock()
        update.callback_query.data = "search:test:2"  # page 2
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "search_service": mock_search_service,
        }

        await pagination_callback(update, context)

        # Should answer the callback query
        update.callback_query.answer.assert_called()
        # Should edit the message with new content
        update.callback_query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_pagination_callback_ignores_invalid_data(self):
        """Test pagination callback handles invalid callback data gracefully."""
        from src.tnse.bot.search_handlers import pagination_callback

        update = MagicMock()
        update.callback_query.data = "invalid_data"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {}

        # Should not raise an exception
        await pagination_callback(update, context)

        # Should at least answer the callback
        update.callback_query.answer.assert_called()


class TestResultsWithReactions:
    """Tests for displaying reaction breakdowns in results."""

    def test_format_result_includes_reactions(self):
        """Test that formatted result includes reaction breakdown."""
        from src.tnse.bot.search_handlers import SearchFormatter

        formatter = SearchFormatter()

        # Mock a result with reactions stored in context
        # Note: SearchResult doesn't have reactions directly,
        # they would need to be fetched separately or stored

        result_with_reactions = {
            "channel_title": "Test Channel",
            "view_count": 12500,
            "reactions": {"thumbs_up": 150, "heart": 89, "fire": 34},
            "reaction_score": 273.0,
        }

        formatted_reactions = formatter.format_reactions(result_with_reactions.get("reactions", {}))

        # Should show individual emoji counts
        assert "150" in formatted_reactions
        assert "89" in formatted_reactions
        assert "34" in formatted_reactions


class TestTelegramLinks:
    """Tests for Telegram post links in results."""

    def test_format_result_includes_link(self):
        """Test that formatted result includes Telegram link."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        now = datetime.now(timezone.utc)

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=now - timedelta(hours=1),
            view_count=1000,
            reaction_score=100.0,
            relative_engagement=0.5,
            telegram_message_id=456,
        )

        formatted = formatter.format_result(result, index=1, reference_time=now)

        # Should contain Telegram link
        assert "t.me/test_channel/456" in formatted or "View Post" in formatted

    def test_telegram_link_property_exists(self):
        """Test that SearchResult has telegram_link property."""
        from src.tnse.search.service import SearchResult

        now = datetime.now(timezone.utc)

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=now,
            view_count=1000,
            reaction_score=100.0,
            relative_engagement=0.5,
            telegram_message_id=789,
        )

        assert result.telegram_link == "https://t.me/test_channel/789"

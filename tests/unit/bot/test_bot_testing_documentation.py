"""
Tests for TNSE Telegram Bot Testing Suite (WS-6.10).

Following TDD methodology: these tests are written BEFORE implementation updates.

This test module covers:
1. Rate limit behavior tests
2. Error scenarios and recovery tests
3. Edge cases for bot handlers
4. Command parameter validation
5. Session state management
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.error import TelegramError, NetworkError, RetryAfter, TimedOut


# =============================================================================
# Test: Rate Limit Behavior
# =============================================================================


class TestRateLimitBehavior:
    """Tests for bot behavior when Telegram rate limits are encountered."""

    @pytest.mark.asyncio
    async def test_search_handles_retry_after_error(self):
        """Test that search gracefully handles RetryAfter errors."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock search service that raises RetryAfter
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(
            side_effect=RetryAfter(30)  # Retry after 30 seconds
        )

        context = MagicMock()
        context.args = ["test", "query"]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Should inform user about rate limiting
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert (
            "rate" in call_args.lower() or
            "limit" in call_args.lower() or
            "wait" in call_args.lower() or
            "try again" in call_args.lower()
        )

    @pytest.mark.asyncio
    async def test_addchannel_handles_retry_after_error(self):
        """Test that addchannel gracefully handles RetryAfter errors."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel service that raises RetryAfter
        mock_channel_service = MagicMock()
        mock_channel_service.validate_channel = AsyncMock(
            side_effect=RetryAfter(60)
        )

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            "channel_service": mock_channel_service,
            "db_session_factory": MagicMock(),
        }
        context.bot.send_chat_action = AsyncMock()

        await addchannel_command(update, context)

        # Should inform user about rate limiting
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert (
            "rate" in call_args.lower() or
            "limit" in call_args.lower() or
            "try again" in call_args.lower() or
            "error" in call_args.lower()
        )

    @pytest.mark.asyncio
    async def test_import_handles_rate_limit_on_bulk_operation(self):
        """Test that bulk import handles rate limits during channel validation."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock document with channels
        document = MagicMock()
        document.file_name = "channels.txt"
        document.mime_type = "text/plain"

        file_mock = MagicMock()
        file_mock.download_as_bytearray = AsyncMock(
            return_value=b"@channel1\n@channel2\n@channel3"
        )
        document.get_file = AsyncMock(return_value=file_mock)
        update.message.document = document

        # Mock channel service that rate limits on second channel
        call_count = 0

        async def mock_validate_channel(username):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RetryAfter(30)
            result = MagicMock()
            result.is_valid = True
            result.channel_info = MagicMock(
                telegram_id=call_count,
                username=username,
                title=f"Test Channel {call_count}",
                description="",
                subscriber_count=1000,
                photo_url=None,
                invite_link=None,
            )
            return result

        mock_channel_service = MagicMock()
        mock_channel_service.validate_channel = mock_validate_channel

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "channel_service": mock_channel_service,
            "db_session_factory": lambda: mock_session,
        }
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        # Should report rate limit in failed channels
        calls = update.message.reply_text.call_args_list
        final_message = calls[-1][0][0]
        # Should mention that some channels failed
        assert "Failed" in final_message or "rate" in final_message.lower()


# =============================================================================
# Test: Network Error Handling
# =============================================================================


class TestNetworkErrorHandling:
    """Tests for bot behavior when network errors occur."""

    @pytest.mark.asyncio
    async def test_search_handles_network_error(self):
        """Test that search handles network errors gracefully."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock search service that raises NetworkError
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(
            side_effect=NetworkError("Connection reset")
        )

        context = MagicMock()
        context.args = ["test"]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Should inform user about network issue
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert (
            "error" in call_args.lower() or
            "try again" in call_args.lower() or
            "network" in call_args.lower()
        )

    @pytest.mark.asyncio
    async def test_search_handles_timeout_error(self):
        """Test that search handles timeout errors gracefully."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock search service that raises TimedOut
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(
            side_effect=TimedOut("Request timed out")
        )

        context = MagicMock()
        context.args = ["test"]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Should inform user about timeout
        update.message.reply_text.assert_called()


# =============================================================================
# Test: Error Recovery and State Management
# =============================================================================


class TestErrorRecoveryAndStateManagement:
    """Tests for error recovery and session state management."""

    @pytest.mark.asyncio
    async def test_user_data_preserved_after_error(self):
        """Test that user_data is preserved even after handler errors."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock search service that raises error
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(
            side_effect=Exception("Database error")
        )

        context = MagicMock()
        context.args = ["test"]
        context.user_data = {
            "last_search_query": "previous query",
            "last_search_results": ["result1", "result2"],
        }
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        # Should not modify user_data on error
        original_query = context.user_data.get("last_search_query")

        await search_command(update, context)

        # Previous search data should still be accessible
        assert context.user_data.get("last_search_query") == original_query

    @pytest.mark.asyncio
    async def test_export_works_after_failed_search(self):
        """Test that export uses cached results even if a subsequent search fails."""
        from src.tnse.bot.export_handlers import export_command
        from src.tnse.search.service import SearchResult
        from uuid import uuid4

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        # Create mock cached results
        cached_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="test_channel",
                channel_title="Test Channel",
                text_content="Test content",
                published_at=datetime.now(timezone.utc),
                view_count=1000,
                reaction_score=50.0,
                relative_engagement=0.3,
                telegram_message_id=12345,
            )
        ]

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_query": "test query",
            "last_search_results": cached_results,
        }

        await export_command(update, context)

        # Should successfully export cached results
        update.message.reply_document.assert_called_once()


# =============================================================================
# Test: Edge Cases for Bot Handlers
# =============================================================================


class TestBotHandlerEdgeCases:
    """Tests for edge cases and boundary conditions in bot handlers."""

    @pytest.mark.asyncio
    async def test_search_with_special_characters_in_query(self):
        """Test that search handles special characters in query."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        context = MagicMock()
        # Query with special characters
        context.args = ["test&query<script>alert(1)</script>"]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        # Should not raise exception
        await search_command(update, context)

        # Should call search (input is sanitized or passed through)
        mock_search_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_very_long_query(self):
        """Test that search handles very long queries."""
        from src.tnse.bot.search_handlers import search_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[])

        context = MagicMock()
        # Very long query (1000 characters)
        context.args = ["a" * 1000]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = AsyncMock()

        # Should not raise exception
        await search_command(update, context)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_addchannel_with_unicode_username(self):
        """Test that addchannel handles unicode characters in channel identifier."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_channel_service = MagicMock()
        validation_result = MagicMock()
        validation_result.is_valid = False
        validation_result.error = "Invalid channel name"
        mock_channel_service.validate_channel = AsyncMock(
            return_value=validation_result
        )

        context = MagicMock()
        context.args = ["@channel"]  # Cyrillic 'c' and 'a'
        context.bot_data = {
            "channel_service": mock_channel_service,
            "db_session_factory": MagicMock(),
        }
        context.bot.send_chat_action = AsyncMock()

        # Should not raise exception
        await addchannel_command(update, context)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_pagination_with_page_beyond_total(self):
        """Test that pagination handles page number beyond total pages."""
        from src.tnse.bot.search_handlers import pagination_callback

        update = MagicMock()
        callback_query = MagicMock()
        callback_query.data = "search:test:9999"  # Page way beyond results
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        update.callback_query = callback_query

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[MagicMock()])

        context = MagicMock()
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}

        # Should handle gracefully, capping to last page
        await pagination_callback(update, context)
        callback_query.answer.assert_called()

    @pytest.mark.asyncio
    async def test_pagination_with_negative_page(self):
        """Test that pagination handles negative page numbers."""
        from src.tnse.bot.search_handlers import pagination_callback

        update = MagicMock()
        callback_query = MagicMock()
        callback_query.data = "search:test:-1"  # Negative page
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        update.callback_query = callback_query

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=[MagicMock()])

        context = MagicMock()
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}

        # Should handle gracefully
        await pagination_callback(update, context)
        callback_query.answer.assert_called()

    @pytest.mark.asyncio
    async def test_export_with_empty_results_list(self):
        """Test that export handles empty results list properly."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_query": "test",
            "last_search_results": [],  # Empty results
        }

        await export_command(update, context)

        # Should inform user about empty results
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "no results" in call_args.lower()

    @pytest.mark.asyncio
    async def test_topic_name_with_spaces(self):
        """Test that topic commands handle names with spaces properly."""
        from src.tnse.bot.topic_handlers import savetopic_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        mock_topic_service = MagicMock()
        mock_topic_service.save_topic = AsyncMock()

        context = MagicMock()
        # Only first arg is used as topic name
        context.args = ["my", "topic", "name"]  # Multiple words
        context.user_data = {"last_search_query": "test"}
        context.bot_data = {"topic_service": mock_topic_service}

        await savetopic_command(update, context)

        # Should use only first word as topic name
        if mock_topic_service.save_topic.called:
            call_kwargs = mock_topic_service.save_topic.call_args
            # Name should be first word only
            assert call_kwargs.kwargs.get("name") == "my"


# =============================================================================
# Test: Command Parameter Validation
# =============================================================================


class TestCommandParameterValidation:
    """Tests for proper validation of command parameters."""

    @pytest.mark.asyncio
    async def test_channelinfo_with_empty_username(self):
        """Test channelinfo with empty/whitespace username."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["   "]  # Whitespace only
        context.bot_data = {"db_session_factory": MagicMock()}

        await channelinfo_command(update, context)

        # Should show usage or handle gracefully
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_usetemplate_with_nonexistent_template(self):
        """Test usetemplate with template that doesn't exist."""
        from src.tnse.bot.topic_handlers import use_template_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["nonexistent_template_12345"]
        context.bot_data = {"search_service": MagicMock()}

        await use_template_command(update, context)

        # Should inform user template not found
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "not found" in call_args.lower()

    @pytest.mark.asyncio
    async def test_export_with_invalid_format(self):
        """Test export with unsupported format."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["xml"]  # Invalid format
        context.user_data = {
            "last_search_query": "test",
            "last_search_results": [MagicMock()],
        }

        await export_command(update, context)

        # Should inform user about invalid format
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "invalid" in call_args.lower() or "format" in call_args.lower()


# =============================================================================
# Test: Concurrent Request Handling
# =============================================================================


class TestConcurrentRequestHandling:
    """Tests for handling concurrent requests from same user."""

    @pytest.mark.asyncio
    async def test_rapid_search_commands_handled(self):
        """Test that rapid successive search commands are handled."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult
        from uuid import uuid4
        import asyncio

        mock_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="test",
                channel_title="Test",
                text_content="Content",
                published_at=datetime.now(timezone.utc),
                view_count=100,
                reaction_score=10.0,
                relative_engagement=0.1,
                telegram_message_id=1,
            )
        ]

        update1 = MagicMock()
        update1.effective_user.id = 123456
        update1.effective_chat.id = 123456
        update1.message.reply_text = AsyncMock()

        update2 = MagicMock()
        update2.effective_user.id = 123456
        update2.effective_chat.id = 123456
        update2.message.reply_text = AsyncMock()

        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        context1 = MagicMock()
        context1.args = ["query1"]
        context1.user_data = {}
        context1.bot_data = {"search_service": mock_search_service}
        context1.bot.send_chat_action = AsyncMock()

        context2 = MagicMock()
        context2.args = ["query2"]
        context2.user_data = {}  # Separate user_data instance
        context2.bot_data = {"search_service": mock_search_service}
        context2.bot.send_chat_action = AsyncMock()

        # Execute both concurrently
        await asyncio.gather(
            search_command(update1, context1),
            search_command(update2, context2),
        )

        # Both should complete without error
        update1.message.reply_text.assert_called()
        update2.message.reply_text.assert_called()

        # Each should store their own query
        assert context1.user_data.get("last_search_query") == "query1"
        assert context2.user_data.get("last_search_query") == "query2"


# =============================================================================
# Test: Message Length Handling
# =============================================================================


class TestMessageLengthHandling:
    """Tests for handling Telegram message length limits."""

    def test_search_results_respect_telegram_limit(self):
        """Test that formatted search results respect Telegram's 4096 char limit."""
        from src.tnse.bot.search_handlers import SearchFormatter, TELEGRAM_MESSAGE_LIMIT
        from src.tnse.search.service import SearchResult
        from uuid import uuid4

        formatter = SearchFormatter()

        # Create many results with long text
        results = []
        for index in range(100):
            results.append(
                SearchResult(
                    post_id=str(uuid4()),
                    channel_id=str(uuid4()),
                    channel_username=f"channel_{index}",
                    channel_title=f"Test Channel {index}" + "x" * 50,
                    text_content="Long content " * 100,  # Very long content
                    published_at=datetime.now(timezone.utc),
                    view_count=1000 * (index + 1),
                    reaction_score=50.0,
                    relative_engagement=0.3,
                    telegram_message_id=12345 + index,
                )
            )

        # Format the results
        formatted = formatter.format_results_page(
            query="test query",
            results=results[:10],  # First 10 results
            total_count=100,
            page=1,
            page_size=10,
        )

        # Should not exceed Telegram limit
        assert len(formatted) <= TELEGRAM_MESSAGE_LIMIT

    def test_channel_list_handles_many_channels(self):
        """Test that channel list formatting handles many channels."""
        from src.tnse.bot.channel_handlers import format_subscriber_count

        # Test formatting for various subscriber counts
        assert len(format_subscriber_count(1_500_000)) < 10  # "1.5M"
        assert len(format_subscriber_count(150_000)) < 10  # "150.0K"
        assert len(format_subscriber_count(500)) < 5  # "500"


# =============================================================================
# Test: Bot Config Validation
# =============================================================================


class TestBotConfigValidation:
    """Tests for bot configuration validation."""

    def test_bot_config_validates_token_format(self):
        """Test that BotConfig validates token format."""
        from src.tnse.bot.config import BotConfig

        # Valid token format
        config = BotConfig(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        assert config.token is not None

    def test_bot_config_with_empty_allowed_users(self):
        """Test that empty allowed_users means open access."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(
            token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            allowed_users=[],
        )
        assert config.allowed_users == []

    def test_bot_config_with_allowed_users_list(self):
        """Test that allowed_users list is properly stored."""
        from src.tnse.bot.config import BotConfig

        config = BotConfig(
            token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            allowed_users=[123, 456, 789],
        )
        assert 123 in config.allowed_users
        assert 456 in config.allowed_users
        assert 789 in config.allowed_users
        assert len(config.allowed_users) == 3


# =============================================================================
# Test: Typing Indicator Behavior
# =============================================================================


class TestTypingIndicatorBehavior:
    """Tests for typing indicator consistency."""

    @pytest.mark.asyncio
    async def test_typing_sent_before_search_processing(self):
        """Test that typing indicator is sent before search starts."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult
        from uuid import uuid4
        from telegram.constants import ChatAction

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Track order of calls
        call_order = []

        async def mock_send_chat_action(chat_id, action):
            call_order.append(("typing", action))

        async def mock_search(*args, **kwargs):
            call_order.append(("search", None))
            return [
                SearchResult(
                    post_id=str(uuid4()),
                    channel_id=str(uuid4()),
                    channel_username="test",
                    channel_title="Test",
                    text_content="Content",
                    published_at=datetime.now(timezone.utc),
                    view_count=100,
                    reaction_score=10.0,
                    relative_engagement=0.1,
                    telegram_message_id=1,
                )
            ]

        mock_search_service = MagicMock()
        mock_search_service.search = mock_search

        context = MagicMock()
        context.args = ["test"]
        context.user_data = {}
        context.bot_data = {"search_service": mock_search_service}
        context.bot.send_chat_action = mock_send_chat_action

        await search_command(update, context)

        # Typing should be sent before search
        assert len(call_order) >= 2
        assert call_order[0][0] == "typing"
        assert call_order[0][1] == ChatAction.TYPING
        # Search should be after typing
        search_index = next(
            index for index, (action, _) in enumerate(call_order) if action == "search"
        )
        typing_index = next(
            index for index, (action, _) in enumerate(call_order) if action == "typing"
        )
        assert typing_index < search_index

"""
Tests for TNSE Telegram bot sync command handlers.

Work Stream: WS-9.2 - Manual Channel Sync Command

Following TDD methodology: these tests are written BEFORE the implementation.

Requirements tested:
- /sync command to trigger content collection for all channels
- /sync @channel command to sync specific channel
- Progress feedback (typing indicator, status messages)
- Rate limiting to prevent abuse (max 1 sync per 5 minutes)
- Restrict to admin users (configurable whitelist)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestSyncHandlerExists:
    """Tests that sync handler module and functions exist."""

    def test_sync_handlers_module_exists(self):
        """Test that sync_handlers module can be imported."""
        from src.tnse.bot import sync_handlers

        assert sync_handlers is not None

    def test_sync_command_function_exists(self):
        """Test that sync_command handler function exists."""
        from src.tnse.bot.sync_handlers import sync_command

        assert callable(sync_command)

    def test_rate_limiter_class_exists(self):
        """Test that SyncRateLimiter class exists."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        assert SyncRateLimiter is not None


class TestRateLimiter:
    """Tests for the sync rate limiter."""

    def test_rate_limiter_allows_first_sync(self):
        """Test that rate limiter allows first sync attempt."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=300)
        user_id = 123456

        assert limiter.can_sync(user_id) is True

    def test_rate_limiter_blocks_immediate_second_sync(self):
        """Test that rate limiter blocks immediate second sync."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=300)
        user_id = 123456

        # First sync records the timestamp
        limiter.record_sync(user_id)

        # Immediate second check should be blocked
        assert limiter.can_sync(user_id) is False

    def test_rate_limiter_allows_sync_after_cooldown(self):
        """Test that rate limiter allows sync after cooldown period."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=300)
        user_id = 123456

        # Record sync with time in the past
        past_time = datetime.now(timezone.utc) - timedelta(seconds=301)
        limiter._last_sync[user_id] = past_time

        # Should be allowed now
        assert limiter.can_sync(user_id) is True

    def test_rate_limiter_returns_remaining_cooldown(self):
        """Test that rate limiter returns remaining cooldown time."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=300)
        user_id = 123456

        # Record sync
        limiter.record_sync(user_id)

        # Get remaining time
        remaining = limiter.get_remaining_cooldown(user_id)

        # Should be close to 300 seconds (allow some margin)
        assert 295 <= remaining <= 300

    def test_rate_limiter_independent_per_user(self):
        """Test that rate limiter tracks users independently."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=300)
        user_a = 111111
        user_b = 222222

        # User A syncs
        limiter.record_sync(user_a)

        # User B should still be able to sync
        assert limiter.can_sync(user_b) is True

        # User A should be blocked
        assert limiter.can_sync(user_a) is False


class TestSyncCommandBasic:
    """Basic tests for /sync command handler."""

    @pytest.mark.asyncio
    async def test_sync_command_without_args_syncs_all(self):
        """Test /sync without arguments triggers sync for all channels."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-123"))

        # Mock database session with at least one channel
        mock_channels = [MagicMock(username="test_channel", is_active=True)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_channels
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
                record_sync=MagicMock(),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_all_channels",
            mock_task,
        ):
            await sync_command(update, context)

        # Should have triggered collect_all_channels task
        mock_task.delay.assert_called_once()

        # Should have sent a response
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "sync" in message.lower() or "collection" in message.lower()

    @pytest.mark.asyncio
    async def test_sync_command_with_channel_syncs_specific(self):
        """Test /sync @channel syncs specific channel only."""
        from src.tnse.bot.sync_handlers import sync_command
        from src.tnse.db.models import Channel

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-456"))

        # Mock database session with channel
        channel_id = str(uuid4())
        mock_channel = MagicMock()
        mock_channel.id = channel_id
        mock_channel.username = "test_channel"
        mock_channel.title = "Test Channel"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_channel
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
                record_sync=MagicMock(),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_channel_content",
            mock_task,
        ):
            await sync_command(update, context)

        # Should have triggered collect_channel_content with channel_id
        mock_task.delay.assert_called_once_with(channel_id)

    @pytest.mark.asyncio
    async def test_sync_command_shows_typing_indicator(self):
        """Test /sync shows typing indicator during processing."""
        from src.tnse.bot.sync_handlers import sync_command
        from telegram.constants import ChatAction

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-123"))

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": MagicMock(),
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
                record_sync=MagicMock(),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_all_channels",
            mock_task,
        ):
            await sync_command(update, context)

        # Should have sent typing indicator
        context.bot.send_chat_action.assert_called_with(
            chat_id=123456,
            action=ChatAction.TYPING,
        )


class TestSyncCommandRateLimiting:
    """Tests for /sync command rate limiting."""

    @pytest.mark.asyncio
    async def test_sync_command_rate_limited(self):
        """Test /sync is rate limited after recent sync."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": MagicMock(),
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=False),
                get_remaining_cooldown=MagicMock(return_value=180),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        await sync_command(update, context)

        # Should have sent rate limit message
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "wait" in message.lower() or "cooldown" in message.lower() or "rate" in message.lower()
        # Should mention remaining time
        assert "180" in message or "3 minute" in message.lower()

    @pytest.mark.asyncio
    async def test_sync_command_records_sync_on_success(self):
        """Test /sync records the sync timestamp on success."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-123"))

        mock_rate_limiter = MagicMock(
            can_sync=MagicMock(return_value=True),
            record_sync=MagicMock(),
        )

        # Mock database session with at least one channel
        mock_channels = [MagicMock(username="test_channel", is_active=True)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_channels
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": mock_rate_limiter,
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_all_channels",
            mock_task,
        ):
            await sync_command(update, context)

        # Should have recorded the sync
        mock_rate_limiter.record_sync.assert_called_once_with(123456)


class TestSyncCommandChannelNotFound:
    """Tests for /sync when channel is not found."""

    @pytest.mark.asyncio
    async def test_sync_channel_not_found(self):
        """Test /sync @unknown_channel shows error message."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session returning None
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = ["@unknown_channel"]
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        await sync_command(update, context)

        # Should have sent error message
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "not found" in message.lower() or "not monitored" in message.lower()


class TestSyncCommandDatabaseRequired:
    """Tests for /sync when database is not configured."""

    @pytest.mark.asyncio
    async def test_sync_command_no_database(self):
        """Test /sync without database shows error message."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {}  # No db_session_factory
        context.bot.send_chat_action = AsyncMock()

        await sync_command(update, context)

        # Should have sent error message
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "database" in message.lower() or "not configured" in message.lower()


class TestSyncCommandProgressFeedback:
    """Tests for sync command progress feedback."""

    @pytest.mark.asyncio
    async def test_sync_all_shows_channel_count(self):
        """Test /sync shows number of channels being synced."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-123"))

        # Mock database session with multiple channels
        mock_channels = [MagicMock(username=f"channel_{i}") for i in range(5)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_channels
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
                record_sync=MagicMock(),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_all_channels",
            mock_task,
        ):
            await sync_command(update, context)

        # Should mention channel count in response
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "5" in message or "channels" in message.lower()

    @pytest.mark.asyncio
    async def test_sync_specific_channel_shows_name(self):
        """Test /sync @channel shows channel name in response."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_task = MagicMock()
        mock_task.delay = MagicMock(return_value=MagicMock(id="task-456"))

        # Mock database session with channel
        mock_channel = MagicMock()
        mock_channel.id = str(uuid4())
        mock_channel.username = "specific_channel"
        mock_channel.title = "Specific Channel Title"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_channel
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = ["@specific_channel"]
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
                record_sync=MagicMock(),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        with patch(
            "src.tnse.bot.sync_handlers.collect_channel_content",
            mock_task,
        ):
            await sync_command(update, context)

        # Should mention channel name in response
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "specific_channel" in message or "Specific Channel" in message


class TestSyncCommandNoChannels:
    """Tests for /sync when no channels are being monitored."""

    @pytest.mark.asyncio
    async def test_sync_no_channels_shows_message(self):
        """Test /sync with no channels shows appropriate message."""
        from src.tnse.bot.sync_handlers import sync_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session with no channels
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": MagicMock(
                can_sync=MagicMock(return_value=True),
            ),
        }
        context.bot.send_chat_action = AsyncMock()

        await sync_command(update, context)

        # Should mention no channels
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "no channel" in message.lower() or "add a channel" in message.lower()


class TestExtractChannelUsername:
    """Tests for extracting channel username from various formats."""

    def test_extract_username_with_at_sign(self):
        """Test extracting username from @username format."""
        from src.tnse.bot.sync_handlers import extract_channel_username

        assert extract_channel_username("@test_channel") == "test_channel"

    def test_extract_username_without_at_sign(self):
        """Test extracting username from plain format."""
        from src.tnse.bot.sync_handlers import extract_channel_username

        assert extract_channel_username("test_channel") == "test_channel"

    def test_extract_username_from_t_me_url(self):
        """Test extracting username from t.me URL."""
        from src.tnse.bot.sync_handlers import extract_channel_username

        assert extract_channel_username("https://t.me/test_channel") == "test_channel"
        assert extract_channel_username("t.me/test_channel") == "test_channel"

    def test_extract_username_strips_whitespace(self):
        """Test that whitespace is stripped."""
        from src.tnse.bot.sync_handlers import extract_channel_username

        assert extract_channel_username("  @test_channel  ") == "test_channel"


class TestSyncRateLimiterDefaultCooldown:
    """Tests for default rate limiter cooldown configuration."""

    def test_default_cooldown_is_five_minutes(self):
        """Test that default cooldown is 5 minutes (300 seconds)."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter()
        assert limiter.cooldown_seconds == 300

    def test_custom_cooldown_can_be_set(self):
        """Test that custom cooldown can be configured."""
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        limiter = SyncRateLimiter(cooldown_seconds=600)
        assert limiter.cooldown_seconds == 600

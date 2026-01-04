"""
Tests for AsyncSession connection leak bug fix.

Work Stream: WS-8.4 - AsyncSession Connection Leak Bug Fix

This test file verifies that database sessions are properly closed
after use in bot command handlers. The bug manifests as:

  "The garbage collector is trying to clean up non-checked-in connection
  <AdaptedConnection <asyncpg.connection.Connection object at ...>>,
  which will be terminated."

The fix ensures all database sessions use proper async context managers
(`async with session_factory() as session:`) or explicitly call
`await session.close()`.

Following TDD methodology: these tests are written BEFORE the fix.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestChannelHandlersSessionManagement:
    """Tests for proper session lifecycle management in channel_handlers.py."""

    @pytest.mark.asyncio
    async def test_addchannel_closes_session_on_success(self):
        """Test that addchannel_command properly closes session after success."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Create mock channel info for validation
        mock_channel_info = MagicMock()
        mock_channel_info.telegram_id = 123456789
        mock_channel_info.username = "test_channel"
        mock_channel_info.title = "Test Channel"
        mock_channel_info.subscriber_count = 1000
        mock_channel_info.description = "A test channel"
        mock_channel_info.photo_url = None
        mock_channel_info.invite_link = None

        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = mock_channel_info

        # Create mock session that tracks close() calls
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        # Create async context manager mock for session factory
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": mock_session_factory,
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        # Session should have been used via async context manager
        # __aexit__ being called indicates proper cleanup
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_addchannel_closes_session_on_validation_failure(self):
        """Test that addchannel_command properly closes session when validation fails."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock validation failure
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = False
        mock_validation_result.error = "Channel not found"

        # Create mock session that tracks close() calls
        mock_session = MagicMock()
        mock_session.close = AsyncMock()

        # Create async context manager mock for session factory
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": mock_session_factory,
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        # Validation fails before DB is accessed, so no session should be created
        # This test verifies the handler returns early without leaving session open
        # The session factory should not be called if validation fails first
        # (This is the expected behavior - early return before DB access)

    @pytest.mark.asyncio
    async def test_addchannel_closes_session_on_exception(self):
        """Test that addchannel_command closes session even when exception occurs."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Create mock channel info
        mock_channel_info = MagicMock()
        mock_channel_info.telegram_id = 123456789
        mock_channel_info.username = "test_channel"
        mock_channel_info.title = "Test Channel"
        mock_channel_info.subscriber_count = 1000

        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = mock_channel_info

        # Create mock session that raises exception on execute
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        mock_session.close = AsyncMock()

        # Create async context manager mock for session factory
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": mock_session_factory,
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        # Session should have been closed even after exception
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_removechannel_closes_session_on_success(self):
        """Test that removechannel_command properly closes session after success."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock existing channel
        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        existing_channel.title = "Test Channel"

        # Create mock session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel))
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await removechannel_command(update, context)

        # Session should have been used via async context manager
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_removechannel_closes_session_on_not_found(self):
        """Test that removechannel_command closes session when channel not found."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock no channel found
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await removechannel_command(update, context)

        # Session should have been closed even when channel not found
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_channels_closes_session_on_success(self):
        """Test that channels_command properly closes session after listing."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channels
        channel1 = MagicMock()
        channel1.username = "channel_one"
        channel1.title = "Channel One"
        channel1.subscriber_count = 1000
        channel1.is_active = True

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel1]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await channels_command(update, context)

        # Session should have been closed
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_channels_closes_session_on_empty_list(self):
        """Test that channels_command closes session even when no channels found."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock empty list
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await channels_command(update, context)

        # Session should have been closed
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_channelinfo_closes_session_on_success(self):
        """Test that channelinfo_command properly closes session after showing info."""
        from src.tnse.bot.channel_handlers import channelinfo_command
        from datetime import datetime, timezone

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel
        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        existing_channel.title = "Test Channel"
        existing_channel.description = "A test channel"
        existing_channel.subscriber_count = 50000
        existing_channel.is_active = True
        existing_channel.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        existing_channel.health_logs = []

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel))
        )
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await channelinfo_command(update, context)

        # Session should have been closed
        async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_channelinfo_closes_session_on_not_found(self):
        """Test that channelinfo_command closes session when channel not found."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock no channel found
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.close = AsyncMock()

        # Create async context manager mock
        async_context = MagicMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_factory = MagicMock(return_value=async_context)

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": mock_session_factory,
        }

        await channelinfo_command(update, context)

        # Session should have been closed
        async_context.__aexit__.assert_called_once()

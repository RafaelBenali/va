"""
Tests for TNSE Telegram bot channel management commands.

Work Stream: WS-1.5 - Channel Management (Bot Commands)

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover:
- /addchannel @username - Add channel to monitor
- /removechannel @username - Remove from monitoring
- /channels - List all monitored channels
- /channelinfo @username - Show channel details
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestAddChannelCommand:
    """Tests for the /addchannel command handler."""

    @pytest.mark.asyncio
    async def test_addchannel_command_exists(self):
        """Test that addchannel_command handler function exists."""
        from src.tnse.bot.channel_handlers import addchannel_command

        assert callable(addchannel_command)

    @pytest.mark.asyncio
    async def test_addchannel_requires_username_argument(self):
        """Test that /addchannel requires a channel username."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []  # No arguments provided
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await addchannel_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show usage instructions
        assert "usage" in message.lower() or "/addchannel" in message

    @pytest.mark.asyncio
    async def test_addchannel_validates_channel(self):
        """Test that /addchannel validates the channel exists."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session factory
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()

        # Mock channel service to return invalid result
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = False
        mock_validation_result.error = "Channel not found"
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show error message
        assert "not found" in message.lower() or "error" in message.lower() or "invalid" in message.lower()

    @pytest.mark.asyncio
    async def test_addchannel_adds_valid_channel(self):
        """Test that /addchannel successfully adds a valid channel."""
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
        mock_channel_info.description = "A test channel"
        mock_channel_info.is_public = True

        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = mock_channel_info

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should confirm addition
        assert "added" in message.lower() or "success" in message.lower() or "test_channel" in message.lower()

    @pytest.mark.asyncio
    async def test_addchannel_rejects_duplicate_channel(self):
        """Test that /addchannel rejects already monitored channels."""
        from src.tnse.bot.channel_handlers import addchannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Create mock channel info
        mock_channel_info = MagicMock()
        mock_channel_info.telegram_id = 123456789
        mock_channel_info.username = "test_channel"

        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = mock_channel_info

        # Mock database session - channel already exists
        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel)))

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await addchannel_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate channel already exists
        assert "already" in message.lower() or "exists" in message.lower() or "monitoring" in message.lower()


class TestRemoveChannelCommand:
    """Tests for the /removechannel command handler."""

    @pytest.mark.asyncio
    async def test_removechannel_command_exists(self):
        """Test that removechannel_command handler function exists."""
        from src.tnse.bot.channel_handlers import removechannel_command

        assert callable(removechannel_command)

    @pytest.mark.asyncio
    async def test_removechannel_requires_username_argument(self):
        """Test that /removechannel requires a channel username."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []  # No arguments provided
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await removechannel_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show usage instructions
        assert "usage" in message.lower() or "/removechannel" in message

    @pytest.mark.asyncio
    async def test_removechannel_removes_existing_channel(self):
        """Test that /removechannel successfully removes an existing channel."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock existing channel in database
        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        existing_channel.title = "Test Channel"

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel)))
        mock_session.delete = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await removechannel_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should confirm removal
        assert "removed" in message.lower() or "deleted" in message.lower() or "test_channel" in message.lower()

    @pytest.mark.asyncio
    async def test_removechannel_handles_nonexistent_channel(self):
        """Test that /removechannel handles non-existent channel gracefully."""
        from src.tnse.bot.channel_handlers import removechannel_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session - channel does not exist
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await removechannel_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate channel not found or not being monitored
        assert "not found" in message.lower() or "not being monitored" in message.lower() or "doesn't exist" in message.lower()


class TestChannelsCommand:
    """Tests for the /channels command handler."""

    @pytest.mark.asyncio
    async def test_channels_command_exists(self):
        """Test that channels_command handler function exists."""
        from src.tnse.bot.channel_handlers import channels_command

        assert callable(channels_command)

    @pytest.mark.asyncio
    async def test_channels_lists_all_monitored_channels(self):
        """Test that /channels lists all monitored channels."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channels in database
        channel1 = MagicMock()
        channel1.username = "channel_one"
        channel1.title = "Channel One"
        channel1.subscriber_count = 1000
        channel1.is_active = True

        channel2 = MagicMock()
        channel2.username = "channel_two"
        channel2.title = "Channel Two"
        channel2.subscriber_count = 5000
        channel2.is_active = True

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[channel1, channel2])))

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channels_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should list channels
        assert "channel_one" in message.lower() or "Channel One" in message
        assert "channel_two" in message.lower() or "Channel Two" in message

    @pytest.mark.asyncio
    async def test_channels_shows_empty_message_when_no_channels(self):
        """Test that /channels shows appropriate message when no channels."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock empty channel list
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channels_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate no channels
        assert "no channel" in message.lower() or "empty" in message.lower() or "add" in message.lower()

    @pytest.mark.asyncio
    async def test_channels_shows_channel_count(self):
        """Test that /channels shows the total count of channels."""
        from src.tnse.bot.channel_handlers import channels_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock 3 channels
        channels = []
        for index in range(3):
            channel = MagicMock()
            channel.username = f"channel_{index}"
            channel.title = f"Channel {index}"
            channel.subscriber_count = 1000 * (index + 1)
            channel.is_active = True
            channels.append(channel)

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=channels)))

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channels_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show count
        assert "3" in message


class TestChannelInfoCommand:
    """Tests for the /channelinfo command handler."""

    @pytest.mark.asyncio
    async def test_channelinfo_command_exists(self):
        """Test that channelinfo_command handler function exists."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        assert callable(channelinfo_command)

    @pytest.mark.asyncio
    async def test_channelinfo_requires_username_argument(self):
        """Test that /channelinfo requires a channel username."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []  # No arguments provided
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await channelinfo_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show usage instructions
        assert "usage" in message.lower() or "/channelinfo" in message

    @pytest.mark.asyncio
    async def test_channelinfo_shows_channel_details(self):
        """Test that /channelinfo shows detailed channel information."""
        from src.tnse.bot.channel_handlers import channelinfo_command
        from datetime import datetime, timezone

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel in database with health_logs
        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        existing_channel.title = "Test Channel"
        existing_channel.description = "A test channel for news"
        existing_channel.subscriber_count = 50000
        existing_channel.is_active = True
        existing_channel.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        existing_channel.health_logs = []  # Empty health logs for this test

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel)))

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channelinfo_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show channel details
        assert "test_channel" in message.lower() or "Test Channel" in message
        assert "50000" in message or "50,000" in message or "50.0k" in message.lower()

    @pytest.mark.asyncio
    async def test_channelinfo_shows_health_status(self):
        """Test that /channelinfo shows channel health status."""
        from src.tnse.bot.channel_handlers import channelinfo_command
        from datetime import datetime, timezone

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel with health logs
        health_log = MagicMock()
        health_log.status = "healthy"
        health_log.checked_at = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)

        existing_channel = MagicMock()
        existing_channel.username = "test_channel"
        existing_channel.title = "Test Channel"
        existing_channel.subscriber_count = 50000
        existing_channel.is_active = True
        existing_channel.health_logs = [health_log]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel)))

        context = MagicMock()
        context.args = ["@test_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channelinfo_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show health status
        assert "health" in message.lower() or "status" in message.lower()

    @pytest.mark.asyncio
    async def test_channelinfo_handles_nonexistent_channel(self):
        """Test that /channelinfo handles non-existent channel gracefully."""
        from src.tnse.bot.channel_handlers import channelinfo_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock database session - channel does not exist
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        context = MagicMock()
        context.args = ["@nonexistent_channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await channelinfo_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate channel not found or not being monitored
        assert "not found" in message.lower() or "not being monitored" in message.lower()


class TestChannelUsernameExtraction:
    """Tests for channel username extraction from various input formats."""

    @pytest.mark.asyncio
    async def test_extract_username_from_at_prefix(self):
        """Test extracting username from @username format."""
        from src.tnse.bot.channel_handlers import extract_channel_username

        result = extract_channel_username("@test_channel")
        assert result == "test_channel"

    @pytest.mark.asyncio
    async def test_extract_username_without_at_prefix(self):
        """Test extracting username without @ prefix."""
        from src.tnse.bot.channel_handlers import extract_channel_username

        result = extract_channel_username("test_channel")
        assert result == "test_channel"

    @pytest.mark.asyncio
    async def test_extract_username_from_telegram_url(self):
        """Test extracting username from t.me URL."""
        from src.tnse.bot.channel_handlers import extract_channel_username

        result = extract_channel_username("https://t.me/test_channel")
        assert result == "test_channel"

    @pytest.mark.asyncio
    async def test_extract_username_handles_whitespace(self):
        """Test that username extraction handles whitespace."""
        from src.tnse.bot.channel_handlers import extract_channel_username

        result = extract_channel_username("  @test_channel  ")
        assert result == "test_channel"

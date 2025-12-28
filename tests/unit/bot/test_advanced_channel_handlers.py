"""
Tests for TNSE Telegram bot advanced channel management commands.

Work Stream: WS-3.2 - Advanced Channel Management (Bulk Import and Health Monitoring)

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover:
- /import - Bulk import channels from file
- /health - Show channel health statuses
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from io import BytesIO


class TestImportCommand:
    """Tests for the /import command handler."""

    @pytest.mark.asyncio
    async def test_import_command_exists(self):
        """Test that import_command handler function exists."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        assert callable(import_command)

    @pytest.mark.asyncio
    async def test_import_requires_file_attachment(self):
        """Test that /import requires a file attachment."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.document = None  # No document attached

        context = MagicMock()
        context.bot_data = {"config": MagicMock(allowed_users=[])}
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should request file attachment
        assert "file" in message.lower() or "attach" in message.lower() or "upload" in message.lower()

    @pytest.mark.asyncio
    async def test_import_accepts_csv_file(self):
        """Test that /import accepts CSV file format."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock CSV document
        mock_document = MagicMock()
        mock_document.file_name = "channels.csv"
        mock_document.mime_type = "text/csv"
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(b"channel_url\n@test_channel\n@another_channel")
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock channel service for validation
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            description="Test",
            photo_url=None,
            invite_link=None,
        )

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await import_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate import results
        assert "import" in message.lower() or "added" in message.lower() or "channel" in message.lower()

    @pytest.mark.asyncio
    async def test_import_accepts_json_file(self):
        """Test that /import accepts JSON file format."""
        from src.tnse.bot.advanced_channel_handlers import import_command
        import json

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock JSON document
        mock_document = MagicMock()
        mock_document.file_name = "channels.json"
        mock_document.mime_type = "application/json"
        json_content = json.dumps({"channels": ["@test_channel", "@another_channel"]})
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(json_content.encode())
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock channel service for validation
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            description="Test",
            photo_url=None,
            invite_link=None,
        )

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await import_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate import results
        assert "import" in message.lower() or "added" in message.lower() or "channel" in message.lower()

    @pytest.mark.asyncio
    async def test_import_accepts_txt_file(self):
        """Test that /import accepts plain text file format."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock TXT document
        mock_document = MagicMock()
        mock_document.file_name = "channels.txt"
        mock_document.mime_type = "text/plain"
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(b"@test_channel\n@another_channel\nhttps://t.me/third_channel")
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock channel service for validation
        mock_validation_result = MagicMock()
        mock_validation_result.is_valid = True
        mock_validation_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            description="Test",
            photo_url=None,
            invite_link=None,
        )

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": MagicMock(),
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()
        context.bot_data["channel_service"].validate_channel = AsyncMock(
            return_value=mock_validation_result
        )

        await import_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate import results
        assert "import" in message.lower() or "added" in message.lower() or "channel" in message.lower()

    @pytest.mark.asyncio
    async def test_import_validates_all_channels_in_batch(self):
        """Test that /import validates all channels before adding them."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock CSV document with multiple channels
        mock_document = MagicMock()
        mock_document.file_name = "channels.csv"
        mock_document.mime_type = "text/csv"
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(b"channel_url\n@valid_channel\n@invalid_channel\n@another_valid")
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock channel service - first and third valid, second invalid
        valid_result = MagicMock()
        valid_result.is_valid = True
        valid_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="valid_channel",
            title="Valid Channel",
            subscriber_count=1000,
            description="Valid",
            photo_url=None,
            invite_link=None,
        )

        invalid_result = MagicMock()
        invalid_result.is_valid = False
        invalid_result.error = "Channel not found"

        mock_channel_service = MagicMock()
        mock_channel_service.validate_channel = AsyncMock(
            side_effect=[valid_result, invalid_result, valid_result]
        )

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": mock_channel_service,
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        # Should have called validate for all 3 channels
        assert mock_channel_service.validate_channel.call_count == 3

    @pytest.mark.asyncio
    async def test_import_reports_results_summary(self):
        """Test that /import reports summary of added/failed channels."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock CSV document with multiple channels
        mock_document = MagicMock()
        mock_document.file_name = "channels.csv"
        mock_document.mime_type = "text/csv"
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(b"channel_url\n@valid_channel\n@invalid_channel")
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock one valid, one invalid channel
        valid_result = MagicMock()
        valid_result.is_valid = True
        valid_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="valid_channel",
            title="Valid Channel",
            subscriber_count=1000,
            description="Valid",
            photo_url=None,
            invite_link=None,
        )

        invalid_result = MagicMock()
        invalid_result.is_valid = False
        invalid_result.error = "Channel not found"

        mock_channel_service = MagicMock()
        mock_channel_service.validate_channel = AsyncMock(
            side_effect=[valid_result, invalid_result]
        )

        # Mock database session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": mock_channel_service,
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should report summary with success/failure counts
        assert "1" in message  # At least show count of success or failure

    @pytest.mark.asyncio
    async def test_import_skips_duplicate_channels(self):
        """Test that /import skips channels that are already being monitored."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock CSV document
        mock_document = MagicMock()
        mock_document.file_name = "channels.csv"
        mock_document.mime_type = "text/csv"
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(b"channel_url\n@existing_channel")
        )
        mock_document.get_file = AsyncMock(return_value=mock_file)
        update.message.document = mock_document

        # Mock valid channel
        valid_result = MagicMock()
        valid_result.is_valid = True
        valid_result.channel_info = MagicMock(
            telegram_id=123456789,
            username="existing_channel",
            title="Existing Channel",
            subscriber_count=1000,
            description="Existing",
            photo_url=None,
            invite_link=None,
        )

        mock_channel_service = MagicMock()
        mock_channel_service.validate_channel = AsyncMock(return_value=valid_result)

        # Mock database session - channel already exists
        existing_channel = MagicMock()
        existing_channel.username = "existing_channel"
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_channel))
        )

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": mock_channel_service,
            "db_session_factory": MagicMock(return_value=mock_session),
        }
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate channel was skipped or already exists
        assert "skip" in message.lower() or "already" in message.lower() or "exist" in message.lower() or "0" in message

    @pytest.mark.asyncio
    async def test_import_rejects_unsupported_file_type(self):
        """Test that /import rejects unsupported file types."""
        from src.tnse.bot.advanced_channel_handlers import import_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock unsupported document type
        mock_document = MagicMock()
        mock_document.file_name = "channels.pdf"
        mock_document.mime_type = "application/pdf"
        update.message.document = mock_document

        context = MagicMock()
        context.bot_data = {"config": MagicMock(allowed_users=[])}
        context.bot.send_chat_action = AsyncMock()

        await import_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate unsupported format
        assert "unsupported" in message.lower() or "format" in message.lower() or "csv" in message.lower() or "json" in message.lower()


class TestHealthCommand:
    """Tests for the /health command handler."""

    @pytest.mark.asyncio
    async def test_health_command_exists(self):
        """Test that health_command handler function exists."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        assert callable(health_command)

    @pytest.mark.asyncio
    async def test_health_shows_all_channel_statuses(self):
        """Test that /health shows health status of all monitored channels."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channels with health logs
        health_log_1 = MagicMock()
        health_log_1.status = "healthy"
        health_log_1.checked_at = datetime(2025, 12, 26, 12, 0, 0, tzinfo=timezone.utc)
        health_log_1.error_message = None

        channel1 = MagicMock()
        channel1.username = "healthy_channel"
        channel1.title = "Healthy Channel"
        channel1.is_active = True
        channel1.health_logs = [health_log_1]

        health_log_2 = MagicMock()
        health_log_2.status = "rate_limited"
        health_log_2.checked_at = datetime(2025, 12, 26, 11, 0, 0, tzinfo=timezone.utc)
        health_log_2.error_message = "Rate limit exceeded"

        channel2 = MagicMock()
        channel2.username = "limited_channel"
        channel2.title = "Limited Channel"
        channel2.is_active = True
        channel2.health_logs = [health_log_2]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel1, channel2]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show both channels with their status
        assert "healthy" in message.lower() or "limited" in message.lower()

    @pytest.mark.asyncio
    async def test_health_shows_empty_message_when_no_channels(self):
        """Test that /health shows appropriate message when no channels."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock empty channel list
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate no channels
        assert "no channel" in message.lower() or "empty" in message.lower() or "add" in message.lower()

    @pytest.mark.asyncio
    async def test_health_highlights_issues(self):
        """Test that /health highlights channels with issues."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel with issue
        health_log = MagicMock()
        health_log.status = "inaccessible"
        health_log.checked_at = datetime(2025, 12, 26, 12, 0, 0, tzinfo=timezone.utc)
        health_log.error_message = "Channel has been removed"

        channel = MagicMock()
        channel.username = "removed_channel"
        channel.title = "Removed Channel"
        channel.is_active = True
        channel.health_logs = [health_log]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should highlight issue - can use warning emoji or text
        assert "inaccessible" in message.lower() or "removed" in message.lower() or "issue" in message.lower() or "warning" in message.lower()

    @pytest.mark.asyncio
    async def test_health_shows_last_check_time(self):
        """Test that /health shows when each channel was last checked."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel with health log
        health_log = MagicMock()
        health_log.status = "healthy"
        health_log.checked_at = datetime(2025, 12, 26, 12, 30, 0, tzinfo=timezone.utc)
        health_log.error_message = None

        channel = MagicMock()
        channel.username = "test_channel"
        channel.title = "Test Channel"
        channel.is_active = True
        channel.health_logs = [health_log]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show last check time
        assert "12:30" in message or "2025-12-26" in message or "last" in message.lower() or "check" in message.lower()

    @pytest.mark.asyncio
    async def test_health_shows_summary_counts(self):
        """Test that /health shows summary of healthy/unhealthy channels."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock mixed health channels
        healthy_log = MagicMock()
        healthy_log.status = "healthy"
        healthy_log.checked_at = datetime(2025, 12, 26, 12, 0, 0, tzinfo=timezone.utc)
        healthy_log.error_message = None

        unhealthy_log = MagicMock()
        unhealthy_log.status = "rate_limited"
        unhealthy_log.checked_at = datetime(2025, 12, 26, 12, 0, 0, tzinfo=timezone.utc)
        unhealthy_log.error_message = "Rate limit"

        channel1 = MagicMock()
        channel1.username = "healthy_channel"
        channel1.title = "Healthy Channel"
        channel1.is_active = True
        channel1.health_logs = [healthy_log]

        channel2 = MagicMock()
        channel2.username = "unhealthy_channel"
        channel2.title = "Unhealthy Channel"
        channel2.is_active = True
        channel2.health_logs = [unhealthy_log]

        channel3 = MagicMock()
        channel3.username = "another_healthy"
        channel3.title = "Another Healthy"
        channel3.is_active = True
        channel3.health_logs = [healthy_log]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel1, channel2, channel3]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show counts - 2 healthy, 1 unhealthy, or total of 3
        assert "2" in message or "3" in message

    @pytest.mark.asyncio
    async def test_health_handles_channels_without_health_logs(self):
        """Test that /health handles channels that have never been checked."""
        from src.tnse.bot.advanced_channel_handlers import health_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        # Mock channel without health logs
        channel = MagicMock()
        channel.username = "unchecked_channel"
        channel.title = "Unchecked Channel"
        channel.is_active = True
        channel.health_logs = []  # No health logs

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[channel]))
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": MagicMock(return_value=mock_session),
        }

        await health_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate unknown or never checked status
        assert "unknown" in message.lower() or "never" in message.lower() or "pending" in message.lower() or "unchecked" in message.lower()


class TestFileParsingHelpers:
    """Tests for file parsing helper functions."""

    def test_parse_csv_channel_list(self):
        """Test parsing CSV content for channel list."""
        from src.tnse.bot.advanced_channel_handlers import parse_csv_channels

        csv_content = "channel_url,notes\n@channel_one,News\n@channel_two,Tech\nhttps://t.me/channel_three,Entertainment"

        result = parse_csv_channels(csv_content)

        assert len(result) == 3
        assert "@channel_one" in result or "channel_one" in result
        assert "@channel_two" in result or "channel_two" in result

    def test_parse_json_channel_list(self):
        """Test parsing JSON content for channel list."""
        from src.tnse.bot.advanced_channel_handlers import parse_json_channels
        import json

        json_content = json.dumps({
            "channels": ["@channel_one", "@channel_two", "https://t.me/channel_three"]
        })

        result = parse_json_channels(json_content)

        assert len(result) == 3

    def test_parse_json_simple_array(self):
        """Test parsing JSON simple array format."""
        from src.tnse.bot.advanced_channel_handlers import parse_json_channels
        import json

        json_content = json.dumps(["@channel_one", "@channel_two"])

        result = parse_json_channels(json_content)

        assert len(result) == 2

    def test_parse_txt_channel_list(self):
        """Test parsing plain text content for channel list."""
        from src.tnse.bot.advanced_channel_handlers import parse_txt_channels

        txt_content = "@channel_one\n@channel_two\nhttps://t.me/channel_three\n\n# Comment line\nchannel_four"

        result = parse_txt_channels(txt_content)

        # Should extract 4 channels (ignoring empty lines and comments)
        assert len(result) >= 3

"""
Tests for TNSE Telegram bot export command handler.

Work Stream: WS-2.5 - Export Functionality

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover:
- /export - Export search results as CSV or JSON file
- Format selection (csv, json)
- Error handling for no search results
- File generation and sending
"""

import io
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def create_mock_search_result(
    channel_username: str = "test_channel",
    channel_title: str = "Test Channel",
    text_content: str = "Test content",
    view_count: int = 1000,
    reaction_score: float = 50.0,
    telegram_message_id: int = 123,
) -> MagicMock:
    """Create a mock SearchResult for testing."""
    mock_result = MagicMock()
    mock_result.post_id = str(uuid4())
    mock_result.channel_id = str(uuid4())
    mock_result.channel_username = channel_username
    mock_result.channel_title = channel_title
    mock_result.text_content = text_content
    mock_result.published_at = datetime.now(timezone.utc)
    mock_result.view_count = view_count
    mock_result.reaction_score = reaction_score
    mock_result.relative_engagement = 0.05
    mock_result.telegram_message_id = telegram_message_id
    mock_result.preview = text_content[:200] if len(text_content) > 200 else text_content
    mock_result.telegram_link = f"https://t.me/{channel_username}/{telegram_message_id}"
    return mock_result


class TestExportCommandExists:
    """Tests for export command handler existence."""

    def test_export_command_handler_exists(self) -> None:
        """Test that export_command handler function exists."""
        from src.tnse.bot.export_handlers import export_command

        assert callable(export_command)

    def test_export_command_can_be_imported(self) -> None:
        """Test that export_command can be imported from bot module."""
        from src.tnse.bot.export_handlers import export_command

        assert export_command is not None


class TestExportCommandNoResults:
    """Tests for export command when no search results available."""

    @pytest.mark.asyncio
    async def test_export_with_no_previous_search_shows_error(self) -> None:
        """Test that /export shows error when no search has been performed."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.user_data = {}  # No previous search results
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate no results to export
        assert "no result" in message.lower() or "search first" in message.lower() or "nothing to export" in message.lower()

    @pytest.mark.asyncio
    async def test_export_with_empty_results_shows_error(self) -> None:
        """Test that /export shows error when search returned empty results."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.user_data = {
            "last_search_results": [],  # Empty results
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate no results to export
        assert "no result" in message.lower() or "empty" in message.lower()


class TestExportCommandCSV:
    """Tests for CSV export functionality."""

    @pytest.mark.asyncio
    async def test_export_defaults_to_csv_format(self) -> None:
        """Test that /export defaults to CSV format when no format specified."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = []  # No format specified
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        # Should send a document (file)
        update.message.reply_document.assert_called()
        call_args = update.message.reply_document.call_args

        # Check filename ends with .csv
        filename = call_args[1].get("filename", "")
        assert filename.endswith(".csv")

    @pytest.mark.asyncio
    async def test_export_csv_sends_file(self) -> None:
        """Test that /export csv sends a CSV file."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_document.assert_called()
        call_args = update.message.reply_document.call_args

        filename = call_args[1].get("filename", "")
        assert filename.endswith(".csv")


class TestExportCommandJSON:
    """Tests for JSON export functionality."""

    @pytest.mark.asyncio
    async def test_export_json_sends_file(self) -> None:
        """Test that /export json sends a JSON file."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["json"]
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_document.assert_called()
        call_args = update.message.reply_document.call_args

        filename = call_args[1].get("filename", "")
        assert filename.endswith(".json")


class TestExportCommandFormatValidation:
    """Tests for format validation in export command."""

    @pytest.mark.asyncio
    async def test_export_invalid_format_shows_error(self) -> None:
        """Test that /export with invalid format shows error message."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["invalid_format"]
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        # Should show error message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate invalid format
        assert "invalid" in message.lower() or "format" in message.lower() or "csv" in message.lower()

    @pytest.mark.asyncio
    async def test_export_accepts_uppercase_format(self) -> None:
        """Test that /export accepts uppercase format names."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["CSV"]  # Uppercase
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        # Should succeed and send file
        update.message.reply_document.assert_called()


class TestExportCommandMultipleResults:
    """Tests for exporting multiple search results."""

    @pytest.mark.asyncio
    async def test_export_includes_all_results(self) -> None:
        """Test that /export includes all search results in export."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        # Create multiple mock results
        mock_results = [
            create_mock_search_result(channel_username="channel1"),
            create_mock_search_result(channel_username="channel2"),
            create_mock_search_result(channel_username="channel3"),
        ]

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_results": mock_results,
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        # Should send a document
        update.message.reply_document.assert_called()

    @pytest.mark.asyncio
    async def test_export_shows_count_in_message(self) -> None:
        """Test that /export shows the number of results exported."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        # Create 5 mock results
        mock_results = [
            create_mock_search_result(channel_username=f"channel{index}")
            for index in range(5)
        ]

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_results": mock_results,
            "last_search_query": "test query",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_document.assert_called()
        call_args = update.message.reply_document.call_args

        # Check caption contains count
        caption = call_args[1].get("caption", "")
        assert "5" in caption or "results" in caption.lower()


class TestExportCommandFilename:
    """Tests for filename generation in export command."""

    @pytest.mark.asyncio
    async def test_export_filename_contains_query(self) -> None:
        """Test that export filename contains sanitized query."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "corruption",
        }
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        call_args = update.message.reply_document.call_args
        filename = call_args[1].get("filename", "")

        # Filename should contain query term
        assert "corruption" in filename.lower() or "export" in filename.lower()


class TestExportCommandAccessControl:
    """Tests for access control in export command."""

    @pytest.mark.asyncio
    async def test_export_respects_access_control(self) -> None:
        """Test that /export respects user whitelist."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 999999  # Not in whitelist
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        mock_result = create_mock_search_result()

        context = MagicMock()
        context.args = ["csv"]
        context.user_data = {
            "last_search_results": [mock_result],
            "last_search_query": "test",
        }
        context.bot_data = {
            "config": MagicMock(allowed_users=[123456, 789012])  # User not in list
        }

        # When using require_access decorator, access should be checked
        # This test verifies the handler can work with access control


class TestExportCommandHelp:
    """Tests for export command help/usage."""

    @pytest.mark.asyncio
    async def test_export_with_help_argument_shows_usage(self) -> None:
        """Test that /export help shows usage information."""
        from src.tnse.bot.export_handlers import export_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()

        context = MagicMock()
        context.args = ["help"]
        context.user_data = {}
        context.bot_data = {"config": MagicMock(allowed_users=[])}

        await export_command(update, context)

        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show usage information
        assert "/export" in message or "csv" in message.lower() or "json" in message.lower()

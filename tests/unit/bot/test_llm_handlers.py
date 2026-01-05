"""
Tests for TNSE Telegram bot LLM command handlers (WS-5.6).

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover:
- /mode command (show/switch LLM modes)
- /enrich command (trigger manual enrichment)
- /stats llm command (show LLM usage statistics)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestModeCommandExists:
    """Tests for the /mode command handler existence and basic functionality."""

    @pytest.mark.asyncio
    async def test_mode_command_handler_exists(self):
        """Test that mode_command handler function exists."""
        from src.tnse.bot.llm_handlers import mode_command

        assert callable(mode_command)

    @pytest.mark.asyncio
    async def test_mode_command_shows_current_mode_when_no_args(self):
        """Test that /mode with no arguments shows current mode."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "llm_mode": "metrics",
        }

        await mode_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should mention current mode
        assert "mode" in message.lower() or "Mode" in message


class TestModeCommandSwitching:
    """Tests for /mode command mode switching functionality."""

    @pytest.mark.asyncio
    async def test_mode_command_switches_to_llm_mode(self):
        """Test that /mode llm switches to LLM mode."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["llm"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "llm_mode": "metrics",
        }

        await mode_command(update, context)

        # Mode should be changed in bot_data
        assert context.bot_data["llm_mode"] == "llm"

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should confirm the switch
        assert "llm" in message.lower()

    @pytest.mark.asyncio
    async def test_mode_command_switches_to_metrics_mode(self):
        """Test that /mode metrics switches to metrics-only mode."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["metrics"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "llm_mode": "llm",
        }

        await mode_command(update, context)

        # Mode should be changed in bot_data
        assert context.bot_data["llm_mode"] == "metrics"

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should confirm the switch
        assert "metrics" in message.lower()

    @pytest.mark.asyncio
    async def test_mode_command_rejects_invalid_mode(self):
        """Test that /mode with invalid mode shows error."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["invalid_mode"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "llm_mode": "metrics",
        }

        await mode_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show error or usage info
        assert "llm" in message.lower() or "metrics" in message.lower()


class TestModeCommandDefaultMode:
    """Tests for /mode command default behavior."""

    @pytest.mark.asyncio
    async def test_mode_defaults_to_metrics_if_not_set(self):
        """Test that mode defaults to metrics if not explicitly set."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            # No llm_mode set
        }

        await mode_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should default to metrics
        assert "metrics" in message.lower()


class TestEnrichCommand:
    """Tests for the /enrich command handler."""

    @pytest.mark.asyncio
    async def test_enrich_command_handler_exists(self):
        """Test that enrich_command handler function exists."""
        from src.tnse.bot.llm_handlers import enrich_command

        assert callable(enrich_command)

    @pytest.mark.asyncio
    async def test_enrich_command_shows_usage_when_no_args(self):
        """Test that /enrich with no arguments shows usage."""
        from src.tnse.bot.llm_handlers import enrich_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
        }

        await enrich_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should show usage
        assert "/enrich" in message or "usage" in message.lower()

    @pytest.mark.asyncio
    async def test_enrich_command_accepts_channel_argument(self):
        """Test that /enrich @channel accepts a channel argument."""
        from src.tnse.bot.llm_handlers import enrich_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "channel_service": None,  # Not configured
        }
        context.bot.send_chat_action = AsyncMock()

        await enrich_command(update, context)

        # Should have attempted to process
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_enrich_command_shows_error_when_service_unavailable(self):
        """Test that /enrich shows error when LLM service not configured."""
        from src.tnse.bot.llm_handlers import enrich_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@testchannel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            # No enrichment_service configured
        }
        context.bot.send_chat_action = AsyncMock()

        await enrich_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should mention service not available or not configured
        assert "not" in message.lower() or "error" in message.lower() or "unavailable" in message.lower()


class TestStatsLLMCommand:
    """Tests for the /stats llm command handler."""

    @pytest.mark.asyncio
    async def test_stats_llm_command_handler_exists(self):
        """Test that stats_llm_command handler function exists."""
        from src.tnse.bot.llm_handlers import stats_llm_command

        assert callable(stats_llm_command)

    @pytest.mark.asyncio
    async def test_stats_llm_shows_usage_statistics(self):
        """Test that /stats llm shows LLM usage statistics."""
        from src.tnse.bot.llm_handlers import stats_llm_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
        }

        await stats_llm_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should mention statistics or usage
        assert "token" in message.lower() or "usage" in message.lower() or "statistics" in message.lower() or "stats" in message.lower()

    @pytest.mark.asyncio
    async def test_stats_llm_shows_cost_information(self):
        """Test that /stats llm shows cost information."""
        from src.tnse.bot.llm_handlers import stats_llm_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "db_session_factory": None,  # No database
        }

        await stats_llm_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should at least show some stats info
        assert len(message) > 20


class TestModeAliases:
    """Tests for command aliases."""

    @pytest.mark.asyncio
    async def test_m_alias_for_mode_exists(self):
        """Test that /m alias exists and works like /mode."""
        # This is tested via application.py registration
        # The test verifies the handler can be found
        from src.tnse.bot.llm_handlers import mode_command

        assert callable(mode_command)


class TestEnrichmentStatus:
    """Tests for enrichment status information."""

    @pytest.mark.asyncio
    async def test_mode_command_shows_enrichment_status(self):
        """Test that /mode shows enrichment status (enabled/disabled)."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "llm_mode": "llm",
            "enrichment_service": MagicMock(),  # Service available
        }

        await mode_command(update, context)

        call_args = update.message.reply_text.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("text", "")

        # Should indicate mode or status
        assert "llm" in message.lower() or "mode" in message.lower()


class TestSearchIntegration:
    """Tests for search integration with LLM features."""

    @pytest.mark.asyncio
    async def test_llm_mode_affects_search_include_enrichment(self):
        """Test that LLM mode enables enrichment in search."""
        # This tests the integration between mode and search
        # The actual search handler should check llm_mode
        from src.tnse.bot.llm_handlers import get_current_mode

        bot_data = {"llm_mode": "llm"}
        mode = get_current_mode(bot_data)
        assert mode == "llm"

    @pytest.mark.asyncio
    async def test_metrics_mode_disables_enrichment(self):
        """Test that metrics mode disables enrichment in search."""
        from src.tnse.bot.llm_handlers import get_current_mode

        bot_data = {"llm_mode": "metrics"}
        mode = get_current_mode(bot_data)
        assert mode == "metrics"


class TestLLMHandlerErrorHandling:
    """Tests for error handling in LLM handlers."""

    @pytest.mark.asyncio
    async def test_mode_command_handles_missing_config(self):
        """Test that /mode handles missing config gracefully."""
        from src.tnse.bot.llm_handlers import mode_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []
        context.bot_data = {}  # No config

        # Should not raise an exception
        await mode_command(update, context)

        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_command_handles_exception(self):
        """Test that /enrich handles exceptions gracefully."""
        from src.tnse.bot.llm_handlers import enrich_command

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["@channel"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "enrichment_service": MagicMock(side_effect=Exception("Test error")),
        }
        context.bot.send_chat_action = AsyncMock()

        # Should not raise an exception
        await enrich_command(update, context)

        # Should have sent some response
        update.message.reply_text.assert_called()


class TestValidModes:
    """Tests for valid mode values."""

    def test_valid_modes_constant_exists(self):
        """Test that VALID_MODES constant exists."""
        from src.tnse.bot.llm_handlers import VALID_MODES

        assert isinstance(VALID_MODES, (list, tuple, set))
        assert "llm" in VALID_MODES
        assert "metrics" in VALID_MODES

    def test_default_mode_constant_exists(self):
        """Test that DEFAULT_MODE constant exists."""
        from src.tnse.bot.llm_handlers import DEFAULT_MODE

        assert DEFAULT_MODE in ("llm", "metrics")

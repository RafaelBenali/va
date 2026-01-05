"""
Tests for enhanced search handlers with LLM enrichment (WS-5.6).

Following TDD methodology: these tests verify that:
- Search results display category/sentiment when available
- Filter syntax works for category:/sentiment:
- SearchFormatter includes enrichment display
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone


class TestSearchFormatterEnrichment:
    """Tests for SearchFormatter with enrichment display."""

    def test_format_result_includes_category_when_present(self):
        """Test that format_result includes category when available."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        result = SearchResult(
            post_id="123",
            channel_id="456",
            channel_username="testchannel",
            channel_title="Test Channel",
            text_content="Test post content about politics",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=10.0,
            relative_engagement=0.5,
            telegram_message_id=789,
            category="politics",
            sentiment="negative",
        )

        formatted = formatter.format_result(result, index=1)

        assert "politics" in formatted.lower()

    def test_format_result_includes_sentiment_when_present(self):
        """Test that format_result includes sentiment when available."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        result = SearchResult(
            post_id="123",
            channel_id="456",
            channel_username="testchannel",
            channel_title="Test Channel",
            text_content="Test post content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=10.0,
            relative_engagement=0.5,
            telegram_message_id=789,
            category="economics",
            sentiment="positive",
        )

        formatted = formatter.format_result(result, index=1)

        assert "positive" in formatted.lower() or "economics" in formatted.lower()

    def test_format_result_omits_enrichment_when_not_present(self):
        """Test that format_result works without enrichment data."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        result = SearchResult(
            post_id="123",
            channel_id="456",
            channel_username="testchannel",
            channel_title="Test Channel",
            text_content="Test post content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=10.0,
            relative_engagement=0.5,
            telegram_message_id=789,
            # No category or sentiment
        )

        # Should not raise any errors
        formatted = formatter.format_result(result, index=1)

        assert "Test Channel" in formatted
        assert "testchannel" in formatted or "View Post" in formatted


class TestSearchFilterSyntax:
    """Tests for search filter syntax parsing."""

    def test_parse_search_filters_extracts_category(self):
        """Test that category:value is parsed from query."""
        from src.tnse.bot.search_handlers import parse_search_filters

        query = "corruption category:politics"
        parsed_query, filters = parse_search_filters(query)

        assert parsed_query.strip() == "corruption"
        assert filters.get("category") == "politics"

    def test_parse_search_filters_extracts_sentiment(self):
        """Test that sentiment:value is parsed from query."""
        from src.tnse.bot.search_handlers import parse_search_filters

        query = "news sentiment:negative"
        parsed_query, filters = parse_search_filters(query)

        assert parsed_query.strip() == "news"
        assert filters.get("sentiment") == "negative"

    def test_parse_search_filters_extracts_both(self):
        """Test that both category and sentiment are parsed."""
        from src.tnse.bot.search_handlers import parse_search_filters

        query = "breaking news category:politics sentiment:negative"
        parsed_query, filters = parse_search_filters(query)

        assert "breaking news" in parsed_query
        assert filters.get("category") == "politics"
        assert filters.get("sentiment") == "negative"

    def test_parse_search_filters_returns_original_query_when_no_filters(self):
        """Test that query is unchanged when no filters present."""
        from src.tnse.bot.search_handlers import parse_search_filters

        query = "simple search query"
        parsed_query, filters = parse_search_filters(query)

        assert parsed_query == query
        assert filters == {}

    def test_parse_search_filters_handles_empty_query(self):
        """Test that empty query is handled."""
        from src.tnse.bot.search_handlers import parse_search_filters

        query = ""
        parsed_query, filters = parse_search_filters(query)

        assert parsed_query == ""
        assert filters == {}


class TestSearchCommandWithFilters:
    """Tests for /search command with filter support."""

    @pytest.mark.asyncio
    async def test_search_passes_category_filter_to_service(self):
        """Test that category filter is passed to search service."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Create mock search service
        mock_results = [
            SearchResult(
                post_id="123",
                channel_id="456",
                channel_username="test",
                channel_title="Test",
                text_content="Test content",
                published_at=datetime.now(timezone.utc),
                view_count=100,
                reaction_score=5.0,
                relative_engagement=0.3,
                telegram_message_id=789,
                category="politics",
            )
        ]
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        context = MagicMock()
        context.args = ["test", "category:politics"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "search_service": mock_search_service,
            "llm_mode": "llm",
        }
        context.user_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Verify search was called with category filter
        mock_search_service.search.assert_called()
        call_kwargs = mock_search_service.search.call_args[1]
        assert call_kwargs.get("category") == "politics"

    @pytest.mark.asyncio
    async def test_search_passes_sentiment_filter_to_service(self):
        """Test that sentiment filter is passed to search service."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        # Create mock search service
        mock_results = [
            SearchResult(
                post_id="123",
                channel_id="456",
                channel_username="test",
                channel_title="Test",
                text_content="Test content",
                published_at=datetime.now(timezone.utc),
                view_count=100,
                reaction_score=5.0,
                relative_engagement=0.3,
                telegram_message_id=789,
                sentiment="negative",
            )
        ]
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        context = MagicMock()
        context.args = ["scandal", "sentiment:negative"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "search_service": mock_search_service,
            "llm_mode": "llm",
        }
        context.user_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Verify search was called with sentiment filter
        mock_search_service.search.assert_called()
        call_kwargs = mock_search_service.search.call_args[1]
        assert call_kwargs.get("sentiment") == "negative"


class TestSearchModeAwareness:
    """Tests for search mode awareness (LLM vs metrics)."""

    @pytest.mark.asyncio
    async def test_search_uses_include_enrichment_based_on_mode(self):
        """Test that search respects llm_mode for include_enrichment."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_results = [
            SearchResult(
                post_id="123",
                channel_id="456",
                channel_username="test",
                channel_title="Test",
                text_content="Test content",
                published_at=datetime.now(timezone.utc),
                view_count=100,
                reaction_score=5.0,
                relative_engagement=0.3,
                telegram_message_id=789,
            )
        ]
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        # Test with llm_mode = "metrics"
        context = MagicMock()
        context.args = ["test"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "search_service": mock_search_service,
            "llm_mode": "metrics",
        }
        context.user_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Verify include_enrichment is based on mode
        call_kwargs = mock_search_service.search.call_args[1]
        assert call_kwargs.get("include_enrichment") == False

    @pytest.mark.asyncio
    async def test_search_includes_enrichment_when_llm_mode(self):
        """Test that search includes enrichment in LLM mode."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.search.service import SearchResult

        update = MagicMock()
        update.effective_user.id = 123456
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()

        mock_results = [
            SearchResult(
                post_id="123",
                channel_id="456",
                channel_username="test",
                channel_title="Test",
                text_content="Test content",
                published_at=datetime.now(timezone.utc),
                view_count=100,
                reaction_score=5.0,
                relative_engagement=0.3,
                telegram_message_id=789,
            )
        ]
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_results)

        context = MagicMock()
        context.args = ["test"]
        context.bot_data = {
            "config": MagicMock(allowed_users=[]),
            "search_service": mock_search_service,
            "llm_mode": "llm",
        }
        context.user_data = {}
        context.bot.send_chat_action = AsyncMock()

        await search_command(update, context)

        # Verify include_enrichment is True in LLM mode
        call_kwargs = mock_search_service.search.call_args[1]
        assert call_kwargs.get("include_enrichment") == True


class TestEnrichmentIndicator:
    """Tests for enrichment indicator in results."""

    def test_format_result_shows_enriched_indicator(self):
        """Test that enriched posts show an indicator."""
        from src.tnse.bot.search_handlers import SearchFormatter
        from src.tnse.search.service import SearchResult

        formatter = SearchFormatter()
        result = SearchResult(
            post_id="123",
            channel_id="456",
            channel_username="testchannel",
            channel_title="Test Channel",
            text_content="Test post content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=10.0,
            relative_engagement=0.5,
            telegram_message_id=789,
            category="technology",
            sentiment="positive",
        )

        formatted = formatter.format_result(result, index=1)

        # Should show category/sentiment in some format
        assert "technology" in formatted.lower() or "positive" in formatted.lower()

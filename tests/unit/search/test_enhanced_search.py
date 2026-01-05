"""
WS-5.5: Enhanced Search Service Tests

Unit tests for the enhanced search functionality with keyword retrieval
from post enrichments (explicit and implicit keywords).

Requirements addressed:
- Search finds posts via implicit keywords NOT in original text
- Category and sentiment filters work correctly
- Response time remains < 3 seconds
- Backward compatible - works without enrichment data
- Cache handles enrichment fields correctly

This file follows TDD methodology - tests are written first, then implementation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class MockAsyncSession:
    """Mock that supports async context manager protocol for SQLAlchemy AsyncSession."""

    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> "MockAsyncSession":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False


class TestEnhancedSearchResultFields:
    """Tests for new enrichment fields in SearchResult dataclass."""

    def test_search_result_has_category_field(self) -> None:
        """Test that SearchResult has optional category field."""
        from src.tnse.search.service import SearchResult

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            category="politics",
        )

        assert result.category == "politics"

    def test_search_result_has_sentiment_field(self) -> None:
        """Test that SearchResult has optional sentiment field."""
        from src.tnse.search.service import SearchResult

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            sentiment="positive",
        )

        assert result.sentiment == "positive"

    def test_search_result_has_explicit_keywords_field(self) -> None:
        """Test that SearchResult has optional explicit_keywords field."""
        from src.tnse.search.service import SearchResult

        keywords = ["corruption", "politics", "scandal"]
        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            explicit_keywords=keywords,
        )

        assert result.explicit_keywords == keywords

    def test_search_result_has_implicit_keywords_field(self) -> None:
        """Test that SearchResult has optional implicit_keywords field."""
        from src.tnse.search.service import SearchResult

        keywords = ["bribery", "government", "crime"]
        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            implicit_keywords=keywords,
        )

        assert result.implicit_keywords == keywords

    def test_search_result_enrichment_fields_default_to_none(self) -> None:
        """Test that enrichment fields default to None for backward compatibility."""
        from src.tnse.search.service import SearchResult

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
        )

        assert result.category is None
        assert result.sentiment is None
        assert result.explicit_keywords is None
        assert result.implicit_keywords is None

    def test_search_result_has_is_enriched_property(self) -> None:
        """Test that SearchResult has is_enriched property."""
        from src.tnse.search.service import SearchResult

        # Unenriched result
        unenriched = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
        )
        assert unenriched.is_enriched is False

        # Enriched result
        enriched = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="Test content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            category="politics",
            sentiment="negative",
        )
        assert enriched.is_enriched is True


class TestSearchFilterParameters:
    """Tests for new filter parameters in search method."""

    @pytest.mark.asyncio
    async def test_search_accepts_category_filter(self) -> None:
        """Test that search method accepts category filter parameter."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Should not raise TypeError
        await service.search("corruption", category="politics")

    @pytest.mark.asyncio
    async def test_search_accepts_sentiment_filter(self) -> None:
        """Test that search method accepts sentiment filter parameter."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Should not raise TypeError
        await service.search("news", sentiment="positive")

    @pytest.mark.asyncio
    async def test_search_accepts_include_enrichment_flag(self) -> None:
        """Test that search method accepts include_enrichment flag."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Should not raise TypeError - defaults to True
        await service.search("test", include_enrichment=True)
        await service.search("test", include_enrichment=False)

    @pytest.mark.asyncio
    async def test_search_filters_by_category(self) -> None:
        """Test that category filter actually filters results."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        # Create mock rows with different categories
        mock_row_politics = MagicMock()
        mock_row_politics.post_id = str(uuid4())
        mock_row_politics.channel_id = str(uuid4())
        mock_row_politics.channel_username = "politics_channel"
        mock_row_politics.channel_title = "Politics Channel"
        mock_row_politics.text_content = "Political news content"
        mock_row_politics.published_at = datetime.now(timezone.utc)
        mock_row_politics.view_count = 1000
        mock_row_politics.reaction_score = 50.0
        mock_row_politics.relative_engagement = 0.05
        mock_row_politics.telegram_message_id = 123
        mock_row_politics.category = "politics"
        mock_row_politics.sentiment = "neutral"
        mock_row_politics.explicit_keywords = ["news", "politics"]
        mock_row_politics.implicit_keywords = ["government", "election"]

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row_politics]
        mock_session.execute.return_value = mock_result

        results = await service.search("news", category="politics")

        # Verify the SQL query includes category filter
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        # Check that category parameter is passed
        assert "category" in params or ":category" in sql_text

    @pytest.mark.asyncio
    async def test_search_filters_by_sentiment(self) -> None:
        """Test that sentiment filter actually filters results."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("news", sentiment="negative")

        # Verify the SQL query includes sentiment filter
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]

        # Check that sentiment parameter is passed
        assert "sentiment" in params or ":sentiment" in sql_text


class TestHybridSearch:
    """Tests for hybrid search combining full-text and keyword array matching."""

    @pytest.mark.asyncio
    async def test_search_matches_explicit_keywords(self) -> None:
        """Test that search matches against explicit_keywords array."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("corruption")

        # Verify the SQL includes keyword array search
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])

        # Check for array overlap operator or keyword matching
        assert "explicit_keywords" in sql_text or "&&" in sql_text

    @pytest.mark.asyncio
    async def test_search_matches_implicit_keywords(self) -> None:
        """Test that search matches against implicit_keywords array (key RAG feature)."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("bribery")  # A term that might be implicit, not explicit

        # Verify the SQL includes implicit keyword array search
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])

        # Check for implicit keyword matching
        assert "implicit_keywords" in sql_text

    @pytest.mark.asyncio
    async def test_search_joins_post_enrichments_table(self) -> None:
        """Test that search query JOINs the post_enrichments table."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("test", include_enrichment=True)

        # Verify the SQL includes JOIN to post_enrichments
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])

        assert "post_enrichments" in sql_text
        assert "JOIN" in sql_text or "join" in sql_text.lower()

    @pytest.mark.asyncio
    async def test_search_without_enrichment_skips_join(self) -> None:
        """Test that search without enrichment flag skips the JOIN."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("test", include_enrichment=False)

        # Verify the SQL does NOT include JOIN to post_enrichments
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])

        assert "post_enrichments" not in sql_text

    @pytest.mark.asyncio
    async def test_search_returns_enriched_results(self) -> None:
        """Test that search returns results with enrichment data when available."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        # Create mock row with enrichment data
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "test_channel"
        mock_row.channel_title = "Test Channel"
        mock_row.text_content = "Content about corruption scandal"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 5000
        mock_row.reaction_score = 100.0
        mock_row.relative_engagement = 0.10
        mock_row.telegram_message_id = 456
        mock_row.category = "politics"
        mock_row.sentiment = "negative"
        mock_row.explicit_keywords = ["corruption", "scandal"]
        mock_row.implicit_keywords = ["bribery", "government", "crime"]

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        results = await service.search("corruption")

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.category == "politics"
        assert result.sentiment == "negative"
        assert result.explicit_keywords == ["corruption", "scandal"]
        assert result.implicit_keywords == ["bribery", "government", "crime"]
        assert result.is_enriched is True


class TestBackwardCompatibility:
    """Tests for backward compatibility with unenriched posts."""

    @pytest.mark.asyncio
    async def test_search_works_without_enrichment_data(self) -> None:
        """Test that search works for posts without enrichment data."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        # Create mock row WITHOUT enrichment data (NULLs)
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "old_channel"
        mock_row.channel_title = "Old Channel"
        mock_row.text_content = "Old content without enrichment"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 500
        mock_row.reaction_score = 25.0
        mock_row.relative_engagement = 0.025
        mock_row.telegram_message_id = 789
        mock_row.category = None
        mock_row.sentiment = None
        mock_row.explicit_keywords = None
        mock_row.implicit_keywords = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        results = await service.search("content")

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.category is None
        assert result.sentiment is None
        assert result.is_enriched is False

    @pytest.mark.asyncio
    async def test_search_mixes_enriched_and_unenriched(self) -> None:
        """Test that search handles mix of enriched and unenriched posts."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        # Create mock rows - one enriched, one not
        enriched_row = MagicMock()
        enriched_row.post_id = str(uuid4())
        enriched_row.channel_id = str(uuid4())
        enriched_row.channel_username = "enriched_channel"
        enriched_row.channel_title = "Enriched Channel"
        enriched_row.text_content = "Enriched news content"
        enriched_row.published_at = datetime.now(timezone.utc)
        enriched_row.view_count = 1000
        enriched_row.reaction_score = 50.0
        enriched_row.relative_engagement = 0.05
        enriched_row.telegram_message_id = 111
        enriched_row.category = "politics"
        enriched_row.sentiment = "positive"
        enriched_row.explicit_keywords = ["news"]
        enriched_row.implicit_keywords = ["media"]

        unenriched_row = MagicMock()
        unenriched_row.post_id = str(uuid4())
        unenriched_row.channel_id = str(uuid4())
        unenriched_row.channel_username = "unenriched_channel"
        unenriched_row.channel_title = "Unenriched Channel"
        unenriched_row.text_content = "Unenriched news content"
        unenriched_row.published_at = datetime.now(timezone.utc)
        unenriched_row.view_count = 800
        unenriched_row.reaction_score = 40.0
        unenriched_row.relative_engagement = 0.04
        unenriched_row.telegram_message_id = 222
        unenriched_row.category = None
        unenriched_row.sentiment = None
        unenriched_row.explicit_keywords = None
        unenriched_row.implicit_keywords = None

        mock_result = MagicMock()
        mock_result.all.return_value = [enriched_row, unenriched_row]
        mock_session.execute.return_value = mock_result

        results = await service.search("news")

        assert len(results) == 2
        assert results[0].is_enriched is True
        assert results[1].is_enriched is False


class TestEnhancedSearchCaching:
    """Tests for caching with enrichment fields."""

    @pytest.mark.asyncio
    async def test_cache_serialization_includes_enrichment(self) -> None:
        """Test that cache serialization includes enrichment fields."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss

        service = SearchService(
            session_factory=mock_session_factory,
            cache=mock_cache,
        )

        # Create mock row with enrichment
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "cached_channel"
        mock_row.channel_title = "Cached Channel"
        mock_row.text_content = "Content to cache"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 1000
        mock_row.reaction_score = 50.0
        mock_row.relative_engagement = 0.05
        mock_row.telegram_message_id = 123
        mock_row.category = "technology"
        mock_row.sentiment = "positive"
        mock_row.explicit_keywords = ["tech", "gadget"]
        mock_row.implicit_keywords = ["innovation", "startup"]

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        await service.search("tech")

        # Verify cache.set was called with enrichment data
        mock_cache.set.assert_called()
        cache_call_args = mock_cache.set.call_args
        cached_data = cache_call_args[0][1]  # Second positional arg is the data

        # Verify enrichment fields in cached data
        assert len(cached_data) == 1
        cached_item = cached_data[0]
        assert cached_item["category"] == "technology"
        assert cached_item["sentiment"] == "positive"
        assert cached_item["explicit_keywords"] == ["tech", "gadget"]
        assert cached_item["implicit_keywords"] == ["innovation", "startup"]

    @pytest.mark.asyncio
    async def test_cache_deserialization_restores_enrichment(self) -> None:
        """Test that cache deserialization restores enrichment fields."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        cached_results = [
            {
                "post_id": str(uuid4()),
                "channel_id": str(uuid4()),
                "channel_username": "cached_channel",
                "channel_title": "Cached Channel",
                "text_content": "Cached content",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.05,
                "telegram_message_id": 123,
                "category": "economics",
                "sentiment": "neutral",
                "explicit_keywords": ["economy", "market"],
                "implicit_keywords": ["finance", "trading"],
            }
        ]

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_results  # Cache hit

        service = SearchService(
            session_factory=mock_session_factory,
            cache=mock_cache,
        )

        results = await service.search("economy")

        # Should not query database
        mock_session.execute.assert_not_called()

        # Verify enrichment data restored
        assert len(results) == 1
        result = results[0]
        assert result.category == "economics"
        assert result.sentiment == "neutral"
        assert result.explicit_keywords == ["economy", "market"]
        assert result.implicit_keywords == ["finance", "trading"]
        assert result.is_enriched is True

    @pytest.mark.asyncio
    async def test_cache_key_includes_filter_params(self) -> None:
        """Test that cache key includes category and sentiment filters."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        service = SearchService(
            session_factory=mock_session_factory,
            cache=mock_cache,
        )

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Make two searches with different filters
        await service.search("test", category="politics")
        first_cache_key = mock_cache.get.call_args_list[0][0][0]

        await service.search("test", category="economics")
        second_cache_key = mock_cache.get.call_args_list[1][0][0]

        # Cache keys should be different for different filters
        assert first_cache_key != second_cache_key


class TestSearchPerformance:
    """Tests for search performance requirements."""

    @pytest.mark.asyncio
    async def test_search_query_uses_efficient_join(self) -> None:
        """Test that the search query uses LEFT JOIN for optional enrichment."""
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("test", include_enrichment=True)

        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])

        # Should use LEFT JOIN for optional enrichment data
        assert "LEFT JOIN" in sql_text or "LEFT join" in sql_text.lower()


class TestImplicitKeywordRanking:
    """Tests for ranking boost based on keyword match type."""

    @pytest.mark.asyncio
    async def test_search_result_has_match_type_indicator(self) -> None:
        """Test that SearchResult indicates how the match was found."""
        from src.tnse.search.service import SearchResult

        # Result matched via full-text
        fulltext_result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="channel1",
            channel_title="Channel 1",
            text_content="Content with keyword",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
            match_type="fulltext",
        )

        # Result matched via explicit keyword
        explicit_result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="channel2",
            channel_title="Channel 2",
            text_content="Other content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=124,
            match_type="explicit_keyword",
        )

        # Result matched via implicit keyword (semantic match)
        implicit_result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="channel3",
            channel_title="Channel 3",
            text_content="Unrelated text",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=125,
            match_type="implicit_keyword",
        )

        assert fulltext_result.match_type == "fulltext"
        assert explicit_result.match_type == "explicit_keyword"
        assert implicit_result.match_type == "implicit_keyword"

    def test_match_type_defaults_to_none(self) -> None:
        """Test that match_type defaults to None for backward compatibility."""
        from src.tnse.search.service import SearchResult

        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="channel",
            channel_title="Channel",
            text_content="Content",
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
        )

        assert result.match_type is None

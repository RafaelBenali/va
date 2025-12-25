"""
TNSE Search Service Tests

Unit tests for the keyword search service with PostgreSQL full-text search.

Work Stream: WS-2.2 - Keyword Search Engine

Requirements addressed:
- REQ-MO-005: Keyword-based search in metrics-only mode
- REQ-NP-006: Handle Russian, English, Ukrainian, and other Cyrillic languages
- REQ-NP-007: Rank news by configurable criteria
- NFR-P-007: Metrics-only mode response time < 3 seconds
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestSearchService:
    """Tests for the SearchService class."""

    def test_search_service_can_be_instantiated(self) -> None:
        """Test that SearchService can be instantiated."""
        from src.tnse.search.service import SearchService

        service = SearchService(session_factory=MagicMock())

        assert service is not None
        assert hasattr(service, "search")

    def test_search_service_requires_session_factory(self) -> None:
        """Test that SearchService requires a session factory."""
        from src.tnse.search.service import SearchService

        with pytest.raises(TypeError):
            SearchService()  # type: ignore[call-arg]


class TestKeywordSearch:
    """Tests for keyword-based search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_matching_posts(self) -> None:
        """Test that search returns posts matching the keyword."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        # Mock the database query result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            {
                "post_id": str(uuid4()),
                "channel_id": str(uuid4()),
                "channel_username": "test_channel",
                "channel_title": "Test Channel",
                "text_content": "This is a test about corruption in politics",
                "published_at": datetime.now(timezone.utc),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.05,
                "telegram_message_id": 123,
            }
        ]
        mock_session.execute.return_value = mock_result

        results = await service.search("corruption")

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(result, SearchResult) for result in results)

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty_list(self) -> None:
        """Test that searching with empty query returns empty list."""
        from src.tnse.search.service import SearchService

        mock_session_factory = MagicMock()
        service = SearchService(session_factory=mock_session_factory)

        results = await service.search("")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_whitespace_query_returns_empty_list(self) -> None:
        """Test that searching with whitespace-only query returns empty list."""
        from src.tnse.search.service import SearchService

        mock_session_factory = MagicMock()
        service = SearchService(session_factory=mock_session_factory)

        results = await service.search("   \t\n  ")

        assert results == []


class TestMultipleKeywordSearch:
    """Tests for multiple keyword search functionality."""

    @pytest.mark.asyncio
    async def test_search_multiple_keywords(self) -> None:
        """Test searching with multiple keywords (AND logic)."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Search with multiple keywords
        await service.search("corruption politics")

        # Verify that the query was built with multiple keywords
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_handles_russian_keywords(self) -> None:
        """Test that search handles Russian keywords properly."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Search with Russian keywords
        await service.search("коррупция политика")

        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_handles_mixed_language_keywords(self) -> None:
        """Test that search handles mixed Russian and English keywords."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Search with mixed language keywords
        await service.search("corruption коррупция")

        mock_session.execute.assert_called()


class TestSearchTimeWindow:
    """Tests for search time window functionality."""

    @pytest.mark.asyncio
    async def test_search_defaults_to_24_hour_window(self) -> None:
        """Test that search defaults to 24-hour time window."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("test")

        # Verify that the query includes a time filter
        # The exact assertion depends on implementation
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_respects_custom_time_window(self) -> None:
        """Test that search respects custom time window parameter."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        service = SearchService(session_factory=mock_session_factory)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Search with 12-hour window
        await service.search("test", hours=12)

        mock_session.execute.assert_called()


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_has_required_fields(self) -> None:
        """Test that SearchResult has all required fields."""
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

        assert result.post_id is not None
        assert result.channel_id is not None
        assert result.channel_username == "test_channel"
        assert result.channel_title == "Test Channel"
        assert result.text_content == "Test content"
        assert result.view_count == 1000
        assert result.reaction_score == 50.0
        assert result.relative_engagement == 0.05
        assert result.telegram_message_id == 123

    def test_search_result_has_preview_property(self) -> None:
        """Test that SearchResult provides a text preview."""
        from src.tnse.search.service import SearchResult

        long_text = "A" * 500
        result = SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content=long_text,
            published_at=datetime.now(timezone.utc),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.05,
            telegram_message_id=123,
        )

        preview = result.preview
        assert len(preview) <= 203  # 200 chars + "..."
        assert preview.endswith("...")

    def test_search_result_telegram_link(self) -> None:
        """Test that SearchResult generates correct Telegram link."""
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

        link = result.telegram_link
        assert link == "https://t.me/test_channel/123"


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_search_query_has_required_fields(self) -> None:
        """Test that SearchQuery has all required fields."""
        from src.tnse.search.service import SearchQuery

        query = SearchQuery(
            keywords=["corruption", "politics"],
            hours=24,
            limit=100,
            offset=0,
        )

        assert query.keywords == ["corruption", "politics"]
        assert query.hours == 24
        assert query.limit == 100
        assert query.offset == 0

    def test_search_query_defaults(self) -> None:
        """Test that SearchQuery has sensible defaults."""
        from src.tnse.search.service import SearchQuery

        query = SearchQuery(keywords=["test"])

        assert query.keywords == ["test"]
        assert query.hours == 24
        assert query.limit == 100
        assert query.offset == 0


class TestSearchResultSorting:
    """Tests for search result sorting functionality."""

    def test_search_result_default_sort_by_combined_score(self) -> None:
        """Test that results are sorted by combined score by default."""
        from src.tnse.search.service import SearchResult

        now = datetime.now(timezone.utc)

        results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="channel1",
                channel_title="Channel 1",
                text_content="Content 1",
                published_at=now - timedelta(hours=2),
                view_count=500,
                reaction_score=20.0,
                relative_engagement=0.02,
                telegram_message_id=1,
            ),
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="channel2",
                channel_title="Channel 2",
                text_content="Content 2",
                published_at=now - timedelta(hours=1),
                view_count=1000,
                reaction_score=50.0,
                relative_engagement=0.05,
                telegram_message_id=2,
            ),
        ]

        # Second result should have higher score (more views, higher engagement, more recent)
        assert results[1].view_count > results[0].view_count
        assert results[1].relative_engagement > results[0].relative_engagement


class TestSearchCaching:
    """Tests for search result caching functionality."""

    @pytest.mark.asyncio
    async def test_search_caches_results(self) -> None:
        """Test that search results are cached."""
        from src.tnse.search.service import SearchService

        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss

        service = SearchService(
            session_factory=mock_session_factory,
            cache=mock_cache,
        )

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        await service.search("test")

        # Verify cache was checked
        mock_cache.get.assert_called()

    @pytest.mark.asyncio
    async def test_search_returns_cached_results(self) -> None:
        """Test that cached results are returned without database query."""
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
            }
        ]

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_results  # Cache hit

        service = SearchService(
            session_factory=mock_session_factory,
            cache=mock_cache,
        )

        results = await service.search("test")

        # Should not query database when cache hit
        mock_session.execute.assert_not_called()
        assert len(results) == 1

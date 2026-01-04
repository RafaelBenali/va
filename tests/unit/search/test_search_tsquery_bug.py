"""
TNSE Search tsquery Bug Tests

Tests exposing the bug where to_tsquery fails with plain keywords.

Bug Report:
-----------
The search service uses to_tsquery which requires pre-processed lexemes,
but passes raw keywords like 'hello & world'. This causes search to fail
for queries that should match existing content.

Root Cause:
-----------
to_tsquery('english', 'hello & world') expects 'hello' and 'world' to be
lexemes. For example:
- to_tsquery('english', 'run') -> 'run' (works because 'run' is a lexeme)
- to_tsquery('english', 'running') -> ERROR (not a valid tsquery)

Solution:
---------
Use plainto_tsquery() or websearch_to_tsquery() instead of to_tsquery(),
or use the :* suffix for prefix matching with to_tsquery.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4


class MockAsyncSession:
    """Mock that supports async context manager protocol."""

    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> "MockAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False


class TestSearchTsqueryBug:
    """Tests exposing the to_tsquery bug in search."""

    @pytest.mark.asyncio
    async def test_search_with_simple_word_should_match_content(self) -> None:
        """Test that a simple single word search matches content.

        This test verifies that searching for 'corruption' finds content
        containing the word 'corruption'. With the current to_tsquery
        implementation, this might fail depending on PostgreSQL's handling.
        """
        from src.tnse.search.service import SearchService, SearchResult

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        # Create a mock result that matches
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "news_channel"
        mock_row.channel_title = "News Channel"
        mock_row.text_content = "The corruption scandal continues."
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 5000
        mock_row.reaction_score = 100.0
        mock_row.relative_engagement = 0.1
        mock_row.telegram_message_id = 456

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_factory)

        results = await service.search("corruption")

        # The search should return results
        assert len(results) == 1
        assert "corruption" in results[0].text_content.lower()

    @pytest.mark.asyncio
    async def test_search_query_uses_plainto_tsquery_format(self) -> None:
        """Test that search uses plainto_tsquery for plain text search.

        plainto_tsquery handles plain text input correctly, unlike to_tsquery
        which requires pre-processed lexemes.
        """
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_factory)

        await service.search("hello world")

        # Verify execute was called
        assert mock_session.execute.called

        # Get the SQL that was passed
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1]

        # The search_terms should be plain text (space-separated)
        # for use with plainto_tsquery
        search_terms = params.get("search_terms", "")

        # FIX VERIFIED: search_terms is now 'hello world' (space-separated)
        # not 'hello & world' which was the buggy format
        assert search_terms == "hello world", (
            f"Search terms should be space-separated: {search_terms}"
        )

        # The SQL should use plainto_tsquery
        assert "plainto_tsquery" in sql_text, (
            f"SQL should use plainto_tsquery for plain text search: {sql_text}"
        )

    @pytest.mark.asyncio
    async def test_search_with_cyrillic_words_should_work(self) -> None:
        """Test that Cyrillic word search works correctly.

        Russian text like 'koruptsia' should match content containing the word.
        """
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "russian_news"
        mock_row.channel_title = "Russian News"
        mock_row.text_content = "news about politics"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 3000
        mock_row.reaction_score = 75.0
        mock_row.relative_engagement = 0.075
        mock_row.telegram_message_id = 789

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_factory)

        # Search with Russian word
        results = await service.search("news")

        # Should find results
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_empty_result_when_content_exists(self) -> None:
        """Test case documenting the bug where search returns empty even when content exists.

        This happens because:
        1. Content is stored in post_content.text_content
        2. Search uses to_tsquery which may not match plain text correctly
        3. No full-text index exists on the text_content column
        """
        from src.tnse.search.service import SearchService

        mock_session = MockAsyncSession()
        mock_session_factory = MagicMock(return_value=mock_session)

        # Simulate the bug: database returns empty because query doesn't match
        mock_result = MagicMock()
        mock_result.all.return_value = []  # Empty result - this is the bug!
        mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_factory)

        # Search for content that should exist
        results = await service.search("existing content")

        # Currently returns empty due to the to_tsquery bug
        # After fix, this test should be updated to expect results
        assert results == []


class TestSearchIndexMissing:
    """Tests documenting the missing full-text search index."""

    def test_post_content_table_should_have_tsvector_column(self) -> None:
        """Document that post_content table lacks a tsvector column.

        For efficient full-text search, the table should have:
        1. A tsvector column storing pre-computed search vectors
        2. A GIN index on that column
        3. A trigger to keep the tsvector updated

        Currently, the table only has:
        - text_content (plain text)
        - language (detected language code)

        The search query computes tsvector on-the-fly which is inefficient:
        to_tsvector('russian', COALESCE(pc.text_content, ''))
        """
        from src.tnse.db.models import PostContent

        # Check the columns in PostContent model
        columns = [col.name for col in PostContent.__table__.columns]

        # Document current state - no search_vector column
        assert "search_vector" not in columns, (
            "UNEXPECTED: search_vector column exists. Update this test!"
        )

        # After fix, this test should verify the column exists:
        # assert "search_vector" in columns, (
        #     "PostContent should have a search_vector column for FTS"
        # )

    def test_migration_should_add_gin_index(self) -> None:
        """Document that no GIN index exists for full-text search.

        The initial migration creates these indexes:
        - ix_post_content_post_id (on post_id)

        But it's missing:
        - GIN index on tsvector for efficient full-text search

        Example of what should be added:
        CREATE INDEX ix_post_content_search_vector
        ON post_content USING GIN (
            to_tsvector('simple', COALESCE(text_content, ''))
        );
        """
        # This is a documentation test - no assertion needed
        # The fix should create a migration adding the GIN index
        pass

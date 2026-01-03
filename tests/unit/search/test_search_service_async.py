"""
TNSE Search Service Async Context Manager Tests

Tests verifying that SearchService properly uses async context managers
with AsyncSession from SQLAlchemy.

Work Stream: WS-7.4 - Fix AsyncSession Context Manager Bug

This test file validates the fix for:
    TypeError: 'AsyncSession' object does not support the context manager protocol

The bug occurred because the code used:
    with self.session_factory() as session:  # WRONG - sync

Instead of:
    async with self.session_factory() as session:  # CORRECT - async
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class MockAsyncSession:
    """Mock that simulates an AsyncSession from SQLAlchemy.

    This mock ONLY supports async context manager protocol (__aenter__/__aexit__)
    and deliberately DOES NOT support sync context manager protocol (__enter__/__exit__).

    If code tries to use `with session:` instead of `async with session:`,
    it will fail with AttributeError (no __enter__ method).
    """

    def __init__(self) -> None:
        self.execute = AsyncMock()
        self._is_entered = False

    async def __aenter__(self) -> "MockAsyncSession":
        """Async context manager entry."""
        self._is_entered = True
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> bool:
        """Async context manager exit."""
        self._is_entered = False
        return False


class MockAsyncSessionMaker:
    """Mock that simulates async_sessionmaker from SQLAlchemy.

    Returns MockAsyncSession instances that only support async context managers.
    """

    def __init__(self) -> None:
        self.mock_session = MockAsyncSession()
        self._call_count = 0

    def __call__(self) -> MockAsyncSession:
        """Return a new async session when called."""
        self._call_count += 1
        return self.mock_session


class TestAsyncSessionContextManager:
    """Tests for proper async context manager usage in SearchService."""

    @pytest.mark.asyncio
    async def test_execute_search_uses_async_context_manager(self) -> None:
        """Test that _execute_search uses async with for session management.

        This test will FAIL if the code uses `with self.session_factory()` (sync)
        instead of `async with self.session_factory()` (async).

        The MockAsyncSession only implements __aenter__/__aexit__ (async protocol),
        not __enter__/__exit__ (sync protocol). Using sync `with` will raise
        TypeError or AttributeError.
        """
        from src.tnse.search.service import SearchService, SearchQuery

        # Create mock session maker that returns async-only sessions
        mock_session_maker = MockAsyncSessionMaker()

        # Setup mock return value for execute
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "test_channel"
        mock_row.channel_title = "Test Channel"
        mock_row.text_content = "Test content about politics"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 1000
        mock_row.reaction_score = 50.0
        mock_row.relative_engagement = 0.05
        mock_row.telegram_message_id = 123

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session_maker.mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_maker)

        # This should NOT raise TypeError if async context manager is used properly
        results = await service.search("politics")

        # Verify results were returned
        assert len(results) == 1
        assert results[0].channel_username == "test_channel"

        # Verify execute was called with await
        mock_session_maker.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_search_awaits_session_execute(self) -> None:
        """Test that session.execute() is properly awaited.

        This test verifies that the code uses:
            result = await session.execute(...)

        Instead of:
            result = session.execute(...)  # Would return coroutine, not result
        """
        from src.tnse.search.service import SearchService

        mock_session_maker = MockAsyncSessionMaker()

        # Setup mock - execute returns AsyncMock which tracks if awaited
        mock_row = MagicMock()
        mock_row.post_id = str(uuid4())
        mock_row.channel_id = str(uuid4())
        mock_row.channel_username = "async_test"
        mock_row.channel_title = "Async Test Channel"
        mock_row.text_content = "Async test content"
        mock_row.published_at = datetime.now(timezone.utc)
        mock_row.view_count = 500
        mock_row.reaction_score = 25.0
        mock_row.relative_engagement = 0.025
        mock_row.telegram_message_id = 456

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session_maker.mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_maker)

        results = await service.search("async")

        # If execute was awaited, results should be valid SearchResult objects
        assert len(results) == 1
        assert results[0].text_content == "Async test content"

        # Verify the AsyncMock was awaited
        mock_session_maker.mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_search_with_async_session_maker_returns_results(self) -> None:
        """Integration test: SearchService works with async session maker pattern."""
        from src.tnse.search.service import SearchService, SearchResult

        mock_session_maker = MockAsyncSessionMaker()

        # Create multiple mock rows
        rows = []
        for idx in range(3):
            row = MagicMock()
            row.post_id = str(uuid4())
            row.channel_id = str(uuid4())
            row.channel_username = f"channel_{idx}"
            row.channel_title = f"Channel {idx}"
            row.text_content = f"Content {idx} about news"
            row.published_at = datetime.now(timezone.utc)
            row.view_count = 1000 * (idx + 1)
            row.reaction_score = 10.0 * (idx + 1)
            row.relative_engagement = 0.01 * (idx + 1)
            row.telegram_message_id = 100 + idx
            rows.append(row)

        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_session_maker.mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_maker)

        results = await service.search("news")

        # Verify all results returned
        assert len(results) == 3
        assert all(isinstance(result, SearchResult) for result in results)

        # Verify data integrity
        for idx, result in enumerate(results):
            assert result.channel_username == f"channel_{idx}"
            assert result.view_count == 1000 * (idx + 1)

    @pytest.mark.asyncio
    async def test_search_with_empty_results_async(self) -> None:
        """Test that empty results are handled correctly with async session."""
        from src.tnse.search.service import SearchService

        mock_session_maker = MockAsyncSessionMaker()

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session_maker.mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_maker)

        results = await service.search("nonexistent_keyword_xyz")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_pagination_with_async_session(self) -> None:
        """Test that pagination parameters work with async session."""
        from src.tnse.search.service import SearchService

        mock_session_maker = MockAsyncSessionMaker()

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session_maker.mock_session.execute.return_value = mock_result

        service = SearchService(session_factory=mock_session_maker)

        # Test with pagination parameters
        await service.search("test", limit=50, offset=10)

        # Verify execute was called (pagination params passed in SQL)
        mock_session_maker.mock_session.execute.assert_called_once()

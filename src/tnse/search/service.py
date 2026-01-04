"""
TNSE Search Service

Provides keyword search functionality with PostgreSQL full-text search.

Work Stream: WS-2.2 - Keyword Search Engine

Requirements addressed:
- REQ-MO-005: Keyword-based search in metrics-only mode
- REQ-NP-006: Handle Russian, English, Ukrainian, and other Cyrillic languages
- REQ-NP-007: Rank news by configurable criteria
- NFR-P-007: Metrics-only mode response time < 3 seconds

Python 3.10+ Modernization (WS-6.3):
- Uses X | None instead of Optional[X] for union types
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from sqlalchemy import text

from src.tnse.search.tokenizer import Tokenizer


class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        ...

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a value in the cache with TTL in seconds."""
        ...


@dataclass
class SearchQuery:
    """Query parameters for search requests.

    Attributes:
        keywords: List of keywords to search for.
        hours: Time window in hours (default: 24).
        limit: Maximum number of results to return (default: 100).
        offset: Number of results to skip for pagination (default: 0).
    """

    keywords: list[str]
    hours: int = 24
    limit: int = 100
    offset: int = 0


@dataclass
class SearchResult:
    """A single search result with post and engagement data.

    Attributes:
        post_id: Unique identifier of the post.
        channel_id: Unique identifier of the channel.
        channel_username: Telegram username of the channel.
        channel_title: Display title of the channel.
        text_content: Full text content of the post.
        published_at: When the post was published.
        view_count: Number of views.
        reaction_score: Weighted reaction score.
        relative_engagement: Engagement normalized by subscriber count.
        telegram_message_id: Message ID in Telegram.
    """

    post_id: str
    channel_id: str
    channel_username: str
    channel_title: str
    text_content: str
    published_at: datetime
    view_count: int
    reaction_score: float
    relative_engagement: float
    telegram_message_id: int

    @property
    def preview(self) -> str:
        """Generate a text preview of the post content.

        Returns:
            A truncated preview of the post content (max 200 chars).
        """
        if not self.text_content:
            return ""

        if len(self.text_content) <= 200:
            return self.text_content

        return self.text_content[:200] + "..."

    @property
    def telegram_link(self) -> str:
        """Generate a Telegram deep link to the original post.

        Returns:
            URL to the post on Telegram.
        """
        return f"https://t.me/{self.channel_username}/{self.telegram_message_id}"


@dataclass
class SearchService:
    """Service for keyword search with PostgreSQL full-text search.

    Provides search functionality for posts within a configurable time window
    using PostgreSQL's built-in full-text search capabilities with support
    for Russian, English, and Ukrainian content.

    Attributes:
        session_factory: Factory for creating database sessions.
        cache: Optional cache for search results.
        tokenizer: Tokenizer for processing search queries.
        cache_ttl: Time-to-live for cached results in seconds (default: 300).
    """

    session_factory: Callable[..., Any]
    cache: CacheProtocol | None = None
    tokenizer: Tokenizer = field(default_factory=Tokenizer)
    cache_ttl: int = 300

    async def search(
        self,
        query: str,
        hours: int = 24,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SearchResult]:
        """Search for posts matching the given keywords.

        Performs a full-text search on post content within the specified
        time window, returning results sorted by engagement score.

        Args:
            query: Search query string (can contain multiple keywords).
            hours: Time window in hours (default: 24).
            limit: Maximum number of results (default: 100).
            offset: Number of results to skip (default: 0).

        Returns:
            List of SearchResult objects matching the query.
        """
        # Handle empty or whitespace-only queries
        if not query or not query.strip():
            return []

        # Tokenize the query
        keywords = self.tokenizer.tokenize(query)
        if not keywords:
            return []

        # Build search query object
        search_query = SearchQuery(
            keywords=keywords,
            hours=hours,
            limit=limit,
            offset=offset,
        )

        # Check cache first
        if self.cache:
            cache_key = self._build_cache_key(search_query)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return self._deserialize_results(cached)

        # Execute database search
        results = await self._execute_search(search_query)

        # Cache results
        if self.cache and results:
            cache_key = self._build_cache_key(search_query)
            self.cache.set(
                cache_key,
                self._serialize_results(results),
                ttl=self.cache_ttl,
            )

        return results

    async def _execute_search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute the search query against the database.

        Uses PostgreSQL full-text search with support for Russian and
        English text configurations.

        Args:
            query: The search query parameters.

        Returns:
            List of SearchResult objects.
        """
        # Calculate time window cutoff
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=query.hours)

        # Build the search query with parameterized values
        # Join keywords with space for plainto_tsquery (plain text input)
        search_terms = " ".join(query.keywords)

        # Use plainto_tsquery instead of to_tsquery for plain text search.
        # plainto_tsquery handles plain text input and converts it to a
        # tsquery automatically, while to_tsquery requires pre-formatted
        # tsquery syntax with lexemes.
        #
        # Also use websearch_to_tsquery for 'simple' config as it provides
        # more flexible search with implicit AND between terms.
        sql = text("""
            SELECT
                p.id AS post_id,
                p.channel_id,
                c.username AS channel_username,
                c.title AS channel_title,
                pc.text_content,
                p.published_at,
                p.telegram_message_id,
                COALESCE(em.view_count, 0) AS view_count,
                COALESCE(em.reaction_score, 0.0) AS reaction_score,
                COALESCE(em.relative_engagement, 0.0) AS relative_engagement
            FROM posts p
            JOIN channels c ON p.channel_id = c.id
            LEFT JOIN post_content pc ON p.id = pc.post_id
            LEFT JOIN LATERAL (
                SELECT view_count, reaction_score, relative_engagement
                FROM engagement_metrics
                WHERE post_id = p.id
                ORDER BY collected_at DESC
                LIMIT 1
            ) em ON true
            WHERE p.published_at >= :cutoff_time
            AND (
                to_tsvector('russian', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('russian', :search_terms)
                OR to_tsvector('english', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('english', :search_terms)
                OR to_tsvector('simple', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('simple', :search_terms)
            )
            ORDER BY em.relative_engagement DESC, em.view_count DESC
            LIMIT :limit OFFSET :offset
        """)

        async with self.session_factory() as session:
            result = await session.execute(
                sql,
                {
                    "cutoff_time": cutoff_time,
                    "search_terms": search_terms,
                    "limit": query.limit,
                    "offset": query.offset,
                },
            )
            rows = result.all()

        return [
            SearchResult(
                post_id=str(row.post_id),
                channel_id=str(row.channel_id),
                channel_username=row.channel_username,
                channel_title=row.channel_title,
                text_content=row.text_content or "",
                published_at=row.published_at,
                view_count=row.view_count,
                reaction_score=row.reaction_score,
                relative_engagement=row.relative_engagement,
                telegram_message_id=row.telegram_message_id,
            )
            for row in rows
        ]

    def _build_cache_key(self, query: SearchQuery) -> str:
        """Build a cache key for the search query.

        Args:
            query: The search query parameters.

        Returns:
            A unique cache key string.
        """
        key_data = {
            "keywords": sorted(query.keywords),
            "hours": query.hours,
            "limit": query.limit,
            "offset": query.offset,
        }
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]
        return f"search:{key_hash}"

    def _serialize_results(self, results: list[SearchResult]) -> list[dict]:
        """Serialize search results for caching.

        Args:
            results: List of SearchResult objects.

        Returns:
            List of serializable dictionaries.
        """
        return [
            {
                "post_id": result.post_id,
                "channel_id": result.channel_id,
                "channel_username": result.channel_username,
                "channel_title": result.channel_title,
                "text_content": result.text_content,
                "published_at": result.published_at.isoformat(),
                "view_count": result.view_count,
                "reaction_score": result.reaction_score,
                "relative_engagement": result.relative_engagement,
                "telegram_message_id": result.telegram_message_id,
            }
            for result in results
        ]

    def _deserialize_results(self, cached: list[dict]) -> list[SearchResult]:
        """Deserialize cached search results.

        Args:
            cached: List of serialized result dictionaries.

        Returns:
            List of SearchResult objects.
        """
        return [
            SearchResult(
                post_id=item["post_id"],
                channel_id=item["channel_id"],
                channel_username=item["channel_username"],
                channel_title=item["channel_title"],
                text_content=item["text_content"],
                published_at=datetime.fromisoformat(item["published_at"]),
                view_count=item["view_count"],
                reaction_score=item["reaction_score"],
                relative_engagement=item["relative_engagement"],
                telegram_message_id=item["telegram_message_id"],
            )
            for item in cached
        ]

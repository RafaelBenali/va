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
        category: Optional category filter (politics, economics, etc.).
        sentiment: Optional sentiment filter (positive, negative, neutral).
        include_enrichment: Whether to include enrichment data in search.
    """

    keywords: list[str]
    hours: int = 24
    limit: int = 100
    offset: int = 0
    category: str | None = None
    sentiment: str | None = None
    include_enrichment: bool = True


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
        forward_count: Number of forwards/reposts.
        reply_count: Number of replies/comments.
        reaction_score: Weighted reaction score.
        relative_engagement: Engagement normalized by subscriber count.
        reactions: Dictionary mapping emoji names to counts.
        telegram_message_id: Message ID in Telegram.
        category: LLM-extracted topic category (optional).
        sentiment: LLM-extracted sentiment (positive/negative/neutral).
        explicit_keywords: Keywords directly in the text (optional).
        implicit_keywords: Related concepts NOT in text - key RAG feature.
        match_type: How the search matched (fulltext/explicit_keyword/implicit_keyword).
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
    # Additional engagement metrics (Issue 3 fix)
    forward_count: int = 0
    reply_count: int = 0
    reactions: dict[str, int] | None = None
    # Enrichment fields (optional, for backward compatibility)
    category: str | None = None
    sentiment: str | None = None
    explicit_keywords: list[str] | None = None
    implicit_keywords: list[str] | None = None
    match_type: str | None = None

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

    @property
    def is_enriched(self) -> bool:
        """Check if this result has LLM enrichment data.

        Returns:
            True if any enrichment fields are populated.
        """
        return (
            self.category is not None
            or self.sentiment is not None
            or self.explicit_keywords is not None
            or self.implicit_keywords is not None
        )


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
        category: str | None = None,
        sentiment: str | None = None,
        include_enrichment: bool = True,
    ) -> list[SearchResult]:
        """Search for posts matching the given keywords.

        Performs a hybrid search combining full-text search on post content
        and keyword array matching on enriched data (explicit and implicit
        keywords) within the specified time window.

        WS-5.5: Enhanced Search with Keyword Retrieval

        Args:
            query: Search query string (can contain multiple keywords).
            hours: Time window in hours (default: 24).
            limit: Maximum number of results (default: 100).
            offset: Number of results to skip (default: 0).
            category: Optional category filter (politics, economics, etc.).
            sentiment: Optional sentiment filter (positive, negative, neutral).
            include_enrichment: Include enrichment data in search (default: True).

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
            category=category,
            sentiment=sentiment,
            include_enrichment=include_enrichment,
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

        Uses hybrid search combining:
        1. PostgreSQL full-text search with Russian/English/simple configs
        2. Keyword array matching on explicit_keywords and implicit_keywords

        WS-5.5: Enhanced Search with Keyword Retrieval

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

        # Prepare keywords as lowercase array for array overlap matching
        search_keywords = [keyword.lower() for keyword in query.keywords]

        # Build SQL based on whether enrichment is included
        if query.include_enrichment:
            sql = self._build_enriched_search_sql(query)
        else:
            sql = self._build_basic_search_sql()

        # Build parameters
        params: dict[str, Any] = {
            "cutoff_time": cutoff_time,
            "search_terms": search_terms,
            "search_keywords": search_keywords,
            "limit": query.limit,
            "offset": query.offset,
        }

        # Add optional filters
        if query.category:
            params["category"] = query.category
        if query.sentiment:
            params["sentiment"] = query.sentiment

        async with self.session_factory() as session:
            result = await session.execute(sql, params)
            rows = result.all()

        return self._rows_to_results(rows, query.include_enrichment)

    def _build_basic_search_sql(self) -> Any:
        """Build SQL for basic search without enrichment.

        Returns:
            SQLAlchemy text clause for basic search.
        """
        return text("""
            SELECT
                p.id AS post_id,
                p.channel_id,
                c.username AS channel_username,
                c.title AS channel_title,
                pc.text_content,
                p.published_at,
                p.telegram_message_id,
                COALESCE(em.view_count, 0) AS view_count,
                COALESCE(em.forward_count, 0) AS forward_count,
                COALESCE(em.reply_count, 0) AS reply_count,
                COALESCE(em.reaction_score, 0.0) AS reaction_score,
                COALESCE(em.relative_engagement, 0.0) AS relative_engagement,
                em.reactions_json AS reactions,
                NULL::VARCHAR AS category,
                NULL::VARCHAR AS sentiment,
                NULL::TEXT[] AS explicit_keywords,
                NULL::TEXT[] AS implicit_keywords
            FROM posts p
            JOIN channels c ON p.channel_id = c.id
            LEFT JOIN post_content pc ON p.id = pc.post_id
            LEFT JOIN LATERAL (
                SELECT
                    em_inner.view_count,
                    em_inner.forward_count,
                    em_inner.reply_count,
                    em_inner.reaction_score,
                    em_inner.relative_engagement,
                    (
                        SELECT jsonb_object_agg(rc.emoji, rc.count)
                        FROM reaction_counts rc
                        WHERE rc.engagement_metrics_id = em_inner.id
                    ) AS reactions_json
                FROM engagement_metrics em_inner
                WHERE em_inner.post_id = p.id
                ORDER BY em_inner.collected_at DESC
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

    def _build_enriched_search_sql(self, query: SearchQuery) -> Any:
        """Build SQL for enriched search with keyword arrays.

        WS-5.5: Hybrid search combining full-text and keyword array matching.

        Args:
            query: Search query with optional category/sentiment filters.

        Returns:
            SQLAlchemy text clause for enriched search.
        """
        # Build filter conditions
        filter_conditions = []
        if query.category:
            filter_conditions.append("AND pe.category = :category")
        if query.sentiment:
            filter_conditions.append("AND pe.sentiment = :sentiment")

        filter_sql = " ".join(filter_conditions)

        sql_template = f"""
            SELECT
                p.id AS post_id,
                p.channel_id,
                c.username AS channel_username,
                c.title AS channel_title,
                pc.text_content,
                p.published_at,
                p.telegram_message_id,
                COALESCE(em.view_count, 0) AS view_count,
                COALESCE(em.forward_count, 0) AS forward_count,
                COALESCE(em.reply_count, 0) AS reply_count,
                COALESCE(em.reaction_score, 0.0) AS reaction_score,
                COALESCE(em.relative_engagement, 0.0) AS relative_engagement,
                em.reactions_json AS reactions,
                pe.category,
                pe.sentiment,
                pe.explicit_keywords,
                pe.implicit_keywords
            FROM posts p
            JOIN channels c ON p.channel_id = c.id
            LEFT JOIN post_content pc ON p.id = pc.post_id
            LEFT JOIN post_enrichments pe ON p.id = pe.post_id
            LEFT JOIN LATERAL (
                SELECT
                    em_inner.view_count,
                    em_inner.forward_count,
                    em_inner.reply_count,
                    em_inner.reaction_score,
                    em_inner.relative_engagement,
                    (
                        SELECT jsonb_object_agg(rc.emoji, rc.count)
                        FROM reaction_counts rc
                        WHERE rc.engagement_metrics_id = em_inner.id
                    ) AS reactions_json
                FROM engagement_metrics em_inner
                WHERE em_inner.post_id = p.id
                ORDER BY em_inner.collected_at DESC
                LIMIT 1
            ) em ON true
            WHERE p.published_at >= :cutoff_time
            {filter_sql}
            AND (
                -- Full-text search on content
                to_tsvector('russian', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('russian', :search_terms)
                OR to_tsvector('english', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('english', :search_terms)
                OR to_tsvector('simple', COALESCE(pc.text_content, '')) @@
                    plainto_tsquery('simple', :search_terms)
                -- Keyword array matching (explicit keywords)
                OR pe.explicit_keywords && :search_keywords
                -- Keyword array matching (implicit keywords - key RAG feature)
                OR pe.implicit_keywords && :search_keywords
            )
            ORDER BY em.relative_engagement DESC, em.view_count DESC
            LIMIT :limit OFFSET :offset
        """
        return text(sql_template)

    def _rows_to_results(
        self,
        rows: list[Any],
        include_enrichment: bool,
    ) -> list[SearchResult]:
        """Convert database rows to SearchResult objects.

        Args:
            rows: List of database row objects.
            include_enrichment: Whether to include enrichment fields.

        Returns:
            List of SearchResult objects.
        """
        results = []
        for row in rows:
            # Extract reactions from JSONB (may be None or a dict)
            reactions = None
            if hasattr(row, "reactions") and row.reactions:
                # Convert JSONB to Python dict if needed
                if isinstance(row.reactions, dict):
                    reactions = row.reactions
                else:
                    # Handle case where it might come as a string
                    import json
                    try:
                        reactions = json.loads(row.reactions)
                    except (TypeError, json.JSONDecodeError):
                        reactions = None

            result = SearchResult(
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
                # Additional engagement metrics (Issue 3 fix)
                forward_count=getattr(row, "forward_count", 0) or 0,
                reply_count=getattr(row, "reply_count", 0) or 0,
                reactions=reactions,
            )

            # Add enrichment fields if available
            if include_enrichment and hasattr(row, "category"):
                result.category = row.category
                result.sentiment = row.sentiment
                result.explicit_keywords = row.explicit_keywords
                result.implicit_keywords = row.implicit_keywords

            results.append(result)

        return results

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
            "category": query.category,
            "sentiment": query.sentiment,
            "include_enrichment": query.include_enrichment,
        }
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]
        return f"search:{key_hash}"

    def _serialize_results(self, results: list[SearchResult]) -> list[dict]:
        """Serialize search results for caching.

        Includes enrichment fields for proper cache restoration.

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
                "forward_count": result.forward_count,
                "reply_count": result.reply_count,
                "reaction_score": result.reaction_score,
                "relative_engagement": result.relative_engagement,
                "reactions": result.reactions,
                "telegram_message_id": result.telegram_message_id,
                # Enrichment fields (WS-5.5)
                "category": result.category,
                "sentiment": result.sentiment,
                "explicit_keywords": result.explicit_keywords,
                "implicit_keywords": result.implicit_keywords,
                "match_type": result.match_type,
            }
            for result in results
        ]

    def _deserialize_results(self, cached: list[dict]) -> list[SearchResult]:
        """Deserialize cached search results.

        Restores enrichment fields for proper cache hit behavior.

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
                forward_count=item.get("forward_count", 0),
                reply_count=item.get("reply_count", 0),
                reaction_score=item["reaction_score"],
                relative_engagement=item["relative_engagement"],
                reactions=item.get("reactions"),
                telegram_message_id=item["telegram_message_id"],
                # Enrichment fields (WS-5.5)
                category=item.get("category"),
                sentiment=item.get("sentiment"),
                explicit_keywords=item.get("explicit_keywords"),
                implicit_keywords=item.get("implicit_keywords"),
                match_type=item.get("match_type"),
            )
            for item in cached
        ]

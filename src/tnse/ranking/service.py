"""
TNSE Ranking Service

Provides business logic for ranking posts by engagement and recency.

Work Stream: WS-2.3 - Ranking Algorithm

Requirements addressed:
- REQ-MO-006: System MUST rank posts using: views, reaction score, and relative engagement
- Ranking by combined score: engagement * recency
- Sorting options: views, reactions, engagement, recency, combined
- Configurable time window (default 24 hours)
- Configurable weight for recency vs engagement

Python 3.10+ Modernization (WS-6.3):
- Uses match/case for enum-based dispatch
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from uuid import UUID


class SortMode(Enum):
    """Enumeration of available sorting modes for ranking posts.

    Attributes:
        COMBINED: Sort by combined score (engagement * recency factor)
        VIEWS: Sort by view count (highest first)
        REACTIONS: Sort by reaction score (highest first)
        ENGAGEMENT: Sort by relative engagement (highest first)
        RECENCY: Sort by post time (newest first)
    """

    COMBINED = "combined"
    VIEWS = "views"
    REACTIONS = "reactions"
    ENGAGEMENT = "engagement"
    RECENCY = "recency"


@dataclass
class RankedPost:
    """Represents a post with its ranking information.

    Attributes:
        post_id: UUID of the post.
        view_count: Number of views on the post.
        reaction_score: Weighted reaction score.
        relative_engagement: Engagement normalized by subscriber count.
        posted_at: Timestamp when the post was created.
        combined_score: Calculated combined ranking score.
    """

    post_id: UUID
    view_count: int
    reaction_score: float
    relative_engagement: float
    posted_at: datetime
    combined_score: float


@dataclass
class RankingService:
    """Service for ranking posts by engagement and recency.

    This service provides methods to:
    - Calculate recency factors based on post age
    - Calculate combined scores using engagement and recency
    - Rank collections of posts by various criteria
    - Support multiple sorting modes

    Attributes:
        time_window_hours: Time window in hours for recency calculation.
            Posts older than this have zero recency factor. Default: 24.
        recency_weight: Weight for recency in combined score calculation.
            Value of 1.0 means full recency impact, 0.0 means engagement only.
            Default: 1.0.

    Example:
        >>> service = RankingService(time_window_hours=24, recency_weight=1.0)
        >>> posts = [{"post_id": uuid4(), "relative_engagement": 0.5, "posted_at": now}]
        >>> ranked = service.rank_posts(posts, sort_mode=SortMode.COMBINED)
    """

    time_window_hours: int = 24
    recency_weight: float = 1.0

    def calculate_recency_factor(
        self,
        posted_at: datetime,
        reference_time: datetime | None = None,
    ) -> float:
        """Calculate the recency factor for a post.

        The recency factor represents how recent a post is within the time window.
        A brand new post has factor 1.0, a post at the edge of the window has 0.0.

        Formula: recency_factor = max(0, 1 - hours_since_post / time_window_hours)

        Args:
            posted_at: Timestamp when the post was created.
            reference_time: Reference time for calculation. Defaults to now (UTC).

        Returns:
            Recency factor as float between 0.0 and 1.0.
            Returns 1.0 for future posts (edge case).
            Returns 0.0 for posts older than the time window.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Handle naive datetime by treating as UTC
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        # Calculate time difference
        time_diff = reference_time - posted_at
        hours_since_post = time_diff.total_seconds() / 3600.0

        # Handle future posts (edge case)
        if hours_since_post < 0:
            return 1.0

        # Calculate recency factor
        recency_factor = 1.0 - (hours_since_post / self.time_window_hours)

        # Clamp to valid range
        return max(0.0, min(1.0, recency_factor))

    def calculate_combined_score(
        self,
        relative_engagement: float,
        recency_factor: float,
    ) -> float:
        """Calculate the combined ranking score.

        The combined score blends engagement and recency based on the recency_weight.

        With recency_weight=1.0:
            combined = engagement * recency_factor

        With recency_weight=0.0:
            combined = engagement (recency has no effect)

        With recency_weight=0.5:
            combined = engagement * (0.5 + 0.5 * recency_factor)
            This gives half the base engagement plus half weighted by recency.

        General formula:
            combined = engagement * (1 - recency_weight + recency_factor * recency_weight)

        Args:
            relative_engagement: Engagement normalized by subscriber count.
            recency_factor: Recency factor from calculate_recency_factor.

        Returns:
            Combined ranking score as float.
        """
        # Apply weighted recency
        recency_multiplier = (1.0 - self.recency_weight) + (recency_factor * self.recency_weight)
        return relative_engagement * recency_multiplier

    def calculate_score_for_post(
        self,
        post_data: dict[str, Any],
        reference_time: datetime | None = None,
    ) -> float:
        """Calculate the combined score for a single post.

        Args:
            post_data: Dictionary containing post data with:
                - relative_engagement: Engagement normalized by subscribers.
                - posted_at: Timestamp when post was created.
            reference_time: Reference time for recency calculation.

        Returns:
            Combined ranking score as float.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        relative_engagement = post_data.get("relative_engagement", 0.0)
        posted_at = post_data.get("posted_at", reference_time)

        recency_factor = self.calculate_recency_factor(posted_at, reference_time)
        return self.calculate_combined_score(relative_engagement, recency_factor)

    def rank_posts(
        self,
        posts: list[dict[str, Any]],
        sort_mode: SortMode = SortMode.COMBINED,
        reference_time: datetime | None = None,
    ) -> list[RankedPost]:
        """Rank a collection of posts by the specified criteria.

        Creates RankedPost objects with computed combined scores and sorts them
        according to the specified mode.

        Args:
            posts: List of post dictionaries containing:
                - post_id: UUID of the post (required)
                - view_count: Number of views (default: 0)
                - reaction_score: Weighted reaction score (default: 0.0)
                - relative_engagement: Engagement ratio (default: 0.0)
                - posted_at: Post timestamp (default: reference_time)
            sort_mode: Sorting mode from SortMode enum.
            reference_time: Reference time for recency calculations.

        Returns:
            List of RankedPost objects sorted according to sort_mode.
            Higher values come first (descending order).
        """
        if not posts:
            return []

        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Convert posts to RankedPost objects
        ranked_posts = []
        for post_data in posts:
            post_id = post_data.get("post_id")
            view_count = post_data.get("view_count", 0)
            reaction_score = post_data.get("reaction_score", 0.0)
            relative_engagement = post_data.get("relative_engagement", 0.0)
            posted_at = post_data.get("posted_at", reference_time)

            # Calculate combined score
            combined_score = self.calculate_score_for_post(post_data, reference_time)

            ranked_post = RankedPost(
                post_id=post_id,
                view_count=view_count,
                reaction_score=reaction_score,
                relative_engagement=relative_engagement,
                posted_at=posted_at,
                combined_score=combined_score,
            )
            ranked_posts.append(ranked_post)

        # Sort based on mode using match/case (Python 3.10+)
        match sort_mode:
            case SortMode.COMBINED:
                ranked_posts.sort(key=lambda post: post.combined_score, reverse=True)
            case SortMode.VIEWS:
                ranked_posts.sort(key=lambda post: post.view_count, reverse=True)
            case SortMode.REACTIONS:
                ranked_posts.sort(key=lambda post: post.reaction_score, reverse=True)
            case SortMode.ENGAGEMENT:
                ranked_posts.sort(key=lambda post: post.relative_engagement, reverse=True)
            case SortMode.RECENCY:
                ranked_posts.sort(key=lambda post: post.posted_at, reverse=True)

        return ranked_posts

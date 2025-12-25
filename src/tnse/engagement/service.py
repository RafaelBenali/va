"""
TNSE Engagement Service

Provides business logic for engagement metrics extraction and calculation.

Work Stream: WS-2.1 - Engagement Metrics

Requirements addressed:
- REQ-MO-002: System MUST retrieve and display view counts for each post
- REQ-MO-003: System MUST count EACH emoji reaction type separately
- REQ-MO-004: System MUST calculate a "reaction score" based on individual emoji counts
- REQ-MO-006: System MUST rank posts using: views, reaction score, and relative engagement
- REQ-MO-007: System SHOULD allow users to configure reaction score weights
- NFR-D-002: Engagement metrics MUST be stored with timestamps
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from src.tnse.core.config import get_settings


@dataclass
class EngagementService:
    """Service for extracting and calculating engagement metrics.

    This service provides methods to:
    - Calculate reaction scores with configurable weights
    - Extract view counts from message data
    - Extract individual emoji reaction counts
    - Calculate relative engagement (normalized by subscriber count)
    - Create engagement metrics records for database storage

    Attributes:
        reaction_weights: Dictionary mapping emoji names to weight values.
            If not provided, default weights from settings are used.
        default_weight: Weight used for unknown emoji types (default: 1.0).

    Example:
        >>> service = EngagementService()
        >>> reactions = {"heart": 10, "thumbs_up": 20}
        >>> score = service.calculate_reaction_score(reactions)
        >>> print(score)  # 10 * 2.0 + 20 * 1.0 = 40.0
    """

    reaction_weights: dict[str, float] = field(default_factory=dict)
    default_weight: float = 1.0

    def __post_init__(self) -> None:
        """Initialize reaction weights from settings if not provided."""
        if not self.reaction_weights:
            settings = get_settings()
            self.reaction_weights = {
                "heart": settings.reaction_weights.heart,
                "thumbs_up": settings.reaction_weights.thumbs_up,
                "fire": settings.reaction_weights.fire,
                "clap": settings.reaction_weights.clap,
                "thinking": settings.reaction_weights.thinking,
                "thumbs_down": settings.reaction_weights.thumbs_down,
            }
            self.default_weight = settings.reaction_weights.default

    def get_reaction_weights(self) -> dict[str, float]:
        """Get the current reaction weight configuration.

        Returns:
            Dictionary mapping emoji names to their weight values.
        """
        return self.reaction_weights.copy()

    def get_weight_for_emoji(self, emoji: str) -> float:
        """Get the weight for a specific emoji.

        Args:
            emoji: The emoji identifier (e.g., 'heart', 'thumbs_up').

        Returns:
            The weight for the emoji, or default_weight if unknown.
        """
        return self.reaction_weights.get(emoji, self.default_weight)

    def calculate_reaction_score(
        self,
        reactions: Optional[dict[str, int]],
    ) -> float:
        """Calculate the weighted reaction score.

        Implements the formula:
        reaction_score = sum(emoji_count * emoji_weight for emoji in reactions)

        Args:
            reactions: Dictionary mapping emoji names to counts.
                Can be None or empty.

        Returns:
            Weighted reaction score as float. Returns 0.0 for empty/None input.

        Example:
            >>> service = EngagementService()
            >>> reactions = {"thumbs_up": 150, "heart": 89, "fire": 34}
            >>> score = service.calculate_reaction_score(reactions)
            >>> # 150*1.0 + 89*2.0 + 34*1.5 = 379.0
        """
        if not reactions:
            return 0.0

        score = 0.0
        for emoji, count in reactions.items():
            weight = self.get_weight_for_emoji(emoji)
            score += count * weight

        return score

    def extract_view_count(self, message_data: dict[str, Any]) -> int:
        """Extract view count from message data.

        Args:
            message_data: Dictionary containing message data with optional 'views' key.

        Returns:
            View count as integer. Returns 0 if not present or None.
        """
        view_count = message_data.get("views")
        if view_count is None:
            return 0
        return view_count

    def extract_reactions(self, message_data: dict[str, Any]) -> dict[str, int]:
        """Extract individual emoji reaction counts from message data.

        Preserves each emoji type separately as required by REQ-MO-003.

        Args:
            message_data: Dictionary containing message data with optional 'reactions' key.

        Returns:
            Dictionary mapping emoji names to counts. Returns empty dict if not present.
        """
        reactions = message_data.get("reactions")
        if reactions is None:
            return {}
        return reactions.copy()

    def calculate_relative_engagement(
        self,
        views: int,
        reaction_score: float,
        subscriber_count: int,
    ) -> float:
        """Calculate relative engagement normalized by subscriber count.

        Implements the formula:
        relative_engagement = (views + reaction_score) / subscriber_count

        Args:
            views: Number of post views.
            reaction_score: Calculated weighted reaction score.
            subscriber_count: Channel subscriber count.

        Returns:
            Relative engagement as float. Returns 0.0 if subscriber_count is 0
            to avoid division by zero.
        """
        if subscriber_count == 0:
            return 0.0

        return (views + reaction_score) / subscriber_count

    def create_engagement_metrics(
        self,
        post_id: UUID,
        message_data: dict[str, Any],
        subscriber_count: int,
    ) -> dict[str, Any]:
        """Create a complete engagement metrics record for database storage.

        Extracts all metrics from message data and calculates derived values.
        Includes a UTC timestamp as required by NFR-D-002.

        Args:
            post_id: UUID of the post this metrics record belongs to.
            message_data: Dictionary containing message data including views,
                forwards, replies, and reactions.
            subscriber_count: Channel subscriber count for relative engagement.

        Returns:
            Dictionary containing all engagement metrics fields ready for
            database insertion:
            - post_id: UUID of the parent post
            - view_count: Number of views
            - forward_count: Number of forwards
            - reply_count: Number of replies
            - reaction_score: Calculated weighted score
            - relative_engagement: Engagement normalized by subscribers
            - collected_at: UTC timestamp when metrics were collected
        """
        view_count = self.extract_view_count(message_data)
        reactions = self.extract_reactions(message_data)
        reaction_score = self.calculate_reaction_score(reactions)
        relative_engagement = self.calculate_relative_engagement(
            views=view_count,
            reaction_score=reaction_score,
            subscriber_count=subscriber_count,
        )

        return {
            "post_id": post_id,
            "view_count": view_count,
            "forward_count": message_data.get("forwards", 0),
            "reply_count": message_data.get("replies", 0),
            "reaction_score": reaction_score,
            "relative_engagement": relative_engagement,
            "collected_at": datetime.now(timezone.utc),
        }

    def create_reaction_counts(
        self,
        engagement_metrics_id: UUID,
        reactions: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Create reaction count records for database storage.

        Creates one record per emoji type as required by REQ-MO-003.

        Args:
            engagement_metrics_id: UUID of the parent engagement metrics record.
            reactions: Dictionary mapping emoji names to counts.

        Returns:
            List of dictionaries containing reaction count fields:
            - engagement_metrics_id: UUID of parent metrics record
            - emoji: Emoji identifier string
            - count: Number of this reaction type
        """
        if not reactions:
            return []

        records = []
        for emoji, count in reactions.items():
            record = {
                "engagement_metrics_id": engagement_metrics_id,
                "emoji": emoji,
                "count": count,
            }
            records.append(record)

        return records

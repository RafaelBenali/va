"""
TNSE Content Storage Service

Service for persisting collected content to the database.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Store in database
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from src.tnse.core.config import get_settings


@dataclass
class ContentStorage:
    """Service for persisting collected content to the database.

    Provides methods to:
    - Create post records
    - Create content records
    - Create media records
    - Create engagement metric records
    - Calculate reaction scores
    - Calculate relative engagement

    Attributes:
        session_factory: Factory for creating database sessions
        reaction_weights: Weights for calculating reaction scores
    """

    session_factory: Callable
    reaction_weights: dict[str, float] = field(default_factory=dict)

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

    def create_post_record(self, message_data: dict[str, Any]) -> dict[str, Any]:
        """Create a post record dictionary for database insertion.

        Args:
            message_data: Extracted message data from collector.

        Returns:
            Dictionary containing post fields ready for insertion.
        """
        return {
            "telegram_message_id": message_data["telegram_message_id"],
            "channel_id": message_data["channel_id"],
            "published_at": message_data["published_at"],
            "is_forwarded": message_data["is_forwarded"],
            "forward_from_channel_id": message_data.get("forward_from_channel_id"),
            "forward_from_message_id": message_data.get("forward_from_message_id"),
        }

    def create_content_record(
        self,
        post_id: UUID,
        message_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a content record dictionary for database insertion.

        Args:
            post_id: UUID of the parent post.
            message_data: Extracted message data from collector.

        Returns:
            Dictionary containing content fields ready for insertion.
        """
        text_content = message_data.get("text_content", "")
        # A post is media-only if it has no text or only whitespace
        is_media_only = not text_content or not text_content.strip()
        return {
            "post_id": post_id,
            "text_content": text_content,
            "language": message_data.get("language"),
            "is_media_only": is_media_only,
        }

    def create_media_records(
        self,
        post_id: UUID,
        message_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create media record dictionaries for database insertion.

        Args:
            post_id: UUID of the parent post.
            message_data: Extracted message data from collector.

        Returns:
            List of dictionaries containing media fields ready for insertion.
        """
        media_list = message_data.get("media", [])
        if not media_list:
            return []

        records = []
        for media in media_list:
            record = {
                "post_id": post_id,
                "media_type": media.get("media_type"),
                "file_id": media.get("file_id"),
                "file_size": media.get("file_size"),
                "mime_type": media.get("mime_type"),
                "width": media.get("width"),
                "height": media.get("height"),
                "duration": media.get("duration"),
                "thumbnail_file_id": media.get("thumbnail_file_id"),
            }
            records.append(record)

        return records

    def create_engagement_record(
        self,
        post_id: UUID,
        message_data: dict[str, Any],
        subscriber_count: int = 0,
    ) -> dict[str, Any]:
        """Create an engagement metrics record for database insertion.

        Args:
            post_id: UUID of the parent post.
            message_data: Extracted message data from collector.
            subscriber_count: Channel subscriber count for relative engagement.

        Returns:
            Dictionary containing engagement metrics ready for insertion.
        """
        reactions = message_data.get("reactions", {})
        reaction_score = self.calculate_reaction_score(reactions)
        relative_engagement = self.calculate_relative_engagement(
            views=message_data.get("views", 0),
            reaction_score=reaction_score,
            subscriber_count=subscriber_count,
        )

        return {
            "post_id": post_id,
            "view_count": message_data.get("views", 0),
            "forward_count": message_data.get("forwards", 0),
            "reply_count": message_data.get("replies", 0),
            "reaction_score": reaction_score,
            "relative_engagement": relative_engagement,
            "collected_at": datetime.now(timezone.utc),
        }

    def create_reaction_records(
        self,
        engagement_metrics_id: UUID,
        reactions: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Create reaction count records for database insertion.

        Args:
            engagement_metrics_id: UUID of the parent engagement metrics.
            reactions: Dictionary mapping emoji names to counts.

        Returns:
            List of dictionaries containing reaction counts.
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

    def calculate_reaction_score(self, reactions: dict[str, int]) -> float:
        """Calculate the weighted reaction score.

        Uses configurable weights for each emoji type.
        Unknown emojis use the default weight.

        Args:
            reactions: Dictionary mapping emoji names to counts.

        Returns:
            Weighted reaction score as float.
        """
        if not reactions:
            return 0.0

        score = 0.0
        for emoji, count in reactions.items():
            weight = self.reaction_weights.get(emoji, getattr(self, "default_weight", 1.0))
            score += count * weight

        return score

    def calculate_relative_engagement(
        self,
        views: int,
        reaction_score: float,
        subscriber_count: int,
    ) -> float:
        """Calculate relative engagement normalized by subscriber count.

        Formula: (views + reaction_score) / subscriber_count

        Args:
            views: Number of views.
            reaction_score: Weighted reaction score.
            subscriber_count: Channel subscriber count.

        Returns:
            Relative engagement as float (0.0 if no subscribers).
        """
        if subscriber_count == 0:
            return 0.0

        return (views + reaction_score) / subscriber_count

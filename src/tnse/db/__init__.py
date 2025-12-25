"""
TNSE Database Module

Provides database models, connection management, and schema definitions.
"""

from src.tnse.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.tnse.db.models import (
    BotSettings,
    Channel,
    ChannelHealthLog,
    ChannelStatus,
    EngagementMetrics,
    MediaType,
    Post,
    PostContent,
    PostMedia,
    ReactionCount,
    SavedTopic,
    TopicTemplate,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Enums
    "ChannelStatus",
    "MediaType",
    # Channel models
    "Channel",
    "ChannelHealthLog",
    # Post models
    "Post",
    "PostContent",
    "PostMedia",
    # Engagement models
    "EngagementMetrics",
    "ReactionCount",
    # Topic models
    "SavedTopic",
    "TopicTemplate",
    # Settings
    "BotSettings",
]

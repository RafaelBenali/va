"""
TNSE Database Models

Provides SQLAlchemy ORM models for the TNSE database schema.

Requirements addressed:
- WS-1.2: Database Schema
- REQ-CC-003: Channel metadata (name, description, subscriber count)
- REQ-CC-006: Channel health status (accessible, rate-limited, removed)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.tnse.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChannelStatus(str, Enum):
    """Enumeration of possible channel health statuses.

    Used to track the current accessibility state of a monitored channel.
    """

    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    INACCESSIBLE = "inaccessible"
    REMOVED = "removed"


class MediaType(str, Enum):
    """Enumeration of possible media types in posts.

    Used to classify media attachments in Telegram posts.
    """

    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    ANIMATION = "animation"


class Channel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a monitored Telegram channel.

    Stores channel metadata and configuration for content collection.

    Attributes:
        id: Unique identifier (UUID)
        telegram_id: Telegram's internal channel ID
        username: Channel username (without @)
        title: Channel display name
        description: Channel description/about text
        subscriber_count: Number of subscribers
        photo_url: URL to channel photo
        invite_link: Channel invite link
        is_active: Whether channel is currently being monitored
        last_collected_message_id: Last Telegram message ID collected from this channel
        last_collected_at: Timestamp of the last content collection
        created_at: When channel was added
        updated_at: When channel was last modified
    """

    __tablename__ = "channels"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    subscriber_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    photo_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    invite_link: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_collected_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Last Telegram message ID collected from this channel",
    )
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last content collection",
    )

    # Relationships
    health_logs: Mapped[list["ChannelHealthLog"]] = relationship(
        "ChannelHealthLog",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, username=@{self.username}, title={self.title})>"


class ChannelHealthLog(Base, UUIDPrimaryKeyMixin):
    """Model for tracking channel health check history.

    Records each health check performed on a channel, including
    success/failure status and any error messages.

    Attributes:
        id: Unique identifier (UUID)
        channel_id: Reference to the checked channel
        status: Health status result (healthy, rate_limited, etc.)
        error_message: Optional error description if unhealthy
        checked_at: When the health check was performed
    """

    __tablename__ = "channel_health_logs"

    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    channel: Mapped["Channel"] = relationship(
        "Channel",
        back_populates="health_logs",
    )

    def __repr__(self) -> str:
        return f"<ChannelHealthLog(id={self.id}, channel_id={self.channel_id}, status={self.status})>"


class Post(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a Telegram post/message from a monitored channel.

    Stores post metadata including timestamps, forwarding information,
    and links to content and media.

    Attributes:
        id: Unique identifier (UUID)
        channel_id: Reference to the source channel
        telegram_message_id: Telegram's message ID within the channel
        published_at: When the post was originally published
        is_forwarded: Whether this is a forwarded message
        forward_from_channel_id: Original channel if forwarded
        forward_from_message_id: Original message ID if forwarded
        created_at: When record was created
        updated_at: When record was last modified
    """

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint(
            "channel_id",
            "telegram_message_id",
            name="uq_posts_channel_message",
        ),
        Index("ix_posts_published_at", "published_at"),
    )

    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_forwarded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    forward_from_channel_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    forward_from_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Relationships
    channel: Mapped["Channel"] = relationship(
        "Channel",
        backref="posts",
    )
    content: Mapped[Optional["PostContent"]] = relationship(
        "PostContent",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
    )
    media: Mapped[list["PostMedia"]] = relationship(
        "PostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    engagement_metrics: Mapped[list["EngagementMetrics"]] = relationship(
        "EngagementMetrics",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    enrichment: Mapped["PostEnrichment | None"] = relationship(
        "PostEnrichment",
        back_populates="post",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, channel_id={self.channel_id}, msg_id={self.telegram_message_id})>"


class PostContent(Base, UUIDPrimaryKeyMixin):
    """Model storing the text content of a post.

    Separated from Post to support large text content and
    language-specific processing.

    Attributes:
        id: Unique identifier (UUID)
        post_id: Reference to the parent post
        text_content: The full text content of the post
        language: Detected language code (e.g., 'ru', 'en', 'uk')
        created_at: When record was created
    """

    __tablename__ = "post_content"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    text_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="content",
    )

    def __repr__(self) -> str:
        preview = (self.text_content or "")[:50]
        return f"<PostContent(id={self.id}, post_id={self.post_id}, preview='{preview}...')>"


class PostMedia(Base, UUIDPrimaryKeyMixin):
    """Model storing media attachments for posts.

    A post can have multiple media items (photo album, video, etc.).

    Attributes:
        id: Unique identifier (UUID)
        post_id: Reference to the parent post
        media_type: Type of media (photo, video, document, etc.)
        file_id: Telegram file ID for downloading
        file_size: Size in bytes
        mime_type: MIME type of the file
        duration: Duration in seconds (for video/audio)
        width: Width in pixels (for photo/video)
        height: Height in pixels (for photo/video)
        thumbnail_file_id: Telegram file ID for thumbnail
        created_at: When record was created
    """

    __tablename__ = "post_media"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    file_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    duration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    thumbnail_file_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="media",
    )

    def __repr__(self) -> str:
        return f"<PostMedia(id={self.id}, post_id={self.post_id}, type={self.media_type})>"


class EngagementMetrics(Base, UUIDPrimaryKeyMixin):
    """Model storing engagement metrics for a post at a point in time.

    Metrics are collected periodically to track engagement changes.
    Each record represents a snapshot of engagement at collected_at time.

    Attributes:
        id: Unique identifier (UUID)
        post_id: Reference to the measured post
        view_count: Number of views
        forward_count: Number of forwards/shares
        reply_count: Number of replies/comments
        reaction_score: Calculated weighted reaction score
        relative_engagement: Engagement normalized by subscriber count
        collected_at: When metrics were collected
    """

    __tablename__ = "engagement_metrics"
    __table_args__ = (
        Index("ix_engagement_metrics_collected_at", "collected_at"),
    )

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    forward_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reply_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reaction_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    relative_engagement: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="engagement_metrics",
    )
    reactions: Mapped[list["ReactionCount"]] = relationship(
        "ReactionCount",
        back_populates="engagement_metrics",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<EngagementMetrics(id={self.id}, post_id={self.post_id}, views={self.view_count})>"


class ReactionCount(Base, UUIDPrimaryKeyMixin):
    """Model storing individual emoji reaction counts.

    Stores each emoji type separately for detailed reaction analysis.
    Each engagement_metrics record can have multiple reaction types.

    Attributes:
        id: Unique identifier (UUID)
        engagement_metrics_id: Reference to parent metrics record
        emoji: Emoji identifier (e.g., 'thumbs_up', 'heart', 'fire')
        count: Number of this reaction type
    """

    __tablename__ = "reaction_counts"
    __table_args__ = (
        UniqueConstraint(
            "engagement_metrics_id",
            "emoji",
            name="uq_reaction_counts_metrics_emoji",
        ),
        Index("ix_reaction_counts_emoji", "emoji"),
    )

    engagement_metrics_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_metrics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    engagement_metrics: Mapped["EngagementMetrics"] = relationship(
        "EngagementMetrics",
        back_populates="reactions",
    )

    def __repr__(self) -> str:
        return f"<ReactionCount(id={self.id}, emoji={self.emoji}, count={self.count})>"


class SavedTopic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model storing user-saved topic configurations.

    Allows users to save search configurations for quick access.

    Attributes:
        id: Unique identifier (UUID)
        name: Unique name for the saved topic
        description: Optional description of the topic
        keywords: Comma-separated or JSON list of keywords
        search_config: JSON configuration for search parameters
        is_active: Whether the topic is currently active
        created_at: When topic was created
        updated_at: When topic was last modified
    """

    __tablename__ = "saved_topics"

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    keywords: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    search_config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SavedTopic(id={self.id}, name={self.name})>"


class TopicTemplate(Base, UUIDPrimaryKeyMixin):
    """Model storing pre-built topic templates.

    Provides common search configurations for quick use.

    Attributes:
        id: Unique identifier (UUID)
        name: Unique name for the template
        description: Description of what the template searches for
        keywords: Pre-configured keywords for the template
        category: Category for grouping templates (politics, tech, etc.)
        is_builtin: Whether this is a system-provided template
        created_at: When template was created
    """

    __tablename__ = "topic_templates"

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    keywords: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TopicTemplate(id={self.id}, name={self.name}, category={self.category})>"


class BotSettings(Base, UUIDPrimaryKeyMixin):
    """Model storing bot configuration as key-value pairs.

    Simple key-value store for bot configuration options.

    Attributes:
        id: Unique identifier (UUID)
        key: Unique setting key
        value: Setting value (JSON or plain text)
        updated_at: When setting was last modified
    """

    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BotSettings(id={self.id}, key={self.key})>"


class PostEnrichment(Base, UUIDPrimaryKeyMixin):
    """Model storing LLM-enriched metadata for posts.

    Stores extracted keywords, categories, sentiment, and entities
    from LLM analysis of post content. Enables RAG-like retrieval
    using keyword arrays instead of vector embeddings.

    WS-5.2: Database Schema for Post Enrichment

    Attributes:
        id: Unique identifier (UUID)
        post_id: Reference to the parent post (one-to-one)
        explicit_keywords: Keywords directly present in the text
        implicit_keywords: Related concepts NOT in text (key for RAG)
        category: Primary topic category (politics, tech, etc.)
        sentiment: Sentiment classification (positive/negative/neutral)
        entities: Named entities as JSONB (people, organizations, places)
        model_used: LLM model identifier used for enrichment
        token_count: Total tokens used in the enrichment request
        processing_time_ms: Time taken for LLM processing
        enriched_at: When the enrichment was performed
    """

    __tablename__ = "post_enrichments"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    explicit_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    implicit_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    sentiment: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    entities: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="enrichment",
    )

    def __repr__(self) -> str:
        return f"<PostEnrichment(id={self.id}, post_id={self.post_id}, category={self.category})>"


class LLMUsageLog(Base, UUIDPrimaryKeyMixin):
    """Model storing LLM API usage logs for cost tracking.

    Records token usage and estimated costs for LLM API calls.
    Enables monitoring of usage patterns and cost management.

    WS-5.2: Database Schema for Post Enrichment

    Attributes:
        id: Unique identifier (UUID)
        model: LLM model identifier used
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the response
        total_tokens: Total tokens used (prompt + completion)
        estimated_cost_usd: Estimated cost in USD
        task_name: Name of the task/operation
        posts_processed: Number of posts processed in this call
        created_at: When the API call was made
    """

    __tablename__ = "llm_usage_logs"

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    task_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    posts_processed: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<LLMUsageLog(id={self.id}, model={self.model}, tokens={self.total_tokens})>"

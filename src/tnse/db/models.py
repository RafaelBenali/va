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

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
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

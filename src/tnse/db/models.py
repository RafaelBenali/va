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
    ForeignKey,
    Integer,
    String,
    Text,
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

"""initial schema - channels posts engagement topics

Revision ID: 9bab40e1a6eb
Revises:
Create Date: 2025-12-25 22:42:29.536057

This migration creates the initial database schema for TNSE including:
- channels and channel_health_logs tables
- posts, post_content, and post_media tables
- engagement_metrics and reaction_counts tables
- saved_topics, topic_templates, and bot_settings tables
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9bab40e1a6eb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # =========================================================================
    # Channels
    # =========================================================================
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subscriber_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_url", sa.String(1024), nullable=True),
        sa.Column("invite_link", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_channels_telegram_id", "channels", ["telegram_id"])
    op.create_index("ix_channels_username", "channels", ["username"])

    # Channel Health Logs
    op.create_table(
        "channel_health_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_channel_health_logs_channel_id", "channel_health_logs", ["channel_id"])

    # =========================================================================
    # Posts
    # =========================================================================
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_forwarded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("forward_from_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("forward_from_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("channel_id", "telegram_message_id", name="uq_posts_channel_message"),
    )
    op.create_index("ix_posts_channel_id", "posts", ["channel_id"])
    op.create_index("ix_posts_telegram_message_id", "posts", ["telegram_message_id"])
    op.create_index("ix_posts_published_at", "posts", ["published_at"])

    # Post Content
    op.create_table(
        "post_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_post_content_post_id", "post_content", ["post_id"])

    # Post Media
    op.create_table(
        "post_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("file_id", sa.String(255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_file_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_post_media_post_id", "post_media", ["post_id"])

    # =========================================================================
    # Engagement Metrics
    # =========================================================================
    op.create_table(
        "engagement_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forward_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reaction_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("relative_engagement", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_engagement_metrics_post_id", "engagement_metrics", ["post_id"])
    op.create_index("ix_engagement_metrics_collected_at", "engagement_metrics", ["collected_at"])

    # Reaction Counts
    op.create_table(
        "reaction_counts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("engagement_metrics_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("engagement_metrics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("emoji", sa.String(50), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("engagement_metrics_id", "emoji", name="uq_reaction_counts_metrics_emoji"),
    )
    op.create_index("ix_reaction_counts_engagement_metrics_id", "reaction_counts", ["engagement_metrics_id"])
    op.create_index("ix_reaction_counts_emoji", "reaction_counts", ["emoji"])

    # =========================================================================
    # Saved Topics and Templates
    # =========================================================================
    op.create_table(
        "saved_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("search_config", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_saved_topics_name", "saved_topics", ["name"])

    # Topic Templates
    op.create_table(
        "topic_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_topic_templates_name", "topic_templates", ["name"])
    op.create_index("ix_topic_templates_category", "topic_templates", ["category"])

    # Bot Settings
    op.create_table(
        "bot_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_bot_settings_key", "bot_settings", ["key"])


def downgrade() -> None:
    """Drop all tables in reverse order."""

    op.drop_table("bot_settings")
    op.drop_table("topic_templates")
    op.drop_table("saved_topics")
    op.drop_table("reaction_counts")
    op.drop_table("engagement_metrics")
    op.drop_table("post_media")
    op.drop_table("post_content")
    op.drop_table("posts")
    op.drop_table("channel_health_logs")
    op.drop_table("channels")

    # Extensions are not dropped to avoid affecting other databases

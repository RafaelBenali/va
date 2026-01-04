"""Add post_enrichments and llm_usage_logs tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-05

WS-5.2: Database Schema for Post Enrichment

This migration creates:
1. post_enrichments table for LLM-extracted metadata
2. llm_usage_logs table for API cost tracking
3. GIN indexes on keyword arrays for efficient array overlap queries
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create post_enrichments and llm_usage_logs tables with indexes."""
    # Create post_enrichments table
    op.create_table(
        "post_enrichments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "explicit_keywords",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "implicit_keywords",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "sentiment",
            sa.String(20),
            nullable=True,
        ),
        sa.Column(
            "entities",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "model_used",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "processing_time_ms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "enriched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes for post_enrichments
    op.create_index(
        "ix_post_enrichments_post_id",
        "post_enrichments",
        ["post_id"],
    )
    op.create_index(
        "ix_post_enrichments_category",
        "post_enrichments",
        ["category"],
    )

    # Create GIN indexes for keyword array searches (for efficient && operator queries)
    op.create_index(
        "ix_post_enrichments_explicit_keywords_gin",
        "post_enrichments",
        ["explicit_keywords"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_post_enrichments_implicit_keywords_gin",
        "post_enrichments",
        ["implicit_keywords"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_post_enrichments_entities_gin",
        "post_enrichments",
        ["entities"],
        postgresql_using="gin",
    )

    # Create llm_usage_logs table
    op.create_table(
        "llm_usage_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "model",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(10, 6),
            nullable=True,
        ),
        sa.Column(
            "task_name",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "posts_processed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes for llm_usage_logs
    op.create_index(
        "ix_llm_usage_logs_created_at",
        "llm_usage_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_llm_usage_logs_model",
        "llm_usage_logs",
        ["model"],
    )


def downgrade() -> None:
    """Drop post_enrichments and llm_usage_logs tables."""
    # Drop llm_usage_logs indexes and table
    op.drop_index("ix_llm_usage_logs_model", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_created_at", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")

    # Drop post_enrichments indexes and table
    op.drop_index("ix_post_enrichments_entities_gin", table_name="post_enrichments")
    op.drop_index("ix_post_enrichments_implicit_keywords_gin", table_name="post_enrichments")
    op.drop_index("ix_post_enrichments_explicit_keywords_gin", table_name="post_enrichments")
    op.drop_index("ix_post_enrichments_category", table_name="post_enrichments")
    op.drop_index("ix_post_enrichments_post_id", table_name="post_enrichments")
    op.drop_table("post_enrichments")

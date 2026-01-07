"""Add is_media_only column to post_content table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-07

Fix for Issue 1: LLM enrichment loops on media-only posts.
This migration adds an is_media_only boolean column to the post_content table
to mark posts that have no enrichable text content, preventing them from
being repeatedly picked up by the enrichment batch job.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_media_only column to post_content table."""
    # Add the is_media_only column with default False
    op.add_column(
        "post_content",
        sa.Column(
            "is_media_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True if post has no enrichable text content (media-only)",
        ),
    )

    # Create index for efficient filtering of media-only posts
    op.create_index(
        "ix_post_content_is_media_only",
        "post_content",
        ["is_media_only"],
    )

    # Update existing records: mark as media-only where text_content is NULL or empty
    op.execute("""
        UPDATE post_content
        SET is_media_only = true
        WHERE text_content IS NULL
           OR TRIM(text_content) = ''
    """)


def downgrade() -> None:
    """Remove is_media_only column from post_content table."""
    op.drop_index("ix_post_content_is_media_only", table_name="post_content")
    op.drop_column("post_content", "is_media_only")

"""add last_collected_message_id to channels

Revision ID: a1b2c3d4e5f6
Revises: 9bab40e1a6eb
Create Date: 2026-01-04

WS-8.2: Resume-from-Last-Point Tracking

This migration adds the last_collected_message_id column to the channels table
to track the last message ID collected from each channel. This enables
resume-from-last-point functionality, avoiding re-fetching of already
collected messages.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9bab40e1a6eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_collected_message_id column to channels table."""
    op.add_column(
        "channels",
        sa.Column(
            "last_collected_message_id",
            sa.BigInteger(),
            nullable=True,
            comment="Last Telegram message ID collected from this channel",
        ),
    )
    op.add_column(
        "channels",
        sa.Column(
            "last_collected_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of the last content collection",
        ),
    )
    # Add index for efficient lookups during collection
    op.create_index(
        "ix_channels_last_collected_message_id",
        "channels",
        ["last_collected_message_id"],
    )


def downgrade() -> None:
    """Remove last_collected_message_id column from channels table."""
    op.drop_index("ix_channels_last_collected_message_id", table_name="channels")
    op.drop_column("channels", "last_collected_at")
    op.drop_column("channels", "last_collected_message_id")

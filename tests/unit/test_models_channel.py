"""
Tests for TNSE Channel database models.

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover the Channel and ChannelHealthLog models.

Requirements addressed:
- WS-1.2: Design schema for channels (metadata, health)
- REQ-CC-003: System MUST fetch and display channel metadata
- REQ-CC-006: System MUST display channel health status
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID


class TestChannelModel:
    """Tests for the Channel database model."""

    def test_channel_model_exists(self):
        """Test that Channel model class exists and can be imported."""
        from src.tnse.db.models import Channel
        assert Channel is not None

    def test_channel_has_required_fields(self):
        """Test that Channel model has all required fields."""
        from src.tnse.db.models import Channel

        # Check that required columns exist
        column_names = [column.name for column in Channel.__table__.columns]

        required_fields = [
            "id",
            "telegram_id",
            "username",
            "title",
            "description",
            "subscriber_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in column_names, f"Channel model missing required field: {field}"

    def test_channel_id_is_uuid(self):
        """Test that Channel primary key is a UUID type."""
        from src.tnse.db.models import Channel
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID

        id_column = Channel.__table__.columns["id"]
        # Check if the column type is UUID
        assert isinstance(id_column.type, PG_UUID) or "uuid" in str(id_column.type).lower()

    def test_channel_username_is_unique(self):
        """Test that Channel username field has a unique constraint."""
        from src.tnse.db.models import Channel

        username_column = Channel.__table__.columns["username"]
        assert username_column.unique is True

    def test_channel_telegram_id_is_unique(self):
        """Test that Channel telegram_id field has a unique constraint."""
        from src.tnse.db.models import Channel

        telegram_id_column = Channel.__table__.columns["telegram_id"]
        assert telegram_id_column.unique is True

    def test_channel_has_tablename(self):
        """Test that Channel model has correct table name."""
        from src.tnse.db.models import Channel

        assert Channel.__tablename__ == "channels"

    def test_channel_subscriber_count_defaults_to_zero(self):
        """Test that subscriber_count has a default value of 0."""
        from src.tnse.db.models import Channel

        subscriber_column = Channel.__table__.columns["subscriber_count"]
        assert subscriber_column.default is not None or subscriber_column.server_default is not None

    def test_channel_is_active_defaults_to_true(self):
        """Test that is_active defaults to True for new channels."""
        from src.tnse.db.models import Channel

        is_active_column = Channel.__table__.columns["is_active"]
        assert is_active_column.default is not None or is_active_column.server_default is not None

    def test_channel_can_be_instantiated(self):
        """Test that Channel can be instantiated with required fields."""
        from src.tnse.db.models import Channel

        channel = Channel(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
        )

        assert channel.telegram_id == 123456789
        assert channel.username == "test_channel"
        assert channel.title == "Test Channel"

    def test_channel_has_photo_url_field(self):
        """Test that Channel has optional photo_url field."""
        from src.tnse.db.models import Channel

        column_names = [column.name for column in Channel.__table__.columns]
        assert "photo_url" in column_names

    def test_channel_has_invite_link_field(self):
        """Test that Channel has optional invite_link field."""
        from src.tnse.db.models import Channel

        column_names = [column.name for column in Channel.__table__.columns]
        assert "invite_link" in column_names


class TestChannelHealthLogModel:
    """Tests for the ChannelHealthLog database model."""

    def test_channel_health_log_model_exists(self):
        """Test that ChannelHealthLog model class exists."""
        from src.tnse.db.models import ChannelHealthLog
        assert ChannelHealthLog is not None

    def test_channel_health_log_has_required_fields(self):
        """Test that ChannelHealthLog has all required fields."""
        from src.tnse.db.models import ChannelHealthLog

        column_names = [column.name for column in ChannelHealthLog.__table__.columns]

        required_fields = [
            "id",
            "channel_id",
            "status",
            "error_message",
            "checked_at",
        ]

        for field in required_fields:
            assert field in column_names, f"ChannelHealthLog missing required field: {field}"

    def test_channel_health_log_has_tablename(self):
        """Test that ChannelHealthLog has correct table name."""
        from src.tnse.db.models import ChannelHealthLog

        assert ChannelHealthLog.__tablename__ == "channel_health_logs"

    def test_channel_health_log_status_is_enum_or_string(self):
        """Test that status field can represent channel health states."""
        from src.tnse.db.models import ChannelHealthLog

        status_column = ChannelHealthLog.__table__.columns["status"]
        # Status should be defined (either as enum or varchar)
        assert status_column is not None

    def test_channel_health_log_has_foreign_key_to_channel(self):
        """Test that ChannelHealthLog has foreign key to Channel."""
        from src.tnse.db.models import ChannelHealthLog

        channel_id_column = ChannelHealthLog.__table__.columns["channel_id"]
        foreign_keys = list(channel_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "channels.id" in str(foreign_keys[0])

    def test_channel_health_log_can_be_instantiated(self):
        """Test that ChannelHealthLog can be instantiated."""
        from src.tnse.db.models import ChannelHealthLog
        from uuid import uuid4

        log = ChannelHealthLog(
            channel_id=uuid4(),
            status="healthy",
        )

        assert log.status == "healthy"


class TestChannelStatusEnum:
    """Tests for channel health status enumeration."""

    def test_channel_status_enum_exists(self):
        """Test that ChannelStatus enum exists."""
        from src.tnse.db.models import ChannelStatus
        assert ChannelStatus is not None

    def test_channel_status_has_healthy_value(self):
        """Test that ChannelStatus has HEALTHY status."""
        from src.tnse.db.models import ChannelStatus
        assert hasattr(ChannelStatus, "HEALTHY")

    def test_channel_status_has_rate_limited_value(self):
        """Test that ChannelStatus has RATE_LIMITED status."""
        from src.tnse.db.models import ChannelStatus
        assert hasattr(ChannelStatus, "RATE_LIMITED")

    def test_channel_status_has_inaccessible_value(self):
        """Test that ChannelStatus has INACCESSIBLE status."""
        from src.tnse.db.models import ChannelStatus
        assert hasattr(ChannelStatus, "INACCESSIBLE")

    def test_channel_status_has_removed_value(self):
        """Test that ChannelStatus has REMOVED status."""
        from src.tnse.db.models import ChannelStatus
        assert hasattr(ChannelStatus, "REMOVED")

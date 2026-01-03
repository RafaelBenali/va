"""
Integration Tests for Resume-from-Last-Point Tracking (WS-8.2)

These tests verify the end-to-end behavior of resume tracking:
- First collection fetches all messages in 24-hour window
- Subsequent collections only fetch new messages since last run
- Database stores last_collected_message_id per channel
- Collection time significantly reduced on repeat runs

Work Stream: WS-8.2 - Resume-from-Last-Point Tracking
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestResumeTrackingIntegration:
    """Integration tests for resume-from-last-point tracking."""

    @pytest.fixture
    def mock_telegram_client(self):
        """Create a mock Telegram client."""
        from src.tnse.telegram.client import TelegramClient

        return AsyncMock(spec=TelegramClient)

    @pytest.fixture
    def collector(self, mock_telegram_client):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector

        return ContentCollector(telegram_client=mock_telegram_client)

    def create_message(self, message_id: int, hours_ago: float, text: str):
        """Helper to create a MessageInfo for testing."""
        from src.tnse.telegram.client import MessageInfo

        return MessageInfo(
            message_id=message_id,
            channel_id=123,
            text=text,
            date=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        )

    @pytest.mark.asyncio
    async def test_first_collection_then_second_collection_workflow(
        self, collector, mock_telegram_client
    ):
        """Test complete workflow: first collection followed by second collection.

        This test simulates:
        1. First collection: All messages in 24-hour window are fetched (min_id=0)
        2. Application stores max_message_id as last_collected_message_id
        3. New messages arrive
        4. Second collection: Only new messages are fetched (min_id=previous max)
        """
        channel_uuid = uuid4()
        telegram_channel_id = 123456

        # ===== FIRST COLLECTION =====
        # Initial messages in the channel (simulate first fetch)
        initial_messages = [
            self.create_message(message_id=50, hours_ago=12, text="Old post 1"),
            self.create_message(message_id=60, hours_ago=6, text="Old post 2"),
            self.create_message(message_id=100, hours_ago=2, text="Recent post 1"),
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=initial_messages)

        # First collection with min_id=0 (no previous collection)
        first_result = await collector.collect_channel_messages(
            telegram_channel_id=telegram_channel_id,
            channel_uuid=channel_uuid,
            min_id=0,  # First collection
        )

        # Verify first collection results
        assert first_result["count"] == 3
        assert first_result["max_message_id"] == 100
        assert len(first_result["messages"]) == 3

        # Verify API was called with min_id=0
        mock_telegram_client.get_messages.assert_called_once()
        call_kwargs = mock_telegram_client.get_messages.call_args.kwargs
        assert call_kwargs["min_id"] == 0

        # ===== SIMULATE TIME PASSING AND NEW MESSAGES =====
        # The application would store last_collected_message_id = 100

        # New messages arrive (only messages with ID > 100)
        new_messages = [
            self.create_message(message_id=150, hours_ago=1, text="New post 1"),
            self.create_message(message_id=200, hours_ago=0.5, text="New post 2"),
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=new_messages)

        # ===== SECOND COLLECTION =====
        # Second collection with min_id=100 (resume from last point)
        second_result = await collector.collect_channel_messages(
            telegram_channel_id=telegram_channel_id,
            channel_uuid=channel_uuid,
            min_id=100,  # Resume from last collected message
        )

        # Verify second collection results
        assert second_result["count"] == 2  # Only new messages
        assert second_result["max_message_id"] == 200
        assert len(second_result["messages"]) == 2

        # Verify only new message IDs are in the result
        message_ids = [msg["telegram_message_id"] for msg in second_result["messages"]]
        assert 150 in message_ids
        assert 200 in message_ids
        assert 100 not in message_ids  # Not re-fetched
        assert 60 not in message_ids  # Not re-fetched
        assert 50 not in message_ids  # Not re-fetched

        # Verify API was called with min_id=100
        call_kwargs = mock_telegram_client.get_messages.call_args.kwargs
        assert call_kwargs["min_id"] == 100

    @pytest.mark.asyncio
    async def test_no_new_messages_returns_empty_with_none_max_id(
        self, collector, mock_telegram_client
    ):
        """Test collection when there are no new messages since last run."""
        channel_uuid = uuid4()

        # No new messages since last collection
        mock_telegram_client.get_messages = AsyncMock(return_value=[])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123456,
            channel_uuid=channel_uuid,
            min_id=500,  # High min_id, no messages above this
        )

        # Should return empty result
        assert result["count"] == 0
        assert result["max_message_id"] is None
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_collection_with_gaps_in_message_ids(
        self, collector, mock_telegram_client
    ):
        """Test that gaps in message IDs (deleted messages) are handled correctly."""
        channel_uuid = uuid4()

        # Messages with gaps (some were deleted)
        messages_with_gaps = [
            self.create_message(message_id=100, hours_ago=5, text="Msg 100"),
            # Gap: 101-149 deleted
            self.create_message(message_id=150, hours_ago=3, text="Msg 150"),
            # Gap: 151-299 deleted
            self.create_message(message_id=300, hours_ago=1, text="Msg 300"),
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=messages_with_gaps)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123456,
            channel_uuid=channel_uuid,
            min_id=50,
        )

        # Should correctly identify max message ID despite gaps
        assert result["count"] == 3
        assert result["max_message_id"] == 300

    @pytest.mark.asyncio
    async def test_collection_respects_24_hour_window(
        self, collector, mock_telegram_client
    ):
        """Test that only messages within 24-hour window are collected."""
        channel_uuid = uuid4()

        # Mix of messages: some within window, some outside
        messages = [
            self.create_message(message_id=100, hours_ago=48, text="Old (outside)"),
            self.create_message(message_id=150, hours_ago=12, text="Within window"),
            self.create_message(message_id=200, hours_ago=36, text="Old (outside)"),
            self.create_message(message_id=250, hours_ago=6, text="Within window"),
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=messages)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123456,
            channel_uuid=channel_uuid,
            min_id=0,
        )

        # Only messages within 24-hour window should be collected
        assert result["count"] == 2
        message_ids = [msg["telegram_message_id"] for msg in result["messages"]]
        assert 150 in message_ids
        assert 250 in message_ids
        assert 100 not in message_ids  # Outside 24-hour window
        assert 200 not in message_ids  # Outside 24-hour window

        # Max message ID should still be the highest from collected messages
        assert result["max_message_id"] == 250


class TestResumeTrackingDatabaseIntegration:
    """Tests for database integration with resume tracking.

    These tests verify that the Channel model correctly stores
    and retrieves the last_collected_message_id field.
    """

    def test_channel_model_stores_last_collected_message_id(self):
        """Test that Channel model can store last_collected_message_id."""
        from src.tnse.db.models import Channel

        # Verify the column exists and is correct type
        column = Channel.__table__.columns.get("last_collected_message_id")
        assert column is not None
        assert column.nullable is True

        # Verify it's a BigInteger (for large Telegram message IDs)
        from sqlalchemy import BigInteger

        assert isinstance(column.type, BigInteger)

    def test_channel_model_stores_last_collected_at(self):
        """Test that Channel model can store last_collected_at timestamp."""
        from src.tnse.db.models import Channel

        column = Channel.__table__.columns.get("last_collected_at")
        assert column is not None
        assert column.nullable is True

        # Verify it's a DateTime with timezone
        from sqlalchemy import DateTime

        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True


class TestResumeTrackingPerformance:
    """Performance-related tests for resume tracking."""

    @pytest.fixture
    def mock_telegram_client(self):
        """Create a mock Telegram client."""
        from src.tnse.telegram.client import TelegramClient

        return AsyncMock(spec=TelegramClient)

    @pytest.fixture
    def collector(self, mock_telegram_client):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector

        return ContentCollector(telegram_client=mock_telegram_client)

    @pytest.mark.asyncio
    async def test_subsequent_collection_should_process_fewer_messages(
        self, collector, mock_telegram_client
    ):
        """Test that subsequent collections process fewer messages than first.

        This validates the efficiency gain from resume tracking.
        """
        from src.tnse.telegram.client import MessageInfo

        channel_uuid = uuid4()
        now = datetime.now(timezone.utc)

        # First collection: Many messages
        first_batch = [
            MessageInfo(
                message_id=i,
                channel_id=123,
                text=f"Message {i}",
                date=now - timedelta(hours=i % 24),
            )
            for i in range(1, 101)  # 100 messages
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=first_batch)

        first_result = await collector.collect_channel_messages(
            telegram_channel_id=123456,
            channel_uuid=channel_uuid,
            min_id=0,
        )

        first_count = first_result["count"]

        # Second collection: Only a few new messages
        second_batch = [
            MessageInfo(
                message_id=i,
                channel_id=123,
                text=f"New Message {i}",
                date=now - timedelta(hours=0.5),
            )
            for i in range(101, 106)  # 5 new messages
        ]
        mock_telegram_client.get_messages = AsyncMock(return_value=second_batch)

        second_result = await collector.collect_channel_messages(
            telegram_channel_id=123456,
            channel_uuid=channel_uuid,
            min_id=100,  # Resume from last point
        )

        second_count = second_result["count"]

        # Second collection should process significantly fewer messages
        assert second_count < first_count
        assert second_count == 5  # Only new messages

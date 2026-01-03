"""
Tests for Resume-from-Last-Point Tracking (WS-8.2)

Following TDD methodology: tests for tracking last collected message ID
per channel to avoid re-fetching same content.

Work Stream: WS-8.2 - Resume-from-Last-Point Tracking

Requirements addressed:
- Track last collected message ID per channel
- Avoid re-fetching already collected messages
- Update last_collected_message_id after successful collection
- Handle edge cases: channel reset, message deletion, gaps
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestChannelModelResumeFields:
    """Tests for Channel model resume tracking fields."""

    def test_channel_has_last_collected_message_id_field(self):
        """Test that Channel model has last_collected_message_id field."""
        from src.tnse.db.models import Channel

        # Check that the column exists on the model
        assert hasattr(Channel, "last_collected_message_id")

    def test_channel_has_last_collected_at_field(self):
        """Test that Channel model has last_collected_at field."""
        from src.tnse.db.models import Channel

        # Check that the column exists on the model
        assert hasattr(Channel, "last_collected_at")

    def test_last_collected_message_id_is_nullable(self):
        """Test that last_collected_message_id allows None (for first collection)."""
        from src.tnse.db.models import Channel

        # The column should allow null values
        column = Channel.__table__.columns.get("last_collected_message_id")
        assert column is not None
        assert column.nullable is True

    def test_last_collected_at_is_nullable(self):
        """Test that last_collected_at allows None (for first collection)."""
        from src.tnse.db.models import Channel

        column = Channel.__table__.columns.get("last_collected_at")
        assert column is not None
        assert column.nullable is True


class TestContentCollectorResumeTracking:
    """Tests for ContentCollector resume tracking functionality."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = AsyncMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_collector_has_min_id_parameter_support(self, collector):
        """Test that collector supports min_id parameter."""
        # ContentCollector should accept min_id in collect_channel_messages
        import inspect

        from src.tnse.pipeline.collector import ContentCollector

        sig = inspect.signature(ContentCollector.collect_channel_messages)
        params = sig.parameters

        assert "min_id" in params, "collect_channel_messages should accept min_id parameter"

    @pytest.mark.asyncio
    async def test_collect_with_min_id_passes_to_telegram_client(self, collector):
        """Test that min_id is passed to Telegram client."""
        from src.tnse.telegram.client import MessageInfo

        # Setup mock to return messages
        now = datetime.now(timezone.utc)
        message = MessageInfo(
            message_id=100,
            channel_id=123,
            text="New message",
            date=now - timedelta(hours=1),
        )
        collector.telegram_client.get_messages = AsyncMock(return_value=[message])

        # Call with min_id
        await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=50,
        )

        # Verify min_id was passed to get_messages
        collector.telegram_client.get_messages.assert_called_once()
        call_kwargs = collector.telegram_client.get_messages.call_args.kwargs
        assert call_kwargs.get("min_id") == 50

    @pytest.mark.asyncio
    async def test_collect_without_min_id_uses_zero(self, collector):
        """Test that default min_id is 0 (fetch all)."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        message = MessageInfo(
            message_id=100,
            channel_id=123,
            text="Message",
            date=now - timedelta(hours=1),
        )
        collector.telegram_client.get_messages = AsyncMock(return_value=[message])

        # Call without min_id
        await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # Verify min_id defaults to 0
        call_kwargs = collector.telegram_client.get_messages.call_args.kwargs
        assert call_kwargs.get("min_id", 0) == 0

    @pytest.mark.asyncio
    async def test_collect_returns_max_message_id(self, collector):
        """Test that collection returns the max message ID from collected messages."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        messages = [
            MessageInfo(
                message_id=100,
                channel_id=123,
                text="Message 1",
                date=now - timedelta(hours=1),
            ),
            MessageInfo(
                message_id=150,
                channel_id=123,
                text="Message 2",
                date=now - timedelta(minutes=30),
            ),
            MessageInfo(
                message_id=120,
                channel_id=123,
                text="Message 3",
                date=now - timedelta(hours=2),
            ),
        ]
        collector.telegram_client.get_messages = AsyncMock(return_value=messages)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # Result should include max_message_id or be accessible somehow
        assert "max_message_id" in result or hasattr(result, "max_message_id")
        # The max should be 150
        if isinstance(result, dict):
            assert result.get("max_message_id") == 150
        else:
            assert result.max_message_id == 150

    @pytest.mark.asyncio
    async def test_collect_with_no_messages_returns_none_max_id(self, collector):
        """Test that collection with no messages returns None for max_message_id."""
        collector.telegram_client.get_messages = AsyncMock(return_value=[])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # No messages means no max message ID
        if isinstance(result, dict):
            assert result.get("max_message_id") is None
        else:
            assert result.max_message_id is None


class TestResumeTrackingEdgeCases:
    """Tests for edge cases in resume tracking."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = AsyncMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    @pytest.mark.asyncio
    async def test_messages_with_gaps_handled_correctly(self, collector):
        """Test that message ID gaps are handled gracefully."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        # Simulate gap in message IDs (some messages deleted)
        messages = [
            MessageInfo(
                message_id=100,
                channel_id=123,
                text="Message 1",
                date=now - timedelta(hours=1),
            ),
            # Gap: messages 101-149 missing/deleted
            MessageInfo(
                message_id=150,
                channel_id=123,
                text="Message 2",
                date=now - timedelta(minutes=30),
            ),
            # Another gap: 151-199 missing
            MessageInfo(
                message_id=200,
                channel_id=123,
                text="Message 3",
                date=now - timedelta(minutes=10),
            ),
        ]
        collector.telegram_client.get_messages = AsyncMock(return_value=messages)

        # Should not crash and should return max ID
        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=99,
        )

        # Should successfully collect all 3 messages
        if isinstance(result, dict):
            assert result.get("max_message_id") == 200
            messages_data = result.get("messages", result.get("collected", []))
            assert len(messages_data) == 3
        else:
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_min_id_higher_than_existing_returns_empty(self, collector):
        """Test that min_id higher than existing messages returns empty."""
        # Telegram API returns messages with ID > min_id
        # If min_id is higher than all existing messages, we get empty list
        collector.telegram_client.get_messages = AsyncMock(return_value=[])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=9999999,
        )

        # Should handle gracefully
        if isinstance(result, dict):
            assert result.get("max_message_id") is None
            messages_data = result.get("messages", result.get("collected", []))
            assert len(messages_data) == 0
        else:
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_negative_min_id_treated_as_zero(self, collector):
        """Test that negative min_id is treated as 0 (fetch all)."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        message = MessageInfo(
            message_id=100,
            channel_id=123,
            text="Message",
            date=now - timedelta(hours=1),
        )
        collector.telegram_client.get_messages = AsyncMock(return_value=[message])

        # Negative min_id should be treated as 0
        await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=-5,
        )

        # Should pass 0 to Telegram API (negative IDs don't make sense)
        call_kwargs = collector.telegram_client.get_messages.call_args.kwargs
        assert call_kwargs.get("min_id") >= 0


class TestContentCollectorResultFormat:
    """Tests for ContentCollector result format changes for resume tracking."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = AsyncMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    @pytest.mark.asyncio
    async def test_collect_returns_collection_result_with_metadata(self, collector):
        """Test that collect returns a result object with metadata."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        message = MessageInfo(
            message_id=100,
            channel_id=123,
            text="Test message",
            date=now - timedelta(hours=1),
        )
        collector.telegram_client.get_messages = AsyncMock(return_value=[message])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # Result should be a dict with messages and metadata
        assert isinstance(result, dict)
        assert "messages" in result or "collected" in result
        assert "max_message_id" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_collect_result_includes_message_count(self, collector):
        """Test that result includes count of collected messages."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        messages = [
            MessageInfo(
                message_id=i,
                channel_id=123,
                text=f"Message {i}",
                date=now - timedelta(hours=1),
            )
            for i in range(5)
        ]
        collector.telegram_client.get_messages = AsyncMock(return_value=messages)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        assert result.get("count") == 5


class TestFirstCollectionVsSubsequentCollection:
    """Tests for first collection vs subsequent collection behavior."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = AsyncMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    @pytest.mark.asyncio
    async def test_first_collection_fetches_all_in_window(self, collector):
        """Test that first collection (min_id=0) fetches all messages in window."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        messages = [
            MessageInfo(
                message_id=100,
                channel_id=123,
                text="Recent",
                date=now - timedelta(hours=1),
            ),
            MessageInfo(
                message_id=50,
                channel_id=123,
                text="Older",
                date=now - timedelta(hours=12),
            ),
            MessageInfo(
                message_id=200,
                channel_id=123,
                text="Newest",
                date=now - timedelta(minutes=30),
            ),
        ]
        collector.telegram_client.get_messages = AsyncMock(return_value=messages)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=0,  # First collection
        )

        # All messages in window should be collected
        messages_data = result.get("messages", result.get("collected", []))
        assert len(messages_data) == 3

    @pytest.mark.asyncio
    async def test_subsequent_collection_uses_min_id(self, collector):
        """Test that subsequent collection uses min_id to skip old messages."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        # Only messages newer than min_id=100 should be returned by API
        messages = [
            MessageInfo(
                message_id=150,
                channel_id=123,
                text="New since last collection",
                date=now - timedelta(minutes=30),
            ),
            MessageInfo(
                message_id=200,
                channel_id=123,
                text="Even newer",
                date=now - timedelta(minutes=10),
            ),
        ]
        collector.telegram_client.get_messages = AsyncMock(return_value=messages)

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
            min_id=100,  # Last collected was 100
        )

        # Only new messages should be collected
        messages_data = result.get("messages", result.get("collected", []))
        assert len(messages_data) == 2
        # Verify min_id was passed to API
        call_kwargs = collector.telegram_client.get_messages.call_args.kwargs
        assert call_kwargs.get("min_id") == 100

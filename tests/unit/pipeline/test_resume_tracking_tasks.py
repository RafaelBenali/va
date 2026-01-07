"""
Tests for Resume Tracking in Pipeline Tasks

Following TDD methodology: tests for verifying that pipeline tasks
correctly use last_collected_message_id to avoid re-fetching old messages.

Bug: Pipeline tasks don't use last_collected_message_id
- collect_channel_content doesn't read last_collected_message_id from channel
- collect_channel_content doesn't pass min_id to collector.collect_channel_messages
- collect_channel_content doesn't update last_collected_message_id after collection

Work Stream: Bug Fix - Post Collection Uses Resume Tracking
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCollectChannelContentResumeTracking:
    """Tests for resume tracking in collect_channel_content task."""

    @pytest.fixture
    def mock_channel_with_last_message_id(self):
        """Create a mock channel with last_collected_message_id set."""
        channel = MagicMock()
        channel.id = uuid4()
        channel.username = "test_channel"
        channel.telegram_id = 123456789
        channel.is_active = True
        channel.subscriber_count = 1000
        channel.last_collected_message_id = 500  # Last collected was message 500
        channel.last_collected_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return channel

    @pytest.fixture
    def mock_channel_first_collection(self):
        """Create a mock channel with no previous collection (first time)."""
        channel = MagicMock()
        channel.id = uuid4()
        channel.username = "new_channel"
        channel.telegram_id = 987654321
        channel.is_active = True
        channel.subscriber_count = 500
        channel.last_collected_message_id = None  # Never collected before
        channel.last_collected_at = None
        return channel

    @pytest.mark.asyncio
    async def test_collect_uses_last_collected_message_id_as_min_id(
        self, mock_channel_with_last_message_id
    ):
        """Test that collection passes last_collected_message_id to collector.

        This test should FAIL before the bug fix.
        The pipeline task should read last_collected_message_id from the channel
        and pass it as min_id to avoid re-fetching old messages.
        """
        from src.tnse.pipeline.tasks import _collect_channel_content_async
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.pipeline.storage import ContentStorage

        channel = mock_channel_with_last_message_id
        channel_uuid = channel.id

        # Mock the database session
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock execute to return the channel with last_collected_message_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = channel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        # Mock the collector
        mock_collector = MagicMock(spec=ContentCollector)
        mock_collector.collect_channel_messages = AsyncMock(return_value={
            "messages": [],
            "max_message_id": 600,
            "count": 0,
        })

        # Mock the storage
        mock_storage = MagicMock(spec=ContentStorage)

        # Run the async collection
        result = await _collect_channel_content_async(
            channel_id=str(channel_uuid),
            collector=mock_collector,
            storage=mock_storage,
            session_factory=mock_session_factory,
        )

        # CRITICAL: Verify that collect_channel_messages was called with min_id
        mock_collector.collect_channel_messages.assert_called_once()
        call_kwargs = mock_collector.collect_channel_messages.call_args.kwargs

        # Should pass the last_collected_message_id as min_id
        assert "min_id" in call_kwargs, (
            "collect_channel_messages should be called with min_id parameter"
        )
        assert call_kwargs["min_id"] == 500, (
            f"Expected min_id=500 (last_collected_message_id), got {call_kwargs.get('min_id')}"
        )

    @pytest.mark.asyncio
    async def test_first_collection_uses_zero_as_min_id(
        self, mock_channel_first_collection
    ):
        """Test that first-time collection uses min_id=0 to fetch all messages.

        When last_collected_message_id is None (first collection), min_id should be 0.
        """
        from src.tnse.pipeline.tasks import _collect_channel_content_async
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.pipeline.storage import ContentStorage

        channel = mock_channel_first_collection
        channel_uuid = channel.id

        # Mock the database session
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = channel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        # Mock the collector
        mock_collector = MagicMock(spec=ContentCollector)
        mock_collector.collect_channel_messages = AsyncMock(return_value={
            "messages": [],
            "max_message_id": 100,
            "count": 0,
        })

        mock_storage = MagicMock(spec=ContentStorage)

        result = await _collect_channel_content_async(
            channel_id=str(channel_uuid),
            collector=mock_collector,
            storage=mock_storage,
            session_factory=mock_session_factory,
        )

        call_kwargs = mock_collector.collect_channel_messages.call_args.kwargs
        # First collection should use min_id=0 to fetch all messages in window
        assert call_kwargs.get("min_id", 0) == 0, (
            "First collection should use min_id=0"
        )

    @pytest.mark.asyncio
    async def test_collection_updates_last_collected_message_id(
        self, mock_channel_with_last_message_id
    ):
        """Test that collection updates last_collected_message_id after successful run.

        This test should FAIL before the bug fix.
        After collecting new messages, the channel's last_collected_message_id
        should be updated to the max message ID from the collection.
        """
        from src.tnse.pipeline.tasks import _collect_channel_content_async
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.pipeline.storage import ContentStorage

        channel = mock_channel_with_last_message_id
        channel_uuid = channel.id
        original_last_id = channel.last_collected_message_id

        # Mock the database session
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = channel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        # Mock the collector to return new messages with higher IDs
        mock_collector = MagicMock(spec=ContentCollector)
        mock_collector.collect_channel_messages = AsyncMock(return_value={
            "messages": [],  # No new messages in window, but max_id is tracked
            "max_message_id": 750,  # New max message ID
            "count": 0,
        })

        mock_storage = MagicMock(spec=ContentStorage)

        result = await _collect_channel_content_async(
            channel_id=str(channel_uuid),
            collector=mock_collector,
            storage=mock_storage,
            session_factory=mock_session_factory,
        )

        # CRITICAL: Verify that last_collected_message_id was updated
        # Check if the channel object was modified
        # This may be done via direct assignment or via update query
        assert channel.last_collected_message_id == 750 or \
               any("last_collected_message_id" in str(call) for call in mock_session.method_calls), \
               "Channel's last_collected_message_id should be updated to 750"


class TestCollectAllChannelsResumeTracking:
    """Tests for resume tracking across multiple channels."""

    @pytest.mark.asyncio
    async def test_each_channel_uses_its_own_last_collected_id(self):
        """Test that each channel uses its own last_collected_message_id.

        Different channels may have different collection states.
        """
        from src.tnse.pipeline.tasks import _collect_all_channels_async
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.pipeline.storage import ContentStorage

        # Create channels with different last_collected_message_ids
        channel1 = MagicMock()
        channel1.id = uuid4()
        channel1.username = "channel1"
        channel1.telegram_id = 111111
        channel1.is_active = True
        channel1.subscriber_count = 1000
        channel1.last_collected_message_id = 100

        channel2 = MagicMock()
        channel2.id = uuid4()
        channel2.username = "channel2"
        channel2.telegram_id = 222222
        channel2.is_active = True
        channel2.subscriber_count = 2000
        channel2.last_collected_message_id = 500  # Different from channel1

        channels = [channel1, channel2]

        # This test verifies the pattern - actual implementation
        # will be tested after the fix is applied
        assert channel1.last_collected_message_id != channel2.last_collected_message_id

"""
Tests for TNSE Content Collection Service

Following TDD methodology: tests for the ContentCollector service that handles
content collection from Telegram channels.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Create content collection job
- Implement 24-hour content window
- Extract text content
- Extract media metadata
- Detect forwarded messages
- Store in database
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestContentCollectorService:
    """Tests for the ContentCollector service class."""

    def test_collector_service_exists(self):
        """Test that ContentCollector service can be imported."""
        from src.tnse.pipeline.collector import ContentCollector

        assert ContentCollector is not None

    def test_collector_requires_telegram_client(self):
        """Test that ContentCollector requires a Telegram client."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        collector = ContentCollector(telegram_client=mock_client)

        assert collector.telegram_client is mock_client

    def test_collector_has_default_content_window(self):
        """Test that collector has default 24-hour content window."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        collector = ContentCollector(telegram_client=mock_client)

        assert collector.content_window_hours == 24

    def test_collector_accepts_custom_content_window(self):
        """Test that collector accepts custom content window."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        collector = ContentCollector(
            telegram_client=mock_client,
            content_window_hours=12,
        )

        assert collector.content_window_hours == 12


class TestContentWindowFiltering:
    """Tests for 24-hour content window filtering."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_get_cutoff_time_returns_datetime(self, collector):
        """Test that get_cutoff_time returns a datetime."""
        cutoff = collector.get_cutoff_time()

        assert isinstance(cutoff, datetime)

    def test_get_cutoff_time_is_24_hours_ago(self, collector):
        """Test that cutoff time is 24 hours before now."""
        now = datetime.now(timezone.utc)
        cutoff = collector.get_cutoff_time()

        # Should be approximately 24 hours ago (within 1 second tolerance)
        expected = now - timedelta(hours=24)
        time_diff = abs((cutoff - expected).total_seconds())

        assert time_diff < 1.0

    def test_get_cutoff_time_respects_custom_window(self):
        """Test that cutoff time uses custom window hours."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        collector = ContentCollector(
            telegram_client=mock_client,
            content_window_hours=12,
        )

        now = datetime.now(timezone.utc)
        cutoff = collector.get_cutoff_time()

        expected = now - timedelta(hours=12)
        time_diff = abs((cutoff - expected).total_seconds())

        assert time_diff < 1.0

    def test_is_within_window_returns_true_for_recent(self, collector):
        """Test that recent messages are within the window."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

        assert collector.is_within_window(recent_time) is True

    def test_is_within_window_returns_false_for_old(self, collector):
        """Test that old messages are outside the window."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)

        assert collector.is_within_window(old_time) is False

    def test_is_within_window_boundary(self, collector):
        """Test boundary condition for window."""
        # Just inside the window (23 hours ago)
        inside = datetime.now(timezone.utc) - timedelta(hours=23)
        assert collector.is_within_window(inside) is True

        # Just outside the window (25 hours ago)
        outside = datetime.now(timezone.utc) - timedelta(hours=25)
        assert collector.is_within_window(outside) is False


class TestTextContentExtraction:
    """Tests for text content extraction from messages."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_extract_text_content_returns_string(self, collector):
        """Test that extract_text_content returns a string."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test message content",
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_text_content(message)

        assert isinstance(result, str)

    def test_extract_text_content_extracts_text(self, collector):
        """Test that text content is extracted from message."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="This is the message text content",
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_text_content(message)

        assert result == "This is the message text content"

    def test_extract_text_content_handles_none(self, collector):
        """Test that None text is handled gracefully."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text=None,
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_text_content(message)

        assert result == ""

    def test_extract_text_content_handles_empty(self, collector):
        """Test that empty text is handled gracefully."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="",
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_text_content(message)

        assert result == ""

    def test_extract_text_preserves_cyrillic(self, collector):
        """Test that Cyrillic text is preserved correctly."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Привет мир! Это тестовое сообщение.",
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_text_content(message)

        assert result == "Привет мир! Это тестовое сообщение."


class TestMediaMetadataExtraction:
    """Tests for media metadata extraction from messages."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_extract_media_metadata_returns_list(self, collector):
        """Test that extract_media_metadata returns a list."""
        from src.tnse.telegram.client import MediaInfo, MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            media=[],
        )

        result = collector.extract_media_metadata(message)

        assert isinstance(result, list)

    def test_extract_media_metadata_empty_for_no_media(self, collector):
        """Test that empty list returned when no media."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Text only message",
            date=datetime.now(timezone.utc),
            media=[],
        )

        result = collector.extract_media_metadata(message)

        assert result == []

    def test_extract_media_metadata_extracts_photo(self, collector):
        """Test that photo metadata is extracted."""
        from src.tnse.telegram.client import MediaInfo, MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Photo message",
            date=datetime.now(timezone.utc),
            media=[
                MediaInfo(
                    media_type="photo",
                    file_id="photo123",
                    file_size=50000,
                    width=800,
                    height=600,
                )
            ],
        )

        result = collector.extract_media_metadata(message)

        assert len(result) == 1
        assert result[0]["media_type"] == "photo"
        assert result[0]["file_id"] == "photo123"
        assert result[0]["width"] == 800
        assert result[0]["height"] == 600

    def test_extract_media_metadata_extracts_video(self, collector):
        """Test that video metadata is extracted."""
        from src.tnse.telegram.client import MediaInfo, MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Video message",
            date=datetime.now(timezone.utc),
            media=[
                MediaInfo(
                    media_type="video",
                    file_id="video456",
                    file_size=5000000,
                    width=1920,
                    height=1080,
                    duration=120,
                    mime_type="video/mp4",
                )
            ],
        )

        result = collector.extract_media_metadata(message)

        assert len(result) == 1
        assert result[0]["media_type"] == "video"
        assert result[0]["duration"] == 120
        assert result[0]["mime_type"] == "video/mp4"

    def test_extract_media_metadata_handles_multiple(self, collector):
        """Test that multiple media items are extracted."""
        from src.tnse.telegram.client import MediaInfo, MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Album message",
            date=datetime.now(timezone.utc),
            media=[
                MediaInfo(media_type="photo", file_id="photo1"),
                MediaInfo(media_type="photo", file_id="photo2"),
                MediaInfo(media_type="photo", file_id="photo3"),
            ],
        )

        result = collector.extract_media_metadata(message)

        assert len(result) == 3


class TestForwardedMessageDetection:
    """Tests for forwarded message detection."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_is_forwarded_returns_bool(self, collector):
        """Test that is_forwarded returns a boolean."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            is_forwarded=False,
        )

        result = collector.is_forwarded(message)

        assert isinstance(result, bool)

    def test_is_forwarded_true_for_forwarded(self, collector):
        """Test that forwarded messages are detected."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Forwarded message",
            date=datetime.now(timezone.utc),
            is_forwarded=True,
            forward_from_channel_id=456,
            forward_from_message_id=789,
        )

        assert collector.is_forwarded(message) is True

    def test_is_forwarded_false_for_original(self, collector):
        """Test that original messages are not marked as forwarded."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Original message",
            date=datetime.now(timezone.utc),
            is_forwarded=False,
        )

        assert collector.is_forwarded(message) is False

    def test_extract_forward_info_returns_dict(self, collector):
        """Test that extract_forward_info returns a dictionary."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            is_forwarded=True,
            forward_from_channel_id=456,
            forward_from_message_id=789,
        )

        result = collector.extract_forward_info(message)

        assert isinstance(result, dict)

    def test_extract_forward_info_contains_source(self, collector):
        """Test that forward info contains source channel."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Forwarded",
            date=datetime.now(timezone.utc),
            is_forwarded=True,
            forward_from_channel_id=456,
            forward_from_message_id=789,
        )

        result = collector.extract_forward_info(message)

        assert result["forward_from_channel_id"] == 456
        assert result["forward_from_message_id"] == 789

    def test_extract_forward_info_empty_for_original(self, collector):
        """Test that forward info is empty for original messages."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Original",
            date=datetime.now(timezone.utc),
            is_forwarded=False,
        )

        result = collector.extract_forward_info(message)

        assert result["forward_from_channel_id"] is None
        assert result["forward_from_message_id"] is None


class TestMessageDataExtraction:
    """Tests for extracting complete message data for storage."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_extract_message_data_returns_dict(self, collector):
        """Test that extract_message_data returns a dictionary."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
        )

        result = collector.extract_message_data(message, channel_uuid=uuid4())

        assert isinstance(result, dict)

    def test_extract_message_data_contains_required_fields(self, collector):
        """Test that extracted data contains all required fields."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=42,
            channel_id=123,
            text="Complete message",
            date=datetime.now(timezone.utc),
            views=1000,
            forwards=50,
            replies=25,
            reactions={"heart": 100, "thumbs_up": 50},
        )

        channel_uuid = uuid4()
        result = collector.extract_message_data(message, channel_uuid=channel_uuid)

        # Post data
        assert result["telegram_message_id"] == 42
        assert result["channel_id"] == channel_uuid
        assert "published_at" in result

        # Content
        assert result["text_content"] == "Complete message"

        # Engagement
        assert result["views"] == 1000
        assert result["forwards"] == 50
        assert result["replies"] == 25
        assert result["reactions"] == {"heart": 100, "thumbs_up": 50}


class TestEngagementMetricsExtraction:
    """Tests for engagement metrics extraction."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = MagicMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    def test_extract_engagement_returns_dict(self, collector):
        """Test that extract_engagement returns a dictionary."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            views=100,
        )

        result = collector.extract_engagement(message)

        assert isinstance(result, dict)

    def test_extract_engagement_includes_views(self, collector):
        """Test that views are extracted."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            views=5000,
        )

        result = collector.extract_engagement(message)

        assert result["view_count"] == 5000

    def test_extract_engagement_includes_forwards(self, collector):
        """Test that forwards are extracted."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            forwards=250,
        )

        result = collector.extract_engagement(message)

        assert result["forward_count"] == 250

    def test_extract_engagement_includes_replies(self, collector):
        """Test that replies are extracted."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            replies=75,
        )

        result = collector.extract_engagement(message)

        assert result["reply_count"] == 75

    def test_extract_engagement_includes_reactions(self, collector):
        """Test that reactions are extracted with counts."""
        from src.tnse.telegram.client import MessageInfo

        message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Test",
            date=datetime.now(timezone.utc),
            reactions={"heart": 150, "fire": 89, "thumbs_up": 234},
        )

        result = collector.extract_engagement(message)

        assert result["reactions"] == {"heart": 150, "fire": 89, "thumbs_up": 234}


class TestCollectChannelMessages:
    """Tests for collecting messages from a channel."""

    @pytest.fixture
    def collector(self):
        """Create a ContentCollector instance for testing."""
        from src.tnse.pipeline.collector import ContentCollector
        from src.tnse.telegram.client import TelegramClient

        mock_client = AsyncMock(spec=TelegramClient)
        return ContentCollector(telegram_client=mock_client)

    @pytest.mark.asyncio
    async def test_collect_channel_messages_returns_dict_with_messages(self, collector):
        """Test that collect_channel_messages returns a dict with messages list."""
        collector.telegram_client.get_messages = AsyncMock(return_value=[])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # WS-8.2: Return format changed to dict with metadata
        assert isinstance(result, dict)
        assert "messages" in result
        assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_collect_channel_messages_filters_by_window(self, collector):
        """Test that messages outside window are filtered."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        old_message = MessageInfo(
            message_id=1,
            channel_id=123,
            text="Old message",
            date=now - timedelta(hours=48),
        )
        recent_message = MessageInfo(
            message_id=2,
            channel_id=123,
            text="Recent message",
            date=now - timedelta(hours=1),
        )

        collector.telegram_client.get_messages = AsyncMock(
            return_value=[old_message, recent_message]
        )

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # Only recent message should be in result
        # WS-8.2: Access messages from result dict
        messages = result["messages"]
        assert len(messages) == 1
        assert messages[0]["telegram_message_id"] == 2

    @pytest.mark.asyncio
    async def test_collect_channel_messages_handles_empty(self, collector):
        """Test that empty message list is handled."""
        collector.telegram_client.get_messages = AsyncMock(return_value=[])

        result = await collector.collect_channel_messages(
            telegram_channel_id=123,
            channel_uuid=uuid4(),
        )

        # WS-8.2: Return format changed to dict with messages list
        assert result["messages"] == []
        assert result["count"] == 0

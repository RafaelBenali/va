"""
Tests for TNSE Content Storage Service

Following TDD methodology: tests for the ContentStorage service that handles
persisting collected content to the database.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Store in database
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestContentStorageService:
    """Tests for the ContentStorage service class."""

    def test_storage_service_exists(self):
        """Test that ContentStorage service can be imported."""
        from src.tnse.pipeline.storage import ContentStorage

        assert ContentStorage is not None

    def test_storage_requires_session_factory(self):
        """Test that ContentStorage requires a database session factory."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        storage = ContentStorage(session_factory=mock_session_factory)

        assert storage.session_factory is mock_session_factory


class TestPostStorage:
    """Tests for storing posts in the database."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_create_post_record_returns_dict(self, storage):
        """Test that create_post_record returns a dictionary."""
        channel_uuid = uuid4()
        message_data = {
            "telegram_message_id": 123,
            "channel_id": channel_uuid,
            "published_at": datetime.now(timezone.utc),
            "text_content": "Test message",
            "is_forwarded": False,
            "forward_from_channel_id": None,
            "forward_from_message_id": None,
            "media": [],
            "views": 100,
            "forwards": 10,
            "replies": 5,
            "reactions": {},
        }

        result = storage.create_post_record(message_data)

        assert isinstance(result, dict)

    def test_create_post_record_contains_post_fields(self, storage):
        """Test that post record contains required fields."""
        channel_uuid = uuid4()
        published = datetime.now(timezone.utc)
        message_data = {
            "telegram_message_id": 456,
            "channel_id": channel_uuid,
            "published_at": published,
            "text_content": "Test",
            "is_forwarded": True,
            "forward_from_channel_id": 789,
            "forward_from_message_id": 101,
            "media": [],
            "views": 0,
            "forwards": 0,
            "replies": 0,
            "reactions": {},
        }

        result = storage.create_post_record(message_data)

        assert result["telegram_message_id"] == 456
        assert result["channel_id"] == channel_uuid
        assert result["published_at"] == published
        assert result["is_forwarded"] is True
        assert result["forward_from_channel_id"] == 789
        assert result["forward_from_message_id"] == 101


class TestPostContentStorage:
    """Tests for storing post content in the database."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_create_content_record_returns_dict(self, storage):
        """Test that create_content_record returns a dictionary."""
        post_uuid = uuid4()
        message_data = {
            "text_content": "Test content",
        }

        result = storage.create_content_record(post_uuid, message_data)

        assert isinstance(result, dict)

    def test_create_content_record_contains_text(self, storage):
        """Test that content record contains text content."""
        post_uuid = uuid4()
        message_data = {
            "text_content": "This is the full text of the message.",
        }

        result = storage.create_content_record(post_uuid, message_data)

        assert result["post_id"] == post_uuid
        assert result["text_content"] == "This is the full text of the message."


class TestMediaStorage:
    """Tests for storing media metadata in the database."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_create_media_records_returns_list(self, storage):
        """Test that create_media_records returns a list."""
        post_uuid = uuid4()
        message_data = {
            "media": [],
        }

        result = storage.create_media_records(post_uuid, message_data)

        assert isinstance(result, list)

    def test_create_media_records_empty_for_no_media(self, storage):
        """Test that empty list returned when no media."""
        post_uuid = uuid4()
        message_data = {
            "media": [],
        }

        result = storage.create_media_records(post_uuid, message_data)

        assert result == []

    def test_create_media_records_for_photo(self, storage):
        """Test that media record created for photo."""
        post_uuid = uuid4()
        message_data = {
            "media": [
                {
                    "media_type": "photo",
                    "file_id": "photo123",
                    "file_size": 50000,
                    "width": 800,
                    "height": 600,
                    "mime_type": None,
                    "duration": None,
                    "thumbnail_file_id": None,
                }
            ],
        }

        result = storage.create_media_records(post_uuid, message_data)

        assert len(result) == 1
        assert result[0]["post_id"] == post_uuid
        assert result[0]["media_type"] == "photo"
        assert result[0]["file_id"] == "photo123"


class TestEngagementStorage:
    """Tests for storing engagement metrics in the database."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_create_engagement_record_returns_dict(self, storage):
        """Test that create_engagement_record returns a dictionary."""
        post_uuid = uuid4()
        message_data = {
            "views": 1000,
            "forwards": 50,
            "replies": 25,
            "reactions": {},
        }

        result = storage.create_engagement_record(post_uuid, message_data)

        assert isinstance(result, dict)

    def test_create_engagement_record_contains_metrics(self, storage):
        """Test that engagement record contains all metrics."""
        post_uuid = uuid4()
        message_data = {
            "views": 5000,
            "forwards": 100,
            "replies": 75,
            "reactions": {"heart": 150, "fire": 89},
        }

        result = storage.create_engagement_record(post_uuid, message_data)

        assert result["post_id"] == post_uuid
        assert result["view_count"] == 5000
        assert result["forward_count"] == 100
        assert result["reply_count"] == 75

    def test_create_reaction_records_returns_list(self, storage):
        """Test that create_reaction_records returns a list."""
        engagement_uuid = uuid4()
        reactions = {"heart": 100, "thumbs_up": 50}

        result = storage.create_reaction_records(engagement_uuid, reactions)

        assert isinstance(result, list)

    def test_create_reaction_records_for_each_emoji(self, storage):
        """Test that reaction records created for each emoji."""
        engagement_uuid = uuid4()
        reactions = {"heart": 100, "thumbs_up": 50, "fire": 25}

        result = storage.create_reaction_records(engagement_uuid, reactions)

        assert len(result) == 3

        # Check each reaction is present
        emojis = [record["emoji"] for record in result]
        assert "heart" in emojis
        assert "thumbs_up" in emojis
        assert "fire" in emojis

    def test_create_reaction_records_with_counts(self, storage):
        """Test that reaction records have correct counts."""
        engagement_uuid = uuid4()
        reactions = {"heart": 150}

        result = storage.create_reaction_records(engagement_uuid, reactions)

        assert len(result) == 1
        assert result[0]["engagement_metrics_id"] == engagement_uuid
        assert result[0]["emoji"] == "heart"
        assert result[0]["count"] == 150


class TestReactionScoreCalculation:
    """Tests for calculating reaction scores."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_calculate_reaction_score_returns_float(self, storage):
        """Test that calculate_reaction_score returns a float."""
        reactions = {"heart": 100}

        result = storage.calculate_reaction_score(reactions)

        assert isinstance(result, float)

    def test_calculate_reaction_score_empty(self, storage):
        """Test that empty reactions return 0."""
        result = storage.calculate_reaction_score({})

        assert result == 0.0

    def test_calculate_reaction_score_uses_weights(self, storage):
        """Test that reaction score uses configured weights."""
        # heart = 2.0 weight, thumbs_up = 1.0 weight
        reactions = {"heart": 100, "thumbs_up": 50}

        result = storage.calculate_reaction_score(reactions)

        # 100 * 2.0 + 50 * 1.0 = 250.0
        assert result == 250.0


class TestRelativeEngagementCalculation:
    """Tests for calculating relative engagement."""

    @pytest.fixture
    def storage(self):
        """Create a ContentStorage instance for testing."""
        from src.tnse.pipeline.storage import ContentStorage

        mock_session_factory = MagicMock()
        return ContentStorage(session_factory=mock_session_factory)

    def test_calculate_relative_engagement_returns_float(self, storage):
        """Test that calculate_relative_engagement returns a float."""
        result = storage.calculate_relative_engagement(
            views=1000,
            reaction_score=100.0,
            subscriber_count=10000,
        )

        assert isinstance(result, float)

    def test_calculate_relative_engagement_formula(self, storage):
        """Test relative engagement calculation formula."""
        result = storage.calculate_relative_engagement(
            views=5000,
            reaction_score=500.0,
            subscriber_count=100000,
        )

        # (5000 + 500) / 100000 = 0.055
        assert result == pytest.approx(0.055)

    def test_calculate_relative_engagement_zero_subscribers(self, storage):
        """Test handling of zero subscriber count."""
        result = storage.calculate_relative_engagement(
            views=1000,
            reaction_score=100.0,
            subscriber_count=0,
        )

        # Should handle division by zero gracefully
        assert result == 0.0

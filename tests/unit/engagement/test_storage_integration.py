"""
Tests for EngagementService integration with ContentStorage.

Following TDD methodology: these tests verify the integration between
EngagementService and the existing ContentStorage pipeline.

Work Stream: WS-2.1 - Engagement Metrics

Requirements addressed:
- NFR-D-002: Engagement metrics MUST be stored with timestamps
- REQ-MO-008: System MUST display detailed reaction breakdown in results
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class TestEngagementServiceStorageIntegration:
    """Tests for using EngagementService with ContentStorage pipeline."""

    def test_engagement_service_metrics_compatible_with_storage(self):
        """Test that EngagementService output matches ContentStorage expectations."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {
            "views": 5000,
            "forwards": 100,
            "replies": 50,
            "reactions": {"heart": 20, "thumbs_up": 30},
        }

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        # Verify all required storage fields are present
        required_fields = [
            "post_id",
            "view_count",
            "forward_count",
            "reply_count",
            "reaction_score",
            "relative_engagement",
            "collected_at",
        ]

        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"

    def test_engagement_service_reaction_counts_compatible_with_storage(self):
        """Test that reaction counts match storage format."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 20, "thumbs_up": 30, "fire": 10}

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions=reactions,
        )

        # Verify each record has required fields
        for record in counts:
            assert "engagement_metrics_id" in record
            assert "emoji" in record
            assert "count" in record

    def test_engagement_service_produces_same_score_as_storage(self):
        """Test that EngagementService calculates same score as ContentStorage."""
        from src.tnse.engagement.service import EngagementService
        from src.tnse.pipeline.storage import ContentStorage

        # Create instances
        engagement_service = EngagementService()
        storage = ContentStorage(session_factory=lambda: None)

        # Same reactions
        reactions = {"heart": 89, "thumbs_up": 150, "fire": 34}

        service_score = engagement_service.calculate_reaction_score(reactions)
        storage_score = storage.calculate_reaction_score(reactions)

        assert service_score == storage_score

    def test_engagement_service_produces_same_relative_engagement_as_storage(self):
        """Test that EngagementService calculates same relative engagement as ContentStorage."""
        from src.tnse.engagement.service import EngagementService
        from src.tnse.pipeline.storage import ContentStorage

        engagement_service = EngagementService()
        storage = ContentStorage(session_factory=lambda: None)

        views = 5000
        reaction_score = 413.0
        subscriber_count = 10000

        service_result = engagement_service.calculate_relative_engagement(
            views=views,
            reaction_score=reaction_score,
            subscriber_count=subscriber_count,
        )
        storage_result = storage.calculate_relative_engagement(
            views=views,
            reaction_score=reaction_score,
            subscriber_count=subscriber_count,
        )

        assert service_result == storage_result


class TestEngagementProcessingPipeline:
    """Tests for the complete engagement processing pipeline."""

    def test_process_message_engagement_end_to_end(self):
        """Test complete message engagement processing from raw data to storage format."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        # Simulate raw message data from Telegram
        raw_message = {
            "views": 12500,
            "forwards": 250,
            "replies": 75,
            "reactions": {
                "thumbs_up": 150,
                "heart": 89,
                "fire": 34,
                "thinking": 12,
                "clap": 28,
            },
        }
        post_id = uuid4()
        subscriber_count = 50000

        # Process engagement
        metrics = service.create_engagement_metrics(
            post_id=post_id,
            message_data=raw_message,
            subscriber_count=subscriber_count,
        )

        # Verify metrics
        assert metrics["view_count"] == 12500
        assert metrics["forward_count"] == 250
        assert metrics["reply_count"] == 75

        # Verify reaction score calculation
        # thumbs_up: 150 * 1.0 = 150
        # heart: 89 * 2.0 = 178
        # fire: 34 * 1.5 = 51
        # thinking: 12 * 0.5 = 6
        # clap: 28 * 1.0 = 28
        expected_score = 150 + 178 + 51 + 6 + 28  # 413
        assert metrics["reaction_score"] == expected_score

        # Verify relative engagement
        # (12500 + 413) / 50000 = 0.25826
        expected_engagement = (12500 + 413) / 50000
        assert metrics["relative_engagement"] == expected_engagement

    def test_process_reactions_end_to_end(self):
        """Test complete reaction count processing to storage format."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        reactions = {
            "thumbs_up": 150,
            "heart": 89,
            "fire": 34,
            "thinking": 12,
            "clap": 28,
        }
        engagement_metrics_id = uuid4()

        counts = service.create_reaction_counts(
            engagement_metrics_id=engagement_metrics_id,
            reactions=reactions,
        )

        # Verify all reactions are captured
        assert len(counts) == 5

        # Verify each reaction is correct
        emoji_counts = {record["emoji"]: record["count"] for record in counts}
        assert emoji_counts["thumbs_up"] == 150
        assert emoji_counts["heart"] == 89
        assert emoji_counts["fire"] == 34
        assert emoji_counts["thinking"] == 12
        assert emoji_counts["clap"] == 28

    def test_metrics_include_utc_timestamp(self):
        """Test that metrics timestamp is UTC and recent."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        before = datetime.now(timezone.utc)

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data={"views": 1000, "reactions": {}},
            subscriber_count=10000,
        )

        after = datetime.now(timezone.utc)

        # Verify timestamp is between before and after
        assert before <= metrics["collected_at"] <= after

        # Verify it's timezone aware (UTC)
        assert metrics["collected_at"].tzinfo is not None


class TestEngagementExtractionFromCollector:
    """Tests for extracting engagement data from ContentCollector format."""

    def test_extract_from_collector_message_format(self):
        """Test extracting engagement from ContentCollector's message data format."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        # This is the format that ContentCollector.extract_message_data produces
        collector_output = {
            "telegram_message_id": 12345,
            "channel_id": uuid4(),
            "published_at": datetime.now(timezone.utc),
            "text_content": "Test message",
            "is_forwarded": False,
            "forward_from_channel_id": None,
            "forward_from_message_id": None,
            "media": [],
            "views": 5000,
            "forwards": 100,
            "replies": 50,
            "reactions": {"heart": 20, "thumbs_up": 30},
        }

        # EngagementService should be able to process this
        view_count = service.extract_view_count(collector_output)
        reactions = service.extract_reactions(collector_output)

        assert view_count == 5000
        assert reactions == {"heart": 20, "thumbs_up": 30}

    def test_full_pipeline_from_collector_format(self):
        """Test full engagement processing from collector output format."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        # Collector output format
        collector_output = {
            "telegram_message_id": 12345,
            "channel_id": uuid4(),
            "published_at": datetime.now(timezone.utc),
            "text_content": "Test message",
            "is_forwarded": False,
            "views": 8000,
            "forwards": 200,
            "replies": 100,
            "reactions": {"heart": 50, "fire": 25},
        }

        post_id = uuid4()
        subscriber_count = 20000

        # Process using EngagementService
        metrics = service.create_engagement_metrics(
            post_id=post_id,
            message_data=collector_output,
            subscriber_count=subscriber_count,
        )

        # Verify all metrics extracted correctly
        assert metrics["view_count"] == 8000
        assert metrics["forward_count"] == 200
        assert metrics["reply_count"] == 100

        # heart: 50 * 2.0 = 100, fire: 25 * 1.5 = 37.5 = 137.5
        expected_score = (50 * 2.0) + (25 * 1.5)
        assert metrics["reaction_score"] == expected_score

        # (8000 + 137.5) / 20000 = 0.406875
        expected_engagement = (8000 + expected_score) / 20000
        assert metrics["relative_engagement"] == expected_engagement

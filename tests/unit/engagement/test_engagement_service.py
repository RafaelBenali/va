"""
Tests for TNSE Engagement Service.

Following TDD methodology: these tests are written BEFORE the implementation.

Work Stream: WS-2.1 - Engagement Metrics

Requirements addressed:
- REQ-MO-002: System MUST retrieve and display view counts for each post
- REQ-MO-003: System MUST count EACH emoji reaction type separately
- REQ-MO-004: System MUST calculate a "reaction score" based on individual emoji counts
- REQ-MO-006: System MUST rank posts using: views, reaction score, and relative engagement
- REQ-MO-007: System SHOULD allow users to configure reaction score weights
- NFR-D-002: Engagement metrics MUST be stored with timestamps
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class TestEngagementServiceExists:
    """Tests to verify EngagementService class exists and can be imported."""

    def test_engagement_service_class_exists(self):
        """Test that EngagementService class exists and can be imported."""
        from src.tnse.engagement.service import EngagementService

        assert EngagementService is not None

    def test_engagement_service_can_be_instantiated(self):
        """Test that EngagementService can be instantiated."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        assert service is not None


class TestReactionWeightsConfiguration:
    """Tests for configurable reaction weights."""

    def test_default_reaction_weights_are_loaded(self):
        """Test that default reaction weights are loaded from settings."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert isinstance(weights, dict)
        assert "heart" in weights
        assert "thumbs_up" in weights
        assert "fire" in weights
        assert "clap" in weights
        assert "thinking" in weights
        assert "thumbs_down" in weights

    def test_default_heart_weight_is_2(self):
        """Test that heart reaction has weight of 2.0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert weights["heart"] == 2.0

    def test_default_thumbs_up_weight_is_1(self):
        """Test that thumbs up reaction has weight of 1.0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert weights["thumbs_up"] == 1.0

    def test_default_fire_weight_is_1_5(self):
        """Test that fire reaction has weight of 1.5."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert weights["fire"] == 1.5

    def test_default_thumbs_down_weight_is_negative_1(self):
        """Test that thumbs down reaction has weight of -1.0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert weights["thumbs_down"] == -1.0

    def test_default_thinking_weight_is_0_5(self):
        """Test that thinking reaction has weight of 0.5."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        weights = service.get_reaction_weights()

        assert weights["thinking"] == 0.5

    def test_custom_weights_can_be_provided(self):
        """Test that custom reaction weights can be provided."""
        from src.tnse.engagement.service import EngagementService

        custom_weights = {
            "heart": 3.0,
            "thumbs_up": 2.0,
            "fire": 2.5,
            "clap": 1.5,
            "thinking": 1.0,
            "thumbs_down": -2.0,
        }

        service = EngagementService(reaction_weights=custom_weights)
        weights = service.get_reaction_weights()

        assert weights["heart"] == 3.0
        assert weights["thumbs_up"] == 2.0

    def test_get_weight_for_emoji_returns_correct_weight(self):
        """Test that get_weight_for_emoji returns the correct weight."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        assert service.get_weight_for_emoji("heart") == 2.0
        assert service.get_weight_for_emoji("fire") == 1.5

    def test_get_weight_for_unknown_emoji_returns_default(self):
        """Test that unknown emoji returns default weight of 1.0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        assert service.get_weight_for_emoji("unknown_emoji") == 1.0
        assert service.get_weight_for_emoji("custom_reaction") == 1.0


class TestReactionScoreCalculation:
    """Tests for reaction score calculation."""

    def test_calculate_reaction_score_returns_float(self):
        """Test that calculate_reaction_score returns a float."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10, "thumbs_up": 5}

        score = service.calculate_reaction_score(reactions)

        assert isinstance(score, float)

    def test_calculate_reaction_score_empty_reactions_returns_zero(self):
        """Test that empty reactions dictionary returns 0.0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        assert service.calculate_reaction_score({}) == 0.0
        assert service.calculate_reaction_score(None) == 0.0

    def test_calculate_reaction_score_single_reaction(self):
        """Test reaction score with a single reaction type."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10}  # heart weight = 2.0

        score = service.calculate_reaction_score(reactions)

        assert score == 20.0  # 10 * 2.0

    def test_calculate_reaction_score_multiple_reactions(self):
        """Test reaction score with multiple reaction types."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        # heart=2.0, thumbs_up=1.0, fire=1.5
        reactions = {"heart": 10, "thumbs_up": 20, "fire": 5}

        score = service.calculate_reaction_score(reactions)

        expected = (10 * 2.0) + (20 * 1.0) + (5 * 1.5)  # 20 + 20 + 7.5 = 47.5
        assert score == expected

    def test_calculate_reaction_score_with_negative_weight(self):
        """Test reaction score with negative weight (thumbs_down)."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10, "thumbs_down": 5}

        score = service.calculate_reaction_score(reactions)

        expected = (10 * 2.0) + (5 * -1.0)  # 20 - 5 = 15
        assert score == expected

    def test_calculate_reaction_score_with_unknown_emoji(self):
        """Test reaction score with unknown emoji uses default weight."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"custom_emoji": 10}  # default weight = 1.0

        score = service.calculate_reaction_score(reactions)

        assert score == 10.0

    def test_calculate_reaction_score_matches_formula(self):
        """Test that reaction score matches the documented formula.

        Formula: reaction_score = sum(emoji_count * emoji_weight for emoji in reactions)
        """
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {
            "thumbs_up": 150,
            "heart": 89,
            "fire": 34,
            "thinking": 12,
            "clap": 28,
        }

        score = service.calculate_reaction_score(reactions)

        # thumbs_up: 150 * 1.0 = 150
        # heart: 89 * 2.0 = 178
        # fire: 34 * 1.5 = 51
        # thinking: 12 * 0.5 = 6
        # clap: 28 * 1.0 = 28
        expected = 150 + 178 + 51 + 6 + 28  # 413
        assert score == expected


class TestViewCountExtraction:
    """Tests for view count extraction."""

    def test_extract_view_count_from_message_data(self):
        """Test extracting view count from message data."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 1000}

        view_count = service.extract_view_count(message_data)

        assert view_count == 1000

    def test_extract_view_count_missing_returns_zero(self):
        """Test that missing view count returns 0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {}

        view_count = service.extract_view_count(message_data)

        assert view_count == 0

    def test_extract_view_count_none_returns_zero(self):
        """Test that None view count returns 0."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": None}

        view_count = service.extract_view_count(message_data)

        assert view_count == 0


class TestReactionCountExtraction:
    """Tests for individual emoji reaction count extraction."""

    def test_extract_reactions_returns_dict(self):
        """Test that extract_reactions returns a dictionary."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"reactions": {"heart": 10, "fire": 5}}

        reactions = service.extract_reactions(message_data)

        assert isinstance(reactions, dict)

    def test_extract_reactions_preserves_counts(self):
        """Test that all reaction counts are preserved."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {
            "reactions": {
                "thumbs_up": 150,
                "heart": 89,
                "fire": 34,
                "thinking": 12,
                "clap": 28,
            }
        }

        reactions = service.extract_reactions(message_data)

        assert reactions["thumbs_up"] == 150
        assert reactions["heart"] == 89
        assert reactions["fire"] == 34
        assert reactions["thinking"] == 12
        assert reactions["clap"] == 28

    def test_extract_reactions_missing_returns_empty_dict(self):
        """Test that missing reactions returns empty dict."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {}

        reactions = service.extract_reactions(message_data)

        assert reactions == {}

    def test_extract_reactions_none_returns_empty_dict(self):
        """Test that None reactions returns empty dict."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"reactions": None}

        reactions = service.extract_reactions(message_data)

        assert reactions == {}


class TestRelativeEngagementCalculation:
    """Tests for relative engagement calculation."""

    def test_calculate_relative_engagement_returns_float(self):
        """Test that calculate_relative_engagement returns a float."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        result = service.calculate_relative_engagement(
            views=1000, reaction_score=100.0, subscriber_count=10000
        )

        assert isinstance(result, float)

    def test_calculate_relative_engagement_formula(self):
        """Test that relative engagement follows the formula.

        Formula: relative_engagement = (views + reaction_score) / subscriber_count
        """
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        result = service.calculate_relative_engagement(
            views=1000, reaction_score=500.0, subscriber_count=10000
        )

        expected = (1000 + 500.0) / 10000  # 0.15
        assert result == expected

    def test_calculate_relative_engagement_zero_subscribers_returns_zero(self):
        """Test that zero subscribers returns 0.0 (avoid division by zero)."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        result = service.calculate_relative_engagement(
            views=1000, reaction_score=500.0, subscriber_count=0
        )

        assert result == 0.0

    def test_calculate_relative_engagement_high_engagement(self):
        """Test relative engagement for viral content (>100% reach)."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        result = service.calculate_relative_engagement(
            views=50000, reaction_score=10000.0, subscriber_count=10000
        )

        expected = (50000 + 10000.0) / 10000  # 6.0 (600% reach)
        assert result == expected


class TestEngagementMetricsCreation:
    """Tests for creating complete engagement metrics."""

    def test_create_engagement_metrics_returns_dict(self):
        """Test that create_engagement_metrics returns a dictionary."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {
            "views": 1000,
            "forwards": 50,
            "replies": 25,
            "reactions": {"heart": 10, "thumbs_up": 20},
        }

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert isinstance(metrics, dict)

    def test_create_engagement_metrics_includes_view_count(self):
        """Test that metrics include view_count."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 5000, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "view_count" in metrics
        assert metrics["view_count"] == 5000

    def test_create_engagement_metrics_includes_reaction_score(self):
        """Test that metrics include calculated reaction_score."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {
            "views": 1000,
            "reactions": {"heart": 10, "thumbs_up": 20},  # 10*2 + 20*1 = 40
        }

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "reaction_score" in metrics
        assert metrics["reaction_score"] == 40.0

    def test_create_engagement_metrics_includes_relative_engagement(self):
        """Test that metrics include calculated relative_engagement."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {
            "views": 1000,
            "reactions": {"heart": 10},  # score = 20
        }

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "relative_engagement" in metrics
        expected = (1000 + 20) / 10000  # 0.102
        assert metrics["relative_engagement"] == expected

    def test_create_engagement_metrics_includes_timestamp(self):
        """Test that metrics include collected_at timestamp."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 1000, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "collected_at" in metrics
        assert isinstance(metrics["collected_at"], datetime)

    def test_create_engagement_metrics_timestamp_is_utc(self):
        """Test that collected_at timestamp is timezone-aware (UTC)."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 1000, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert metrics["collected_at"].tzinfo is not None

    def test_create_engagement_metrics_includes_forward_count(self):
        """Test that metrics include forward_count."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 1000, "forwards": 75, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "forward_count" in metrics
        assert metrics["forward_count"] == 75

    def test_create_engagement_metrics_includes_reply_count(self):
        """Test that metrics include reply_count."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        message_data = {"views": 1000, "replies": 42, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=uuid4(),
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "reply_count" in metrics
        assert metrics["reply_count"] == 42

    def test_create_engagement_metrics_includes_post_id(self):
        """Test that metrics include the post_id."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        post_id = uuid4()
        message_data = {"views": 1000, "reactions": {}}

        metrics = service.create_engagement_metrics(
            post_id=post_id,
            message_data=message_data,
            subscriber_count=10000,
        )

        assert "post_id" in metrics
        assert metrics["post_id"] == post_id


class TestReactionCountsCreation:
    """Tests for creating individual reaction count records."""

    def test_create_reaction_counts_returns_list(self):
        """Test that create_reaction_counts returns a list."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10, "fire": 5}

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions=reactions,
        )

        assert isinstance(counts, list)

    def test_create_reaction_counts_empty_reactions_returns_empty_list(self):
        """Test that empty reactions returns empty list."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions={},
        )

        assert counts == []

    def test_create_reaction_counts_creates_record_per_emoji(self):
        """Test that a record is created for each emoji type."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10, "fire": 5, "thumbs_up": 20}

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions=reactions,
        )

        assert len(counts) == 3

    def test_create_reaction_counts_includes_emoji_name(self):
        """Test that each record includes the emoji name."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 10}

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions=reactions,
        )

        assert counts[0]["emoji"] == "heart"

    def test_create_reaction_counts_includes_count(self):
        """Test that each record includes the count."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        reactions = {"heart": 42}

        counts = service.create_reaction_counts(
            engagement_metrics_id=uuid4(),
            reactions=reactions,
        )

        assert counts[0]["count"] == 42

    def test_create_reaction_counts_includes_engagement_metrics_id(self):
        """Test that each record includes the engagement_metrics_id."""
        from src.tnse.engagement.service import EngagementService

        service = EngagementService()
        metrics_id = uuid4()
        reactions = {"heart": 10}

        counts = service.create_reaction_counts(
            engagement_metrics_id=metrics_id,
            reactions=reactions,
        )

        assert counts[0]["engagement_metrics_id"] == metrics_id

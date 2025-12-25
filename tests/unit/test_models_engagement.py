"""
Tests for TNSE Engagement Metrics database models.

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover the EngagementMetrics and ReactionCount models.

Requirements addressed:
- WS-1.2: Design schema for engagement metrics (views, reactions per emoji)
- REQ-MO-002: System MUST retrieve and display view counts for each post
- REQ-MO-003: System MUST count EACH emoji reaction type separately
- REQ-MO-004: System MUST calculate a "reaction score"
- NFR-D-002: Engagement metrics MUST be stored with timestamps
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestEngagementMetricsModel:
    """Tests for the EngagementMetrics database model."""

    def test_engagement_metrics_model_exists(self):
        """Test that EngagementMetrics model class exists."""
        from src.tnse.db.models import EngagementMetrics
        assert EngagementMetrics is not None

    def test_engagement_metrics_has_required_fields(self):
        """Test that EngagementMetrics has all required fields."""
        from src.tnse.db.models import EngagementMetrics

        column_names = [column.name for column in EngagementMetrics.__table__.columns]

        required_fields = [
            "id",
            "post_id",
            "view_count",
            "forward_count",
            "reply_count",
            "reaction_score",
            "relative_engagement",
            "collected_at",
        ]

        for field in required_fields:
            assert field in column_names, f"EngagementMetrics missing required field: {field}"

    def test_engagement_metrics_has_tablename(self):
        """Test that EngagementMetrics has correct table name."""
        from src.tnse.db.models import EngagementMetrics

        assert EngagementMetrics.__tablename__ == "engagement_metrics"

    def test_engagement_metrics_has_foreign_key_to_post(self):
        """Test that EngagementMetrics has foreign key to Post."""
        from src.tnse.db.models import EngagementMetrics

        post_id_column = EngagementMetrics.__table__.columns["post_id"]
        foreign_keys = list(post_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "posts.id" in str(foreign_keys[0])

    def test_engagement_metrics_view_count_is_integer(self):
        """Test that view_count is an integer type."""
        from src.tnse.db.models import EngagementMetrics
        from sqlalchemy import Integer, BigInteger

        view_column = EngagementMetrics.__table__.columns["view_count"]
        assert isinstance(view_column.type, (Integer, BigInteger))

    def test_engagement_metrics_collected_at_has_timestamp(self):
        """Test that collected_at stores timezone-aware timestamps."""
        from src.tnse.db.models import EngagementMetrics
        from sqlalchemy import DateTime

        collected_at_column = EngagementMetrics.__table__.columns["collected_at"]
        assert isinstance(collected_at_column.type, DateTime)
        assert collected_at_column.type.timezone is True

    def test_engagement_metrics_collected_at_is_indexed(self):
        """Test that collected_at is indexed for time-series queries."""
        from src.tnse.db.models import EngagementMetrics

        collected_at_column = EngagementMetrics.__table__.columns["collected_at"]
        has_index = collected_at_column.index is True or any(
            "collected_at" in [col.name for col in idx.columns]
            for idx in EngagementMetrics.__table__.indexes
        )
        assert has_index, "collected_at should be indexed for time-series queries"

    def test_engagement_metrics_can_be_instantiated(self):
        """Test that EngagementMetrics can be instantiated."""
        from src.tnse.db.models import EngagementMetrics

        metrics = EngagementMetrics(
            post_id=uuid4(),
            view_count=1000,
            forward_count=50,
            reply_count=25,
            reaction_score=150.5,
            relative_engagement=0.025,
        )

        assert metrics.view_count == 1000
        assert metrics.reaction_score == 150.5

    def test_engagement_metrics_defaults_to_zero(self):
        """Test that numeric fields default to 0."""
        from src.tnse.db.models import EngagementMetrics

        view_column = EngagementMetrics.__table__.columns["view_count"]
        forward_column = EngagementMetrics.__table__.columns["forward_count"]
        reply_column = EngagementMetrics.__table__.columns["reply_count"]

        # Check defaults exist
        assert view_column.default is not None or view_column.server_default is not None
        assert forward_column.default is not None or forward_column.server_default is not None
        assert reply_column.default is not None or reply_column.server_default is not None


class TestReactionCountModel:
    """Tests for the ReactionCount database model."""

    def test_reaction_count_model_exists(self):
        """Test that ReactionCount model class exists."""
        from src.tnse.db.models import ReactionCount
        assert ReactionCount is not None

    def test_reaction_count_has_required_fields(self):
        """Test that ReactionCount has all required fields."""
        from src.tnse.db.models import ReactionCount

        column_names = [column.name for column in ReactionCount.__table__.columns]

        required_fields = [
            "id",
            "engagement_metrics_id",
            "emoji",
            "count",
        ]

        for field in required_fields:
            assert field in column_names, f"ReactionCount missing required field: {field}"

    def test_reaction_count_has_tablename(self):
        """Test that ReactionCount has correct table name."""
        from src.tnse.db.models import ReactionCount

        assert ReactionCount.__tablename__ == "reaction_counts"

    def test_reaction_count_has_foreign_key_to_engagement_metrics(self):
        """Test that ReactionCount has foreign key to EngagementMetrics."""
        from src.tnse.db.models import ReactionCount

        metrics_id_column = ReactionCount.__table__.columns["engagement_metrics_id"]
        foreign_keys = list(metrics_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "engagement_metrics.id" in str(foreign_keys[0])

    def test_reaction_count_emoji_is_string(self):
        """Test that emoji field can store emoji characters/codes."""
        from src.tnse.db.models import ReactionCount
        from sqlalchemy import String

        emoji_column = ReactionCount.__table__.columns["emoji"]
        assert isinstance(emoji_column.type, String)

    def test_reaction_count_count_is_integer(self):
        """Test that count is an integer type."""
        from src.tnse.db.models import ReactionCount
        from sqlalchemy import Integer, BigInteger

        count_column = ReactionCount.__table__.columns["count"]
        assert isinstance(count_column.type, (Integer, BigInteger))

    def test_reaction_count_can_be_instantiated(self):
        """Test that ReactionCount can be instantiated."""
        from src.tnse.db.models import ReactionCount

        reaction = ReactionCount(
            engagement_metrics_id=uuid4(),
            emoji="thumbs_up",
            count=150,
        )

        assert reaction.emoji == "thumbs_up"
        assert reaction.count == 150

    def test_reaction_count_emoji_is_indexed(self):
        """Test that emoji is indexed for filtering by reaction type."""
        from src.tnse.db.models import ReactionCount

        emoji_column = ReactionCount.__table__.columns["emoji"]
        has_index = emoji_column.index is True or any(
            "emoji" in [col.name for col in idx.columns]
            for idx in ReactionCount.__table__.indexes
        )
        assert has_index, "emoji should be indexed for reaction type queries"

    def test_reaction_count_has_unique_constraint_on_metrics_and_emoji(self):
        """Test that there's a unique constraint on (engagement_metrics_id, emoji)."""
        from src.tnse.db.models import ReactionCount

        # Check for unique constraint
        constraints = ReactionCount.__table__.constraints
        has_unique = False
        for constraint in constraints:
            if hasattr(constraint, 'columns'):
                col_names = [col.name for col in constraint.columns]
                if 'engagement_metrics_id' in col_names and 'emoji' in col_names:
                    has_unique = True
                    break

        # Also check indexes for unique index
        for index in ReactionCount.__table__.indexes:
            col_names = [col.name for col in index.columns]
            if 'engagement_metrics_id' in col_names and 'emoji' in col_names and index.unique:
                has_unique = True
                break

        assert has_unique, "ReactionCount should have unique constraint on (engagement_metrics_id, emoji)"


class TestEngagementRelationships:
    """Tests for engagement-related relationships."""

    def test_engagement_metrics_has_relationship_to_reactions(self):
        """Test that EngagementMetrics has relationship to ReactionCount."""
        from src.tnse.db.models import EngagementMetrics

        # Check that the relationship exists
        assert hasattr(EngagementMetrics, "reactions")

    def test_post_has_relationship_to_engagement_metrics(self):
        """Test that Post has relationship to EngagementMetrics."""
        from src.tnse.db.models import Post

        # Check that the relationship exists
        assert hasattr(Post, "engagement_metrics")

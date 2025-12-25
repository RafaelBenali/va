"""
Tests for TNSE Ranking Service.

Following TDD methodology: these tests are written BEFORE the implementation.

Work Stream: WS-2.3 - Ranking Algorithm

Requirements addressed:
- REQ-MO-006: System MUST rank posts using: views, reaction score, and relative engagement
- Ranking by combined score: engagement * recency
- Sorting options: views, reactions, engagement, recency, combined
- Configurable time window (default 24 hours)
- Configurable weight for recency vs engagement
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any
from dataclasses import dataclass


class TestRankingServiceExists:
    """Tests to verify RankingService class exists and can be imported."""

    def test_ranking_service_class_exists(self):
        """Test that RankingService class exists and can be imported."""
        from src.tnse.ranking.service import RankingService

        assert RankingService is not None

    def test_ranking_service_can_be_instantiated(self):
        """Test that RankingService can be instantiated."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        assert service is not None


class TestSortModeEnum:
    """Tests for SortMode enumeration."""

    def test_sort_mode_enum_exists(self):
        """Test that SortMode enum exists and can be imported."""
        from src.tnse.ranking.service import SortMode

        assert SortMode is not None

    def test_sort_mode_has_combined(self):
        """Test that SortMode has COMBINED option."""
        from src.tnse.ranking.service import SortMode

        assert hasattr(SortMode, "COMBINED")

    def test_sort_mode_has_views(self):
        """Test that SortMode has VIEWS option."""
        from src.tnse.ranking.service import SortMode

        assert hasattr(SortMode, "VIEWS")

    def test_sort_mode_has_reactions(self):
        """Test that SortMode has REACTIONS option."""
        from src.tnse.ranking.service import SortMode

        assert hasattr(SortMode, "REACTIONS")

    def test_sort_mode_has_engagement(self):
        """Test that SortMode has ENGAGEMENT option."""
        from src.tnse.ranking.service import SortMode

        assert hasattr(SortMode, "ENGAGEMENT")

    def test_sort_mode_has_recency(self):
        """Test that SortMode has RECENCY option."""
        from src.tnse.ranking.service import SortMode

        assert hasattr(SortMode, "RECENCY")


class TestRankedPostDataclass:
    """Tests for RankedPost dataclass."""

    def test_ranked_post_exists(self):
        """Test that RankedPost dataclass exists and can be imported."""
        from src.tnse.ranking.service import RankedPost

        assert RankedPost is not None

    def test_ranked_post_has_post_id_field(self):
        """Test that RankedPost has post_id field."""
        from src.tnse.ranking.service import RankedPost
        from uuid import uuid4

        post = RankedPost(
            post_id=uuid4(),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.1,
            posted_at=datetime.now(timezone.utc),
            combined_score=0.0,
        )
        assert hasattr(post, "post_id")

    def test_ranked_post_has_combined_score_field(self):
        """Test that RankedPost has combined_score field."""
        from src.tnse.ranking.service import RankedPost
        from uuid import uuid4

        post = RankedPost(
            post_id=uuid4(),
            view_count=1000,
            reaction_score=50.0,
            relative_engagement=0.1,
            posted_at=datetime.now(timezone.utc),
            combined_score=0.95,
        )
        assert post.combined_score == 0.95


class TestRankingConfiguration:
    """Tests for configurable ranking parameters."""

    def test_default_time_window_is_24_hours(self):
        """Test that default time window is 24 hours."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        assert service.time_window_hours == 24

    def test_custom_time_window_can_be_provided(self):
        """Test that custom time window can be provided."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=12)
        assert service.time_window_hours == 12

    def test_default_recency_weight_is_1(self):
        """Test that default recency weight is 1.0."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        assert service.recency_weight == 1.0

    def test_custom_recency_weight_can_be_provided(self):
        """Test that custom recency weight can be provided."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(recency_weight=0.5)
        assert service.recency_weight == 0.5


class TestRecencyFactorCalculation:
    """Tests for recency factor calculation."""

    def test_calculate_recency_factor_returns_float(self):
        """Test that calculate_recency_factor returns a float."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        now = datetime.now(timezone.utc)

        result = service.calculate_recency_factor(now)

        assert isinstance(result, float)

    def test_recency_factor_for_just_posted_is_1(self):
        """Test that a post just now has recency factor of 1.0."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        now = datetime.now(timezone.utc)

        result = service.calculate_recency_factor(now)

        assert result == pytest.approx(1.0, abs=0.01)

    def test_recency_factor_for_12_hours_ago_is_0_5(self):
        """Test that a post 12 hours ago has recency factor of 0.5."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24)
        now = datetime.now(timezone.utc)
        posted_at = now - timedelta(hours=12)

        result = service.calculate_recency_factor(posted_at, reference_time=now)

        assert result == pytest.approx(0.5, abs=0.01)

    def test_recency_factor_for_24_hours_ago_is_0(self):
        """Test that a post 24 hours ago has recency factor of 0.0."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24)
        now = datetime.now(timezone.utc)
        posted_at = now - timedelta(hours=24)

        result = service.calculate_recency_factor(posted_at, reference_time=now)

        assert result == pytest.approx(0.0, abs=0.01)

    def test_recency_factor_for_older_than_window_is_0(self):
        """Test that posts older than time window have recency factor of 0."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24)
        now = datetime.now(timezone.utc)
        posted_at = now - timedelta(hours=48)

        result = service.calculate_recency_factor(posted_at, reference_time=now)

        assert result == 0.0

    def test_recency_factor_with_6_hour_window(self):
        """Test recency factor with 6 hour time window."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=6)
        now = datetime.now(timezone.utc)
        posted_at = now - timedelta(hours=3)  # halfway through 6hr window

        result = service.calculate_recency_factor(posted_at, reference_time=now)

        assert result == pytest.approx(0.5, abs=0.01)


class TestCombinedScoreCalculation:
    """Tests for combined score calculation."""

    def test_calculate_combined_score_returns_float(self):
        """Test that calculate_combined_score returns a float."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()

        result = service.calculate_combined_score(
            relative_engagement=0.1,
            recency_factor=1.0,
        )

        assert isinstance(result, float)

    def test_combined_score_formula(self):
        """Test that combined score follows the formula.

        Formula: combined_score = relative_engagement * (recency_factor * recency_weight)
        With recency_weight=1.0: combined_score = relative_engagement * recency_factor
        """
        from src.tnse.ranking.service import RankingService

        service = RankingService(recency_weight=1.0)

        result = service.calculate_combined_score(
            relative_engagement=0.25,
            recency_factor=0.8,
        )

        expected = 0.25 * 0.8  # 0.2
        assert result == pytest.approx(expected, abs=0.001)

    def test_combined_score_with_custom_recency_weight(self):
        """Test combined score with custom recency weight."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(recency_weight=0.5)

        result = service.calculate_combined_score(
            relative_engagement=0.5,
            recency_factor=0.5,
        )

        # With recency_weight=0.5, the recency factor is weighted
        # combined = engagement * (1 - recency_weight + recency_factor * recency_weight)
        # combined = 0.5 * (1 - 0.5 + 0.5 * 0.5) = 0.5 * (0.5 + 0.25) = 0.5 * 0.75 = 0.375
        expected = 0.5 * (1 - 0.5 + 0.5 * 0.5)
        assert result == pytest.approx(expected, abs=0.001)

    def test_combined_score_zero_recency_with_weight_preserves_engagement(self):
        """Test that zero recency with partial weight preserves some engagement."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(recency_weight=0.5)

        result = service.calculate_combined_score(
            relative_engagement=0.5,
            recency_factor=0.0,
        )

        # With recency_weight=0.5 and recency_factor=0:
        # combined = engagement * (1 - recency_weight + recency_factor * recency_weight)
        # combined = 0.5 * (1 - 0.5 + 0 * 0.5) = 0.5 * 0.5 = 0.25
        expected = 0.5 * (1 - 0.5)
        assert result == pytest.approx(expected, abs=0.001)

    def test_combined_score_full_recency_weight_matches_simple_formula(self):
        """Test that recency_weight=1.0 matches simple multiplication formula."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(recency_weight=1.0)

        result = service.calculate_combined_score(
            relative_engagement=0.25,
            recency_factor=0.5,
        )

        # With recency_weight=1.0:
        # combined = engagement * (1 - 1.0 + recency_factor * 1.0)
        # combined = engagement * recency_factor
        expected = 0.25 * 0.5
        assert result == pytest.approx(expected, abs=0.001)


class TestCalculateCombinedScoreForPost:
    """Tests for calculating combined score for a single post."""

    def test_calculate_score_for_post_returns_float(self):
        """Test that calculate_score_for_post returns a float."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        now = datetime.now(timezone.utc)
        post_data = {
            "relative_engagement": 0.1,
            "posted_at": now,
        }

        result = service.calculate_score_for_post(post_data)

        assert isinstance(result, float)

    def test_calculate_score_for_new_high_engagement_post(self):
        """Test score calculation for a new post with high engagement."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)
        post_data = {
            "relative_engagement": 0.5,
            "posted_at": now,
        }

        result = service.calculate_score_for_post(post_data, reference_time=now)

        # Brand new post (recency=1.0) with engagement 0.5
        # combined = 0.5 * 1.0 = 0.5
        assert result == pytest.approx(0.5, abs=0.01)

    def test_calculate_score_for_old_high_engagement_post(self):
        """Test score calculation for an old post with high engagement."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)
        posted_at = now - timedelta(hours=24)
        post_data = {
            "relative_engagement": 0.5,
            "posted_at": posted_at,
        }

        result = service.calculate_score_for_post(post_data, reference_time=now)

        # 24-hour old post (recency=0.0) with engagement 0.5
        # combined = 0.5 * 0.0 = 0.0
        assert result == pytest.approx(0.0, abs=0.01)


class TestRankingPosts:
    """Tests for ranking a collection of posts."""

    def test_rank_posts_returns_list(self):
        """Test that rank_posts returns a list."""
        from src.tnse.ranking.service import RankingService, SortMode

        service = RankingService()
        posts = []

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert isinstance(result, list)

    def test_rank_posts_empty_list_returns_empty(self):
        """Test that ranking empty list returns empty list."""
        from src.tnse.ranking.service import RankingService, SortMode

        service = RankingService()
        posts = []

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert result == []

    def test_rank_posts_returns_ranked_post_objects(self):
        """Test that rank_posts returns RankedPost objects."""
        from src.tnse.ranking.service import RankingService, RankedPost, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)
        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.1,
                "posted_at": now,
            }
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert len(result) == 1
        assert isinstance(result[0], RankedPost)

    def test_rank_posts_by_combined_score_descending(self):
        """Test that posts are ranked by combined score (highest first)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 500,
                "reaction_score": 25.0,
                "relative_engagement": 0.1,  # Low engagement
                "posted_at": now,  # Very recent
            },
            {
                "post_id": uuid4(),
                "view_count": 2000,
                "reaction_score": 100.0,
                "relative_engagement": 0.5,  # High engagement
                "posted_at": now - timedelta(hours=12),  # Half recency
            },
            {
                "post_id": uuid4(),
                "view_count": 3000,
                "reaction_score": 150.0,
                "relative_engagement": 0.8,  # Very high engagement
                "posted_at": now - timedelta(hours=1),  # Very recent
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED, reference_time=now)

        # Post 3 should be first: 0.8 * (1 - 1/24) ~ 0.77
        # Post 1 should be second: 0.1 * 1.0 = 0.1
        # Post 2 should be third: 0.5 * 0.5 = 0.25
        # Wait - Post 2 with 0.25 > Post 1 with 0.1
        # Order should be: Post 3 (0.77), Post 2 (0.25), Post 1 (0.1)
        assert result[0].relative_engagement == 0.8
        assert result[1].relative_engagement == 0.5
        assert result[2].relative_engagement == 0.1


class TestSortByViews:
    """Tests for sorting by views."""

    def test_sort_by_views_descending(self):
        """Test that posts are sorted by views (highest first)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 500,
                "reaction_score": 100.0,
                "relative_engagement": 0.5,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 2000,
                "reaction_score": 50.0,
                "relative_engagement": 0.1,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 75.0,
                "relative_engagement": 0.3,
                "posted_at": now,
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.VIEWS)

        assert result[0].view_count == 2000
        assert result[1].view_count == 1000
        assert result[2].view_count == 500


class TestSortByReactions:
    """Tests for sorting by reaction score."""

    def test_sort_by_reactions_descending(self):
        """Test that posts are sorted by reaction score (highest first)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 2000,
                "reaction_score": 50.0,
                "relative_engagement": 0.1,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 500,
                "reaction_score": 150.0,
                "relative_engagement": 0.5,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 100.0,
                "relative_engagement": 0.3,
                "posted_at": now,
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.REACTIONS)

        assert result[0].reaction_score == 150.0
        assert result[1].reaction_score == 100.0
        assert result[2].reaction_score == 50.0


class TestSortByEngagement:
    """Tests for sorting by relative engagement."""

    def test_sort_by_engagement_descending(self):
        """Test that posts are sorted by relative engagement (highest first)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 2000,
                "reaction_score": 100.0,
                "relative_engagement": 0.1,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 500,
                "reaction_score": 50.0,
                "relative_engagement": 0.5,
                "posted_at": now,
            },
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 75.0,
                "relative_engagement": 0.3,
                "posted_at": now,
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.ENGAGEMENT)

        assert result[0].relative_engagement == 0.5
        assert result[1].relative_engagement == 0.3
        assert result[2].relative_engagement == 0.1


class TestSortByRecency:
    """Tests for sorting by recency."""

    def test_sort_by_recency_descending(self):
        """Test that posts are sorted by recency (newest first)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.1,
                "posted_at": now - timedelta(hours=12),
            },
            {
                "post_id": uuid4(),
                "view_count": 500,
                "reaction_score": 25.0,
                "relative_engagement": 0.05,
                "posted_at": now - timedelta(hours=1),
            },
            {
                "post_id": uuid4(),
                "view_count": 2000,
                "reaction_score": 100.0,
                "relative_engagement": 0.2,
                "posted_at": now - timedelta(hours=6),
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.RECENCY)

        # Newest first (1 hour ago, then 6 hours ago, then 12 hours ago)
        assert result[0].view_count == 500  # 1 hour ago
        assert result[1].view_count == 2000  # 6 hours ago
        assert result[2].view_count == 1000  # 12 hours ago


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handle_zero_relative_engagement(self):
        """Test handling of zero relative engagement."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.0,  # Zero engagement (e.g., zero subscribers)
                "posted_at": now,
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert len(result) == 1
        assert result[0].combined_score == 0.0

    def test_handle_very_old_posts(self):
        """Test handling of posts older than time window."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService(time_window_hours=24)
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 10000,
                "reaction_score": 500.0,
                "relative_engagement": 1.0,  # Very high engagement
                "posted_at": now - timedelta(hours=48),  # Very old post
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED, reference_time=now)

        assert len(result) == 1
        # Even high engagement post should have 0 combined score if too old
        assert result[0].combined_score == 0.0

    def test_handle_future_posted_at(self):
        """Test handling of future post timestamps (edge case)."""
        from src.tnse.ranking.service import RankingService

        service = RankingService()
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(hours=1)

        result = service.calculate_recency_factor(future_time, reference_time=now)

        # Future posts should be capped at recency factor of 1.0
        assert result == 1.0

    def test_handle_missing_relative_engagement_uses_zero(self):
        """Test that missing relative_engagement defaults to 0."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                # relative_engagement is missing
                "posted_at": now,
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert len(result) == 1
        assert result[0].relative_engagement == 0.0

    def test_handle_missing_posted_at_uses_now(self):
        """Test that missing posted_at defaults to now (full recency)."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.5,
                # posted_at is missing
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        assert len(result) == 1
        # Should have high combined score since defaults to now
        assert result[0].combined_score > 0

    def test_handle_naive_datetime_converts_to_utc(self):
        """Test that naive datetime is treated as UTC."""
        from src.tnse.ranking.service import RankingService

        service = RankingService(time_window_hours=24)
        now = datetime.now(timezone.utc)
        naive_time = datetime.now()  # Naive datetime

        # Should not raise an error
        result = service.calculate_recency_factor(naive_time, reference_time=now)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0


class TestRankingWithMultiplePosts:
    """Tests for ranking multiple posts with various scenarios."""

    def test_rank_10_posts_by_combined_score(self):
        """Test ranking 10 posts by combined score."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000 * i,
                "reaction_score": 50.0 * i,
                "relative_engagement": 0.1 * i,
                "posted_at": now - timedelta(hours=i),
            }
            for i in range(1, 11)
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED, reference_time=now)

        assert len(result) == 10
        # Results should be sorted by combined score descending
        for i in range(len(result) - 1):
            assert result[i].combined_score >= result[i + 1].combined_score

    def test_posts_with_same_score_maintain_stable_order(self):
        """Test that posts with same score maintain stable order."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        post_ids = [uuid4() for _ in range(3)]
        posts = [
            {
                "post_id": post_ids[i],
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.1,
                "posted_at": now,
            }
            for i in range(3)
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.VIEWS)

        # All have same view count, should maintain input order
        assert len(result) == 3


class TestCombinedScoreAccessor:
    """Tests for accessing combined score after ranking."""

    def test_ranked_post_has_computed_combined_score(self):
        """Test that RankedPost includes the computed combined score."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.25,
                "posted_at": now - timedelta(hours=12),  # 50% recency
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.COMBINED, reference_time=now)

        # combined = 0.25 * 0.5 = 0.125
        assert result[0].combined_score == pytest.approx(0.125, abs=0.01)

    def test_combined_score_computed_even_for_non_combined_sort(self):
        """Test that combined score is computed even when not sorting by it."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService(time_window_hours=24, recency_weight=1.0)
        now = datetime.now(timezone.utc)

        posts = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "reaction_score": 50.0,
                "relative_engagement": 0.25,
                "posted_at": now,  # 100% recency
            },
        ]

        result = service.rank_posts(posts, sort_mode=SortMode.VIEWS, reference_time=now)

        # combined = 0.25 * 1.0 = 0.25
        assert result[0].combined_score == pytest.approx(0.25, abs=0.01)


class TestRankingServiceIntegrationWithEngagementService:
    """Tests for integration with EngagementService data format."""

    def test_rank_posts_accepts_engagement_metrics_format(self):
        """Test that rank_posts accepts the format from EngagementService."""
        from src.tnse.ranking.service import RankingService, SortMode
        from uuid import uuid4

        service = RankingService()
        now = datetime.now(timezone.utc)

        # Format matching EngagementService.create_engagement_metrics output
        engagement_data = [
            {
                "post_id": uuid4(),
                "view_count": 1000,
                "forward_count": 50,
                "reply_count": 25,
                "reaction_score": 150.0,
                "relative_engagement": 0.115,
                "collected_at": now,
                "posted_at": now - timedelta(hours=2),
            },
        ]

        result = service.rank_posts(engagement_data, sort_mode=SortMode.COMBINED)

        assert len(result) == 1
        assert result[0].view_count == 1000
        assert result[0].reaction_score == 150.0
        assert result[0].relative_engagement == 0.115

"""
Tests for LLM Cost Tracking and Monitoring (WS-5.7)

Following TDD methodology: these tests are written BEFORE implementation.
The tests validate:
1. Groq pricing constants configuration
2. Cost estimation calculations
3. Usage logging to database
4. Daily and monthly statistics retrieval
5. Cost limit alerts and warnings
6. Stats command output formatting

Work Stream: WS-5.7 - LLM Cost Tracking and Monitoring
Dependencies: WS-5.4 (Celery Enrichment Tasks), WS-5.6 (Bot Integration)
"""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestGroqPricingConstants:
    """Tests for Groq pricing constants configuration."""

    def test_default_pricing_exists(self):
        """Test that default pricing constants are defined."""
        from src.tnse.llm.cost_tracker import GROQ_PRICING

        assert GROQ_PRICING is not None
        assert "default" in GROQ_PRICING

    def test_pricing_has_input_output_rates(self):
        """Test that pricing includes both input and output token rates."""
        from src.tnse.llm.cost_tracker import GROQ_PRICING

        default_pricing = GROQ_PRICING["default"]
        assert "input" in default_pricing
        assert "output" in default_pricing

    def test_pricing_for_known_models(self):
        """Test that pricing is defined for known Groq models."""
        from src.tnse.llm.cost_tracker import GROQ_PRICING

        # These models should have pricing defined
        known_models = [
            "qwen-qwq-32b",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
        ]

        for model in known_models:
            assert model in GROQ_PRICING, f"Missing pricing for {model}"
            assert "input" in GROQ_PRICING[model]
            assert "output" in GROQ_PRICING[model]

    def test_pricing_rates_are_numeric(self):
        """Test that all pricing rates are numeric values."""
        from src.tnse.llm.cost_tracker import GROQ_PRICING

        for model, rates in GROQ_PRICING.items():
            assert isinstance(rates["input"], (int, float)), f"Invalid input rate for {model}"
            assert isinstance(rates["output"], (int, float)), f"Invalid output rate for {model}"

    def test_pricing_rates_are_positive(self):
        """Test that all pricing rates are positive."""
        from src.tnse.llm.cost_tracker import GROQ_PRICING

        for model, rates in GROQ_PRICING.items():
            assert rates["input"] >= 0, f"Negative input rate for {model}"
            assert rates["output"] >= 0, f"Negative output rate for {model}"


class TestCostEstimation:
    """Tests for cost estimation calculations."""

    def test_estimate_cost_basic(self):
        """Test basic cost estimation calculation."""
        from src.tnse.llm.cost_tracker import estimate_cost

        # Using default model (qwen-qwq-32b)
        # Pricing is per 1M tokens
        cost = estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="qwen-qwq-32b"
        )

        assert isinstance(cost, Decimal)
        assert cost > Decimal("0")

    def test_estimate_cost_with_unknown_model_uses_default(self):
        """Test that unknown models use default pricing."""
        from src.tnse.llm.cost_tracker import estimate_cost

        cost_unknown = estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="unknown-model-xyz"
        )

        cost_default = estimate_cost(
            prompt_tokens=1000,
            completion_tokens=500,
            model="default"
        )

        assert cost_unknown == cost_default

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        from src.tnse.llm.cost_tracker import estimate_cost

        cost = estimate_cost(
            prompt_tokens=0,
            completion_tokens=0,
            model="qwen-qwq-32b"
        )

        assert cost == Decimal("0")

    def test_estimate_cost_large_token_count(self):
        """Test cost estimation with large token counts."""
        from src.tnse.llm.cost_tracker import estimate_cost

        # 1 million tokens each
        cost = estimate_cost(
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            model="qwen-qwq-32b"
        )

        assert cost > Decimal("0")
        # Should be roughly the sum of input and output rates
        assert cost < Decimal("100")  # Sanity check

    def test_estimate_cost_precision(self):
        """Test that cost estimation maintains decimal precision."""
        from src.tnse.llm.cost_tracker import estimate_cost

        cost = estimate_cost(
            prompt_tokens=100,
            completion_tokens=50,
            model="qwen-qwq-32b"
        )

        # Should have at least 6 decimal places of precision
        assert cost.as_tuple().exponent >= -6


class TestCostTracker:
    """Tests for CostTracker class functionality."""

    def test_cost_tracker_initialization(self):
        """Test that CostTracker can be initialized."""
        from src.tnse.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        assert tracker is not None

    def test_cost_tracker_with_custom_daily_limit(self):
        """Test CostTracker with custom daily cost limit."""
        from src.tnse.llm.cost_tracker import CostTracker

        tracker = CostTracker(daily_cost_limit_usd=Decimal("5.00"))
        assert tracker.daily_cost_limit_usd == Decimal("5.00")

    def test_cost_tracker_default_daily_limit(self):
        """Test CostTracker default daily cost limit from environment."""
        from src.tnse.llm.cost_tracker import CostTracker

        # Default should be 10.00 USD
        tracker = CostTracker()
        assert tracker.daily_cost_limit_usd == Decimal("10.00")

    def test_cost_tracker_from_environment(self):
        """Test CostTracker loads limit from environment variable."""
        from src.tnse.llm.cost_tracker import CostTracker

        with patch.dict(os.environ, {"LLM_DAILY_COST_LIMIT_USD": "25.50"}):
            tracker = CostTracker()
            assert tracker.daily_cost_limit_usd == Decimal("25.50")


class TestUsageLogging:
    """Tests for logging LLM usage to database."""

    @pytest.mark.asyncio
    async def test_log_usage_creates_record(self):
        """Test that log_usage creates a database record."""
        from src.tnse.llm.cost_tracker import CostTracker
        from src.tnse.db.models import LLMUsageLog

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        tracker = CostTracker()
        await tracker.log_usage(
            session=mock_session,
            model="qwen-qwq-32b",
            prompt_tokens=1000,
            completion_tokens=500,
            task_name="enrich_post",
            posts_processed=1,
        )

        # Verify a record was added
        mock_session.add.assert_called_once()
        added_record = mock_session.add.call_args[0][0]
        assert isinstance(added_record, LLMUsageLog)
        assert added_record.model == "qwen-qwq-32b"
        assert added_record.prompt_tokens == 1000
        assert added_record.completion_tokens == 500
        assert added_record.task_name == "enrich_post"
        assert added_record.posts_processed == 1

    @pytest.mark.asyncio
    async def test_log_usage_includes_cost_estimate(self):
        """Test that log_usage includes estimated cost."""
        from src.tnse.llm.cost_tracker import CostTracker
        from src.tnse.db.models import LLMUsageLog

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        tracker = CostTracker()
        await tracker.log_usage(
            session=mock_session,
            model="qwen-qwq-32b",
            prompt_tokens=1000,
            completion_tokens=500,
            task_name="enrich_post",
            posts_processed=1,
        )

        added_record = mock_session.add.call_args[0][0]
        assert added_record.estimated_cost_usd is not None
        assert added_record.estimated_cost_usd > Decimal("0")

    @pytest.mark.asyncio
    async def test_log_usage_calculates_total_tokens(self):
        """Test that log_usage calculates total tokens correctly."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        tracker = CostTracker()
        await tracker.log_usage(
            session=mock_session,
            model="qwen-qwq-32b",
            prompt_tokens=1000,
            completion_tokens=500,
            task_name="enrich_post",
            posts_processed=1,
        )

        added_record = mock_session.add.call_args[0][0]
        assert added_record.total_tokens == 1500


class TestDailyStats:
    """Tests for daily statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_daily_stats_returns_correct_structure(self):
        """Test that get_daily_stats returns expected data structure."""
        from src.tnse.llm.cost_tracker import CostTracker, DailyStats

        mock_session = AsyncMock()

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_tokens=10000,
            total_cost=Decimal("0.005"),
            posts_processed=50,
            call_count=50,
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        stats = await tracker.get_daily_stats(session=mock_session)

        assert isinstance(stats, DailyStats)
        assert hasattr(stats, "total_tokens")
        assert hasattr(stats, "total_cost_usd")
        assert hasattr(stats, "posts_processed")
        assert hasattr(stats, "call_count")
        assert hasattr(stats, "date")

    @pytest.mark.asyncio
    async def test_get_daily_stats_for_specific_date(self):
        """Test that get_daily_stats can query a specific date."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        specific_date = datetime(2026, 1, 1, tzinfo=timezone.utc).date()
        stats = await tracker.get_daily_stats(
            session=mock_session,
            date=specific_date
        )

        assert stats.date == specific_date

    @pytest.mark.asyncio
    async def test_get_daily_stats_empty_returns_zero(self):
        """Test that get_daily_stats returns zeroes when no data."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        stats = await tracker.get_daily_stats(session=mock_session)

        assert stats.total_tokens == 0
        assert stats.total_cost_usd == Decimal("0")
        assert stats.posts_processed == 0
        assert stats.call_count == 0


class TestMonthlyStats:
    """Tests for monthly statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_monthly_stats_returns_correct_structure(self):
        """Test that get_monthly_stats returns expected data structure."""
        from src.tnse.llm.cost_tracker import CostTracker, MonthlyStats

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_tokens=500000,
            total_cost=Decimal("0.25"),
            posts_processed=2500,
            call_count=2500,
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        stats = await tracker.get_monthly_stats(session=mock_session)

        assert isinstance(stats, MonthlyStats)
        assert hasattr(stats, "total_tokens")
        assert hasattr(stats, "total_cost_usd")
        assert hasattr(stats, "posts_processed")
        assert hasattr(stats, "call_count")
        assert hasattr(stats, "year")
        assert hasattr(stats, "month")

    @pytest.mark.asyncio
    async def test_get_monthly_stats_for_specific_month(self):
        """Test that get_monthly_stats can query a specific month."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        stats = await tracker.get_monthly_stats(
            session=mock_session,
            year=2025,
            month=12,
        )

        assert stats.year == 2025
        assert stats.month == 12


class TestWeeklyStats:
    """Tests for weekly statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_weekly_stats_returns_correct_structure(self):
        """Test that get_weekly_stats returns expected data structure."""
        from src.tnse.llm.cost_tracker import CostTracker, WeeklyStats

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_tokens=70000,
            total_cost=Decimal("0.035"),
            posts_processed=350,
            call_count=350,
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker()
        stats = await tracker.get_weekly_stats(session=mock_session)

        assert isinstance(stats, WeeklyStats)
        assert hasattr(stats, "total_tokens")
        assert hasattr(stats, "total_cost_usd")
        assert hasattr(stats, "posts_processed")
        assert hasattr(stats, "call_count")
        assert hasattr(stats, "week_start")
        assert hasattr(stats, "week_end")


class TestCostAlerts:
    """Tests for cost limit alerts and warnings."""

    @pytest.mark.asyncio
    async def test_check_daily_limit_under_limit(self):
        """Test that check_daily_limit returns OK when under limit."""
        from src.tnse.llm.cost_tracker import CostTracker, CostStatus

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_cost=Decimal("1.00"),
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(daily_cost_limit_usd=Decimal("10.00"))
        status = await tracker.check_daily_limit(session=mock_session)

        assert status.status == "ok"
        assert status.current_cost == Decimal("1.00")
        assert status.limit == Decimal("10.00")
        assert status.percentage_used == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_check_daily_limit_warning_at_threshold(self):
        """Test warning when approaching daily limit (80%)."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_cost=Decimal("8.50"),  # 85% of 10.00
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(daily_cost_limit_usd=Decimal("10.00"))
        status = await tracker.check_daily_limit(session=mock_session)

        assert status.status == "warning"
        assert status.percentage_used == Decimal("85.00")

    @pytest.mark.asyncio
    async def test_check_daily_limit_exceeded(self):
        """Test alert when daily limit is exceeded."""
        from src.tnse.llm.cost_tracker import CostTracker

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            total_cost=Decimal("12.00"),  # Over 10.00 limit
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        tracker = CostTracker(daily_cost_limit_usd=Decimal("10.00"))
        status = await tracker.check_daily_limit(session=mock_session)

        assert status.status == "exceeded"
        assert status.percentage_used == Decimal("120.00")


class TestStatsFormatting:
    """Tests for stats command output formatting."""

    def test_format_stats_for_display(self):
        """Test formatting stats for Telegram display."""
        from src.tnse.llm.cost_tracker import format_llm_stats, DailyStats, WeeklyStats, MonthlyStats

        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        daily = DailyStats(
            date=today,
            total_tokens=10000,
            total_cost_usd=Decimal("0.005"),
            posts_processed=50,
            call_count=50,
            avg_tokens_per_post=200,
        )

        weekly = WeeklyStats(
            week_start=week_start,
            week_end=week_end,
            total_tokens=70000,
            total_cost_usd=Decimal("0.035"),
            posts_processed=350,
            call_count=350,
            avg_tokens_per_post=200,
        )

        monthly = MonthlyStats(
            year=today.year,
            month=today.month,
            total_tokens=300000,
            total_cost_usd=Decimal("0.15"),
            posts_processed=1500,
            call_count=1500,
            avg_tokens_per_post=200,
        )

        formatted = format_llm_stats(daily, weekly, monthly)

        assert isinstance(formatted, str)
        assert "Today" in formatted or "today" in formatted.lower()
        assert "Week" in formatted or "week" in formatted.lower()
        assert "Month" in formatted or "month" in formatted.lower()
        assert "tokens" in formatted.lower()
        assert "cost" in formatted.lower() or "$" in formatted

    def test_format_stats_includes_token_counts(self):
        """Test that formatted stats include token counts."""
        from src.tnse.llm.cost_tracker import format_llm_stats, DailyStats, WeeklyStats, MonthlyStats

        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())

        daily = DailyStats(
            date=today,
            total_tokens=12345,
            total_cost_usd=Decimal("0.006"),
            posts_processed=60,
            call_count=60,
            avg_tokens_per_post=205,
        )

        weekly = WeeklyStats(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            total_tokens=70000,
            total_cost_usd=Decimal("0.035"),
            posts_processed=350,
            call_count=350,
            avg_tokens_per_post=200,
        )

        monthly = MonthlyStats(
            year=today.year,
            month=today.month,
            total_tokens=300000,
            total_cost_usd=Decimal("0.15"),
            posts_processed=1500,
            call_count=1500,
            avg_tokens_per_post=200,
        )

        formatted = format_llm_stats(daily, weekly, monthly)

        # Should show today's tokens in some form
        assert "12" in formatted or "12,345" in formatted or "12345" in formatted

    def test_format_stats_includes_cost(self):
        """Test that formatted stats include cost estimates."""
        from src.tnse.llm.cost_tracker import format_llm_stats, DailyStats, WeeklyStats, MonthlyStats

        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())

        daily = DailyStats(
            date=today,
            total_tokens=10000,
            total_cost_usd=Decimal("0.12"),
            posts_processed=50,
            call_count=50,
            avg_tokens_per_post=200,
        )

        weekly = WeeklyStats(
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            total_tokens=70000,
            total_cost_usd=Decimal("0.84"),
            posts_processed=350,
            call_count=350,
            avg_tokens_per_post=200,
        )

        monthly = MonthlyStats(
            year=today.year,
            month=today.month,
            total_tokens=300000,
            total_cost_usd=Decimal("3.60"),
            posts_processed=1500,
            call_count=1500,
            avg_tokens_per_post=200,
        )

        formatted = format_llm_stats(daily, weekly, monthly)

        # Should show cost with dollar sign
        assert "$" in formatted
        assert "0.12" in formatted or ".12" in formatted


class TestAverageTokensPerPost:
    """Tests for average tokens per post calculation."""

    def test_daily_stats_avg_tokens_calculated(self):
        """Test that average tokens per post is calculated correctly."""
        from src.tnse.llm.cost_tracker import DailyStats

        today = datetime.now(timezone.utc).date()
        stats = DailyStats(
            date=today,
            total_tokens=10000,
            total_cost_usd=Decimal("0.005"),
            posts_processed=50,
            call_count=50,
            avg_tokens_per_post=200,  # 10000 / 50
        )

        assert stats.avg_tokens_per_post == 200

    def test_daily_stats_avg_tokens_zero_posts(self):
        """Test that average tokens is zero when no posts processed."""
        from src.tnse.llm.cost_tracker import DailyStats

        today = datetime.now(timezone.utc).date()
        stats = DailyStats(
            date=today,
            total_tokens=0,
            total_cost_usd=Decimal("0"),
            posts_processed=0,
            call_count=0,
            avg_tokens_per_post=0,
        )

        assert stats.avg_tokens_per_post == 0


class TestCostSettingsIntegration:
    """Tests for cost tracking settings integration."""

    def test_llm_cost_settings_in_config(self):
        """Test that LLM cost settings are available in config."""
        from src.tnse.core.config import Settings

        settings = Settings()

        # Check that we can access cost-related settings
        assert hasattr(settings, "groq") or hasattr(settings, "llm")

    def test_daily_cost_limit_from_environment(self):
        """Test that daily cost limit can be set from environment."""
        with patch.dict(os.environ, {"LLM_DAILY_COST_LIMIT_USD": "15.00"}):
            from src.tnse.llm.cost_tracker import CostTracker

            tracker = CostTracker()
            assert tracker.daily_cost_limit_usd == Decimal("15.00")


class TestCostTrackerExports:
    """Tests for module exports."""

    def test_cost_tracker_exports(self):
        """Test that cost_tracker module exports are available."""
        from src.tnse.llm import cost_tracker

        # Should have these public exports
        assert hasattr(cost_tracker, "CostTracker")
        assert hasattr(cost_tracker, "GROQ_PRICING")
        assert hasattr(cost_tracker, "estimate_cost")
        assert hasattr(cost_tracker, "DailyStats")
        assert hasattr(cost_tracker, "WeeklyStats")
        assert hasattr(cost_tracker, "MonthlyStats")
        assert hasattr(cost_tracker, "CostStatus")
        assert hasattr(cost_tracker, "format_llm_stats")

    def test_cost_tracker_in_llm_init(self):
        """Test that cost_tracker is exported from llm package."""
        from src.tnse.llm import CostTracker

        assert CostTracker is not None

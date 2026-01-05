"""
LLM Cost Tracking and Monitoring (WS-5.7)

Provides cost estimation, usage logging, and statistics for LLM API calls.
Enables monitoring of token usage, cost tracking, and budget alerts.

Work Stream: WS-5.7 - LLM Cost Tracking and Monitoring
Dependencies: WS-5.4 (Celery Enrichment Tasks)

Requirements addressed:
- All LLM calls logged with token counts
- Cost estimates accurate to pricing
- /stats llm shows useful information
- Warning logged when approaching cost limit
- Historical data queryable
"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tnse.core.logging import get_logger
from src.tnse.db.models import LLMUsageLog

# Module-level logger
logger = get_logger(__name__)

# Groq model pricing (per 1M tokens) - as of January 2026
# Prices in USD. Update as pricing changes.
GROQ_PRICING: dict[str, dict[str, float]] = {
    "qwen-qwq-32b": {"input": 0.15, "output": 0.60},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.2-90b-vision-preview": {"input": 0.90, "output": 0.90},
    "llama-3.2-11b-vision-preview": {"input": 0.18, "output": 0.18},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "gemma-7b-it": {"input": 0.07, "output": 0.07},
    "default": {"input": 0.15, "output": 0.60},
}

# Default daily cost limit in USD
DEFAULT_DAILY_COST_LIMIT_USD = Decimal("10.00")

# Warning threshold (percentage of limit to trigger warning)
WARNING_THRESHOLD_PERCENT = Decimal("80.00")


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "qwen-qwq-32b",
) -> Decimal:
    """Estimate the cost of an LLM API call.

    Args:
        prompt_tokens: Number of tokens in the prompt/input.
        completion_tokens: Number of tokens in the completion/output.
        model: Model identifier to use for pricing lookup.

    Returns:
        Estimated cost in USD as a Decimal with 6 decimal places precision.
    """
    pricing = GROQ_PRICING.get(model, GROQ_PRICING["default"])

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    total_cost = input_cost + output_cost
    return Decimal(str(round(total_cost, 6)))


@dataclass
class DailyStats:
    """Daily LLM usage statistics.

    Attributes:
        date: The date these stats are for.
        total_tokens: Total tokens used (prompt + completion).
        total_cost_usd: Total estimated cost in USD.
        posts_processed: Number of posts enriched.
        call_count: Number of LLM API calls made.
        avg_tokens_per_post: Average tokens per post.
    """
    date: date
    total_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    posts_processed: int = 0
    call_count: int = 0
    avg_tokens_per_post: int = 0


@dataclass
class WeeklyStats:
    """Weekly LLM usage statistics.

    Attributes:
        week_start: Start date of the week (Monday).
        week_end: End date of the week (Sunday).
        total_tokens: Total tokens used.
        total_cost_usd: Total estimated cost in USD.
        posts_processed: Number of posts enriched.
        call_count: Number of LLM API calls made.
        avg_tokens_per_post: Average tokens per post.
    """
    week_start: date
    week_end: date
    total_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    posts_processed: int = 0
    call_count: int = 0
    avg_tokens_per_post: int = 0


@dataclass
class MonthlyStats:
    """Monthly LLM usage statistics.

    Attributes:
        year: Year (e.g., 2026).
        month: Month (1-12).
        total_tokens: Total tokens used.
        total_cost_usd: Total estimated cost in USD.
        posts_processed: Number of posts enriched.
        call_count: Number of LLM API calls made.
        avg_tokens_per_post: Average tokens per post.
    """
    year: int
    month: int
    total_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    posts_processed: int = 0
    call_count: int = 0
    avg_tokens_per_post: int = 0


@dataclass
class CostStatus:
    """Cost limit status check result.

    Attributes:
        status: One of 'ok', 'warning', 'exceeded'.
        current_cost: Current daily cost spent.
        limit: Configured daily cost limit.
        percentage_used: Percentage of limit used.
    """
    status: str  # 'ok', 'warning', 'exceeded'
    current_cost: Decimal
    limit: Decimal
    percentage_used: Decimal


class CostTracker:
    """LLM cost tracking and monitoring service.

    Provides methods to log usage, retrieve statistics, and check cost limits.

    Usage:
        tracker = CostTracker()
        await tracker.log_usage(session, model="qwen-qwq-32b",
                                prompt_tokens=1000, completion_tokens=500,
                                task_name="enrich_post", posts_processed=1)

        daily = await tracker.get_daily_stats(session)
        status = await tracker.check_daily_limit(session)
    """

    def __init__(
        self,
        daily_cost_limit_usd: Decimal | None = None,
    ) -> None:
        """Initialize CostTracker.

        Args:
            daily_cost_limit_usd: Daily cost limit in USD. If None, reads from
                LLM_DAILY_COST_LIMIT_USD environment variable or uses default.
        """
        if daily_cost_limit_usd is not None:
            self.daily_cost_limit_usd = daily_cost_limit_usd
        else:
            env_limit = os.environ.get("LLM_DAILY_COST_LIMIT_USD")
            if env_limit:
                self.daily_cost_limit_usd = Decimal(env_limit)
            else:
                self.daily_cost_limit_usd = DEFAULT_DAILY_COST_LIMIT_USD

    async def log_usage(
        self,
        session: AsyncSession,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task_name: str,
        posts_processed: int = 1,
    ) -> LLMUsageLog:
        """Log an LLM API usage event.

        Creates a new LLMUsageLog record with token counts and estimated cost.

        Args:
            session: Database session.
            model: Model identifier used.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            task_name: Name of the task/operation.
            posts_processed: Number of posts processed in this call.

        Returns:
            The created LLMUsageLog record.
        """
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = estimate_cost(prompt_tokens, completion_tokens, model)

        usage_log = LLMUsageLog(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            task_name=task_name,
            posts_processed=posts_processed,
            created_at=datetime.now(timezone.utc),
        )

        session.add(usage_log)
        await session.commit()

        logger.debug(
            "Logged LLM usage",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=str(estimated_cost),
            task_name=task_name,
        )

        return usage_log

    async def get_daily_stats(
        self,
        session: AsyncSession,
        date: date | None = None,
    ) -> DailyStats:
        """Get LLM usage statistics for a specific day.

        Args:
            session: Database session.
            date: The date to query. Defaults to today (UTC).

        Returns:
            DailyStats with aggregated usage data.
        """
        if date is None:
            date = datetime.now(timezone.utc).date()

        # Calculate date range (full day in UTC)
        start_dt = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        result = await session.execute(
            select(
                func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LLMUsageLog.estimated_cost_usd), 0).label("total_cost"),
                func.coalesce(func.sum(LLMUsageLog.posts_processed), 0).label("posts_processed"),
                func.count(LLMUsageLog.id).label("call_count"),
            ).where(
                LLMUsageLog.created_at >= start_dt,
                LLMUsageLog.created_at < end_dt,
            )
        )

        row = result.one_or_none()

        if row is None:
            return DailyStats(
                date=date,
                total_tokens=0,
                total_cost_usd=Decimal("0"),
                posts_processed=0,
                call_count=0,
                avg_tokens_per_post=0,
            )

        total_tokens = int(row.total_tokens or 0)
        posts_processed = int(row.posts_processed or 0)
        total_cost = Decimal(str(row.total_cost or 0))
        call_count = int(row.call_count or 0)

        avg_tokens = total_tokens // posts_processed if posts_processed > 0 else 0

        return DailyStats(
            date=date,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            posts_processed=posts_processed,
            call_count=call_count,
            avg_tokens_per_post=avg_tokens,
        )

    async def get_weekly_stats(
        self,
        session: AsyncSession,
        week_start: date | None = None,
    ) -> WeeklyStats:
        """Get LLM usage statistics for a week.

        Args:
            session: Database session.
            week_start: Start of week (Monday). Defaults to current week.

        Returns:
            WeeklyStats with aggregated usage data.
        """
        if week_start is None:
            today = datetime.now(timezone.utc).date()
            # Find Monday of current week
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        # Calculate datetime range
        start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

        result = await session.execute(
            select(
                func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LLMUsageLog.estimated_cost_usd), 0).label("total_cost"),
                func.coalesce(func.sum(LLMUsageLog.posts_processed), 0).label("posts_processed"),
                func.count(LLMUsageLog.id).label("call_count"),
            ).where(
                LLMUsageLog.created_at >= start_dt,
                LLMUsageLog.created_at < end_dt,
            )
        )

        row = result.one_or_none()

        if row is None:
            return WeeklyStats(
                week_start=week_start,
                week_end=week_end,
                total_tokens=0,
                total_cost_usd=Decimal("0"),
                posts_processed=0,
                call_count=0,
                avg_tokens_per_post=0,
            )

        total_tokens = int(row.total_tokens or 0)
        posts_processed = int(row.posts_processed or 0)
        total_cost = Decimal(str(row.total_cost or 0))
        call_count = int(row.call_count or 0)

        avg_tokens = total_tokens // posts_processed if posts_processed > 0 else 0

        return WeeklyStats(
            week_start=week_start,
            week_end=week_end,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            posts_processed=posts_processed,
            call_count=call_count,
            avg_tokens_per_post=avg_tokens,
        )

    async def get_monthly_stats(
        self,
        session: AsyncSession,
        year: int | None = None,
        month: int | None = None,
    ) -> MonthlyStats:
        """Get LLM usage statistics for a month.

        Args:
            session: Database session.
            year: Year to query. Defaults to current year.
            month: Month to query (1-12). Defaults to current month.

        Returns:
            MonthlyStats with aggregated usage data.
        """
        now = datetime.now(timezone.utc)
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        # Calculate month date range
        start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        result = await session.execute(
            select(
                func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(LLMUsageLog.estimated_cost_usd), 0).label("total_cost"),
                func.coalesce(func.sum(LLMUsageLog.posts_processed), 0).label("posts_processed"),
                func.count(LLMUsageLog.id).label("call_count"),
            ).where(
                LLMUsageLog.created_at >= start_dt,
                LLMUsageLog.created_at < end_dt,
            )
        )

        row = result.one_or_none()

        if row is None:
            return MonthlyStats(
                year=year,
                month=month,
                total_tokens=0,
                total_cost_usd=Decimal("0"),
                posts_processed=0,
                call_count=0,
                avg_tokens_per_post=0,
            )

        total_tokens = int(row.total_tokens or 0)
        posts_processed = int(row.posts_processed or 0)
        total_cost = Decimal(str(row.total_cost or 0))
        call_count = int(row.call_count or 0)

        avg_tokens = total_tokens // posts_processed if posts_processed > 0 else 0

        return MonthlyStats(
            year=year,
            month=month,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            posts_processed=posts_processed,
            call_count=call_count,
            avg_tokens_per_post=avg_tokens,
        )

    async def check_daily_limit(
        self,
        session: AsyncSession,
    ) -> CostStatus:
        """Check current daily cost against the configured limit.

        Returns status indicating whether limit is OK, approaching (warning),
        or exceeded.

        Args:
            session: Database session.

        Returns:
            CostStatus with current cost, limit, and status.
        """
        daily_stats = await self.get_daily_stats(session)
        current_cost = daily_stats.total_cost_usd

        if self.daily_cost_limit_usd > Decimal("0"):
            percentage_used = (current_cost / self.daily_cost_limit_usd) * Decimal("100")
        else:
            percentage_used = Decimal("0")

        # Round to 2 decimal places
        percentage_used = percentage_used.quantize(Decimal("0.01"))

        if percentage_used >= Decimal("100"):
            status = "exceeded"
            logger.warning(
                "Daily LLM cost limit exceeded",
                current_cost=str(current_cost),
                limit=str(self.daily_cost_limit_usd),
                percentage_used=str(percentage_used),
            )
        elif percentage_used >= WARNING_THRESHOLD_PERCENT:
            status = "warning"
            logger.warning(
                "Approaching daily LLM cost limit",
                current_cost=str(current_cost),
                limit=str(self.daily_cost_limit_usd),
                percentage_used=str(percentage_used),
            )
        else:
            status = "ok"

        return CostStatus(
            status=status,
            current_cost=current_cost,
            limit=self.daily_cost_limit_usd,
            percentage_used=percentage_used,
        )


def format_llm_stats(
    daily: DailyStats,
    weekly: WeeklyStats,
    monthly: MonthlyStats,
) -> str:
    """Format LLM usage statistics for Telegram display.

    Args:
        daily: Daily statistics.
        weekly: Weekly statistics.
        monthly: Monthly statistics.

    Returns:
        Formatted string suitable for Telegram message.
    """

    def format_tokens(tokens: int) -> str:
        """Format token count with thousands separator."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.2f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.1f}K"
        return str(tokens)

    def format_cost(cost: Decimal) -> str:
        """Format cost with dollar sign."""
        return f"${cost:.4f}"

    # Build formatted output
    lines = [
        "LLM Usage Statistics",
        "",
        "Today:",
        f"  Tokens: {format_tokens(daily.total_tokens)}",
        f"  Cost: {format_cost(daily.total_cost_usd)}",
        f"  Posts: {daily.posts_processed}",
        f"  Avg tokens/post: {daily.avg_tokens_per_post}",
        "",
        f"This Week ({weekly.week_start} - {weekly.week_end}):",
        f"  Tokens: {format_tokens(weekly.total_tokens)}",
        f"  Cost: {format_cost(weekly.total_cost_usd)}",
        f"  Posts: {weekly.posts_processed}",
        "",
        f"This Month ({monthly.year}-{monthly.month:02d}):",
        f"  Tokens: {format_tokens(monthly.total_tokens)}",
        f"  Cost: {format_cost(monthly.total_cost_usd)}",
        f"  Posts: {monthly.posts_processed}",
    ]

    return "\n".join(lines)


# Public exports
__all__ = [
    "GROQ_PRICING",
    "estimate_cost",
    "CostTracker",
    "DailyStats",
    "WeeklyStats",
    "MonthlyStats",
    "CostStatus",
    "format_llm_stats",
]

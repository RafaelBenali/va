"""
LLM Integration Module (WS-5.1, WS-5.3, WS-5.4, WS-5.7)

Provides LLM client integrations for post enrichment.
Currently supports Groq as the primary provider.

Usage:
    from src.tnse.llm import GroqClient, CompletionResult, EnrichmentService

    async with GroqClient(api_key="your-key") as client:
        result = await client.complete("Hello!")
        print(result.content)

    # For post enrichment:
    service = EnrichmentService(llm_client=client)
    enrichment = await service.enrich_post(post_id=123, text="Post content...")

    # For Celery tasks (WS-5.4):
    from src.tnse.llm import tasks
    tasks.enrich_post.delay(post_id=123)

    # For cost tracking (WS-5.7):
    from src.tnse.llm import CostTracker
    tracker = CostTracker()
    await tracker.log_usage(session, model="qwen-qwq-32b",
                            prompt_tokens=1000, completion_tokens=500,
                            task_name="enrich_post", posts_processed=1)
"""

from src.tnse.llm.base import CompletionResult, LLMProvider
from src.tnse.llm.groq_client import (
    GroqClient,
    GroqConfigurationError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    JSONParseError,
    RateLimiter,
)
from src.tnse.llm.enrichment_service import (
    EnrichmentResult,
    EnrichmentService,
    EnrichmentSettings,
    ENRICHMENT_PROMPT,
)
# Import tasks module for easy access
from src.tnse.llm import tasks
# Import cost tracking module (WS-5.7)
from src.tnse.llm import cost_tracker
from src.tnse.llm.cost_tracker import (
    CostTracker,
    CostStatus,
    DailyStats,
    WeeklyStats,
    MonthlyStats,
    GROQ_PRICING,
    estimate_cost,
    format_llm_stats,
)

__all__ = [
    # Base classes
    "LLMProvider",
    "CompletionResult",
    # Groq client
    "GroqClient",
    "RateLimiter",
    # Enrichment service (WS-5.3)
    "EnrichmentResult",
    "EnrichmentService",
    "EnrichmentSettings",
    "ENRICHMENT_PROMPT",
    # Celery tasks (WS-5.4)
    "tasks",
    # Cost tracking (WS-5.7)
    "cost_tracker",
    "CostTracker",
    "CostStatus",
    "DailyStats",
    "WeeklyStats",
    "MonthlyStats",
    "GROQ_PRICING",
    "estimate_cost",
    "format_llm_stats",
    # Exceptions
    "GroqConfigurationError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "JSONParseError",
]

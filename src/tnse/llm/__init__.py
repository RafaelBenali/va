"""
LLM Integration Module (WS-5.1, WS-5.3, WS-5.4)

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
    # Exceptions
    "GroqConfigurationError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "JSONParseError",
]

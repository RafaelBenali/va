"""
LLM Integration Module (WS-5.1, WS-5.3)

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
    # Exceptions
    "GroqConfigurationError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "JSONParseError",
]

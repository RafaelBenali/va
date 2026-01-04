"""
LLM Integration Module (WS-5.1)

Provides LLM client integrations for post enrichment.
Currently supports Groq as the primary provider.

Usage:
    from src.tnse.llm import GroqClient, CompletionResult

    async with GroqClient(api_key="your-key") as client:
        result = await client.complete("Hello!")
        print(result.content)
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

__all__ = [
    # Base classes
    "LLMProvider",
    "CompletionResult",
    # Groq client
    "GroqClient",
    "RateLimiter",
    # Exceptions
    "GroqConfigurationError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "JSONParseError",
]

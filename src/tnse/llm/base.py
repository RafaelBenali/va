"""
Base LLM Provider Abstraction (WS-5.1)

Defines the interface that all LLM providers must implement.
This allows for easy swapping between providers (Groq, OpenAI, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Self


@dataclass
class CompletionResult:
    """Result from an LLM completion request.

    Attributes:
        content: The generated text content
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used (prompt + completion)
        model: The model used for generation
        duration_ms: Time taken for the request in milliseconds
        created_at: Timestamp when the result was created
        parsed_json: Parsed JSON if the response was in JSON format
    """

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str = ""
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parsed_json: dict[str, Any] | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM provider implementations must inherit from this class
    and implement its abstract methods.
    """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """Generate a text completion.

        Args:
            prompt: The user prompt to complete
            system_message: Optional system message for context
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional max tokens override

        Returns:
            CompletionResult with the generated text and metadata
        """
        ...

    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """Generate a JSON completion with response format enforcement.

        Args:
            prompt: The user prompt to complete
            system_message: Optional system message for context
            temperature: Optional temperature override (0.0-1.0)
            max_tokens: Optional max tokens override

        Returns:
            CompletionResult with the generated JSON and parsed_json field

        Raises:
            JSONParseError: If the response cannot be parsed as valid JSON
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available and properly configured.

        Returns:
            True if the provider is ready to use, False otherwise
        """
        ...

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        pass

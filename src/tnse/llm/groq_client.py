"""
Groq Client Integration (WS-5.1)

Async client for Groq API with:
- Rate limiting (respects 30 RPM free tier)
- JSON mode support for structured extraction
- Error handling and retries
- Base abstraction implementation
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Self

import groq
from groq import AsyncGroq

from src.tnse.core.config import GroqSettings
from src.tnse.llm.base import CompletionResult, LLMProvider


# Custom exceptions
class GroqError(Exception):
    """Base exception for Groq-related errors."""

    pass


class GroqConfigurationError(GroqError):
    """Raised when Groq is not properly configured."""

    pass


class GroqAuthenticationError(GroqError):
    """Raised when authentication fails."""

    pass


class GroqRateLimitError(GroqError):
    """Raised when rate limit is exceeded and retries exhausted."""

    pass


class GroqTimeoutError(GroqError):
    """Raised when a request times out."""

    pass


class JSONParseError(GroqError):
    """Raised when JSON response cannot be parsed."""

    pass


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API calls.

    Ensures we don't exceed the requests per minute limit.
    Uses a sliding window approach.
    """

    requests_per_minute: int
    _last_request_time: float = 0.0
    _lock: asyncio.Lock | None = None

    def __post_init__(self) -> None:
        """Initialize the lock after dataclass init."""
        self._lock = asyncio.Lock()

    @property
    def min_interval(self) -> float:
        """Minimum interval between requests in seconds."""
        return 60.0 / self.requests_per_minute

    async def acquire(self) -> None:
        """Acquire permission to make a request, waiting if necessary."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            wait_time = self.min_interval - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            self._last_request_time = time.monotonic()


class GroqClient(LLMProvider):
    """Async client for Groq API.

    Implements the LLMProvider interface with:
    - Rate limiting to respect API limits
    - JSON mode for structured outputs
    - Automatic retries with exponential backoff
    - Error handling for common failure modes

    Usage:
        async with GroqClient(api_key="your-key") as client:
            result = await client.complete("Hello, world!")
            print(result.content)

        # Or with JSON mode:
        result = await client.complete_json("Return a JSON object")
        print(result.parsed_json)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "qwen-qwq-32b",
        max_tokens: int = 1024,
        temperature: float = 0.1,
        rate_limit_rpm: int = 30,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Groq client.

        Args:
            api_key: Groq API key (required)
            model: Model ID to use
            max_tokens: Default max tokens for completions
            temperature: Default temperature for completions
            rate_limit_rpm: Rate limit in requests per minute
            timeout_seconds: Request timeout in seconds
            max_retries: Max retries on transient failures

        Raises:
            GroqConfigurationError: If API key is missing
        """
        if api_key is None:
            raise GroqConfigurationError("API key is required")

        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.rate_limit_rpm = rate_limit_rpm
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        self._rate_limiter = RateLimiter(requests_per_minute=rate_limit_rpm)
        self._client: AsyncGroq | None = None
        self._initialized = False
        self._closed = False

    @classmethod
    def from_settings(cls, settings: GroqSettings) -> "GroqClient":
        """Create a GroqClient from settings.

        Args:
            settings: GroqSettings instance

        Returns:
            Configured GroqClient instance
        """
        return cls(
            api_key=settings.api_key,
            model=settings.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            rate_limit_rpm=settings.rate_limit_rpm,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )

    async def __aenter__(self) -> Self:
        """Initialize the async client on context entry."""
        self._client = AsyncGroq(api_key=self.api_key, timeout=self.timeout_seconds)
        self._initialized = True
        self._closed = False
        return self

    async def __aexit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any
    ) -> None:
        """Clean up the async client on context exit."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._closed = True

    async def _ensure_client(self) -> AsyncGroq:
        """Ensure the client is initialized.

        Returns:
            The initialized AsyncGroq client

        Raises:
            GroqConfigurationError: If client is not initialized
        """
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key, timeout=self.timeout_seconds)
            self._initialized = True
        return self._client

    async def _make_request(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[Any, int]:
        """Make an API request with rate limiting and retries.

        Args:
            messages: Chat messages
            response_format: Optional response format (e.g., {"type": "json_object"})
            temperature: Temperature override
            max_tokens: Max tokens override

        Returns:
            Tuple of (API response, duration in ms)

        Raises:
            GroqAuthenticationError: On auth failure
            GroqRateLimitError: On rate limit after retries
            GroqTimeoutError: On timeout
        """
        client = await self._ensure_client()

        last_error: Exception | None = None
        retry_delay = 1.0  # Start with 1 second delay

        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                await self._rate_limiter.acquire()

                start_time = time.monotonic()

                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else self.temperature,
                    "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
                }

                if response_format is not None:
                    kwargs["response_format"] = response_format

                response = await client.chat.completions.create(**kwargs)

                duration_ms = int((time.monotonic() - start_time) * 1000)
                return response, duration_ms

            except groq.AuthenticationError as error:
                raise GroqAuthenticationError(f"Authentication failed: {error}") from error

            except groq.RateLimitError as error:
                last_error = error
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

            except asyncio.TimeoutError as error:
                raise GroqTimeoutError(f"Request timed out: {error}") from error

            except Exception as error:
                # Unexpected error, don't retry
                raise GroqError(f"Unexpected error: {error}") from error

        # All retries exhausted
        raise GroqRateLimitError(
            f"Rate limit exceeded after {self.max_retries} retries: {last_error}"
        )

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
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            CompletionResult with the generated text
        """
        messages: list[dict[str, str]] = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        response, duration_ms = await self._make_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return CompletionResult(
            content=response.choices[0].message.content or "",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model=getattr(response, "model", self.model),
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )

    async def complete_json(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> CompletionResult:
        """Generate a JSON completion.

        Args:
            prompt: The user prompt to complete
            system_message: Optional system message for context
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            CompletionResult with parsed_json field populated

        Raises:
            JSONParseError: If response cannot be parsed as JSON
        """
        messages: list[dict[str, str]] = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        response, duration_ms = await self._make_request(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""

        # Parse JSON
        try:
            parsed_json = json.loads(content)
        except json.JSONDecodeError as error:
            raise JSONParseError(f"Failed to parse JSON response: {error}") from error

        return CompletionResult(
            content=content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            model=getattr(response, "model", self.model),
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
            parsed_json=parsed_json,
        )

    async def is_available(self) -> bool:
        """Check if the client is available and configured.

        Returns:
            True if API key is configured, False otherwise
        """
        return self.api_key is not None

    async def health_check(self) -> bool:
        """Perform a health check by making a simple API call.

        Returns:
            True if the API is reachable and responding, False otherwise
        """
        try:
            await self.complete(
                prompt="Say OK",
                max_tokens=5,
            )
            return True
        except Exception:
            return False

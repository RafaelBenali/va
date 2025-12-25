"""
TNSE Rate Limiter Module

Provides rate limiting and exponential backoff for Telegram API calls.

Work Stream: WS-1.4 - Telegram API Integration

Requirements addressed:
- Handle rate limiting with backoff
- NFR-R-002: Automatic retry for transient API failures
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

# Type variable for generic function return type
T = TypeVar("T")


class FloodWaitError(Exception):
    """Exception raised when Telegram rate limits are hit.

    Telegram's FloodWait error indicates the client must wait
    a specified number of seconds before retrying.

    Attributes:
        seconds: Number of seconds to wait before retrying
    """

    def __init__(self, seconds: int) -> None:
        """Initialize FloodWaitError.

        Args:
            seconds: Number of seconds to wait
        """
        self.seconds = seconds
        super().__init__(f"Flood wait: must wait {seconds} seconds before retrying")


@dataclass
class ExponentialBackoff:
    """Exponential backoff calculator with optional jitter.

    Calculates delay times that increase exponentially with each retry,
    with optional random jitter to prevent thundering herd problems.

    Attributes:
        initial_delay: Starting delay in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Multiplier for each successive retry
        max_retries: Maximum number of retries allowed
        jitter: Whether to add random jitter to delays
    """

    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    max_retries: int = 5
    jitter: bool = False

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add jitter: random value between 50% and 150% of calculated delay
            jitter_factor = 0.5 + random.random()
            delay = delay * jitter_factor

        return delay


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API calls.

    Implements a token bucket algorithm to limit the rate of API calls.
    Supports both per-second and per-minute limits.

    Attributes:
        max_requests_per_second: Maximum requests allowed per second
        max_requests_per_minute: Maximum requests allowed per minute
    """

    max_requests_per_second: int = 5
    max_requests_per_minute: int = 100

    _second_tokens: int = field(default=0, init=False, repr=False)
    _minute_tokens: int = field(default=0, init=False, repr=False)
    _last_second: float = field(default=0.0, init=False, repr=False)
    _last_minute: float = field(default=0.0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize token buckets."""
        self._second_tokens = self.max_requests_per_second
        self._minute_tokens = self.max_requests_per_minute
        self._last_second = time.time()
        self._last_minute = time.time()

    async def acquire(self) -> bool:
        """Acquire a token from the rate limiter.

        Waits if necessary until a token is available.

        Returns:
            True when token is acquired
        """
        async with self._lock:
            current_time = time.time()

            # Refill second tokens
            elapsed_seconds = current_time - self._last_second
            if elapsed_seconds >= 1.0:
                self._second_tokens = self.max_requests_per_second
                self._last_second = current_time

            # Refill minute tokens
            elapsed_minutes = current_time - self._last_minute
            if elapsed_minutes >= 60.0:
                self._minute_tokens = self.max_requests_per_minute
                self._last_minute = current_time

            # Check if we have tokens available
            if self._second_tokens <= 0:
                wait_time = 1.0 - elapsed_seconds
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    self._second_tokens = self.max_requests_per_second
                    self._last_second = time.time()

            if self._minute_tokens <= 0:
                wait_time = 60.0 - elapsed_minutes
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    self._minute_tokens = self.max_requests_per_minute
                    self._last_minute = time.time()

            # Consume tokens
            self._second_tokens -= 1
            self._minute_tokens -= 1

        return True

    async def __aenter__(self) -> "RateLimiter":
        """Async context manager entry - acquires token."""
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Async context manager exit."""
        pass


def retryable(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to make async functions retryable with exponential backoff.

    Automatically retries failed async function calls with exponential
    backoff between attempts. Handles FloodWaitError specially by
    waiting the specified time.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        multiplier: Delay multiplier for each retry
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            backoff = ExponentialBackoff(
                initial_delay=initial_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                max_retries=max_retries,
                jitter=jitter,
            )

            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except FloodWaitError as flood_error:
                    # Handle Telegram's FloodWait specifically
                    if attempt >= max_retries:
                        raise
                    await asyncio.sleep(flood_error.seconds)
                    last_exception = flood_error
                except retryable_exceptions as error:
                    if attempt >= max_retries:
                        raise
                    delay = backoff.get_delay(attempt)
                    await asyncio.sleep(delay)
                    last_exception = error

            # Should not reach here, but raise last exception if we do
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retryable wrapper")

        return wrapper

    return decorator

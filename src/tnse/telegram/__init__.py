"""
TNSE Telegram Integration Module

Provides Telegram MTProto API integration for channel access and content collection.

Work Stream: WS-1.4 - Telegram API Integration

Public API:
- TelegramClient: Abstract base class for Telegram client implementations
- TelethonClient: Telethon-based implementation of TelegramClient
- TelegramClientConfig: Configuration for Telegram client
- ChannelInfo, MessageInfo, MediaInfo: Data transfer objects
- ChannelService: High-level service for channel operations
- ChannelValidationResult: Result of channel validation
- RateLimiter: Token bucket rate limiter
- ExponentialBackoff: Backoff calculator
- FloodWaitError: Exception for Telegram rate limits
- retryable: Decorator for automatic retries
"""

from src.tnse.telegram.channel_service import (
    ChannelService,
    ChannelValidationResult,
)
from src.tnse.telegram.client import (
    ChannelInfo,
    MediaInfo,
    MessageInfo,
    TelegramClient,
    TelegramClientConfig,
    TelethonClient,
)
from src.tnse.telegram.rate_limiter import (
    ExponentialBackoff,
    FloodWaitError,
    RateLimiter,
    retryable,
)

__all__ = [
    # Client
    "TelegramClient",
    "TelethonClient",
    "TelegramClientConfig",
    # Data objects
    "ChannelInfo",
    "MessageInfo",
    "MediaInfo",
    # Service
    "ChannelService",
    "ChannelValidationResult",
    # Rate limiting
    "RateLimiter",
    "ExponentialBackoff",
    "FloodWaitError",
    "retryable",
]

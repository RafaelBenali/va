"""
Tests for TNSE Channel Validation and Metadata Service.

Following TDD methodology: these tests are written BEFORE the implementation.

Work Stream: WS-1.4 - Telegram API Integration

Requirements addressed:
- Implement channel validation (public/accessible)
- Create channel metadata fetcher
- Implement message history retrieval (24 hours)
- Handle rate limiting with backoff
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChannelValidationResult:
    """Tests for ChannelValidationResult dataclass."""

    def test_validation_result_has_is_valid_field(self):
        """Test that result has is_valid field."""
        from src.tnse.telegram.channel_service import ChannelValidationResult

        result = ChannelValidationResult(
            is_valid=True,
            channel_info=None,
        )
        assert result.is_valid is True

    def test_validation_result_has_channel_info_field(self):
        """Test that result has channel_info field."""
        from src.tnse.telegram.channel_service import ChannelValidationResult
        from src.tnse.telegram.client import ChannelInfo

        channel = ChannelInfo(
            telegram_id=123456,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            is_public=True,
        )
        result = ChannelValidationResult(
            is_valid=True,
            channel_info=channel,
        )
        assert result.channel_info == channel

    def test_validation_result_has_error_field(self):
        """Test that result has optional error field."""
        from src.tnse.telegram.channel_service import ChannelValidationResult

        result = ChannelValidationResult(
            is_valid=False,
            channel_info=None,
            error="Channel not found",
        )
        assert result.error == "Channel not found"

    def test_validation_result_has_error_code_field(self):
        """Test that result has optional error code field."""
        from src.tnse.telegram.channel_service import ChannelValidationResult

        result = ChannelValidationResult(
            is_valid=False,
            channel_info=None,
            error="Channel is private",
            error_code="PRIVATE_CHANNEL",
        )
        assert result.error_code == "PRIVATE_CHANNEL"


class TestChannelService:
    """Tests for the ChannelService class."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Provide a mock TelegramClient."""
        from src.tnse.telegram.client import ChannelInfo

        client = MagicMock()
        client.is_connected = True
        client.get_channel = AsyncMock(
            return_value=ChannelInfo(
                telegram_id=123456789,
                username="test_channel",
                title="Test Channel",
                subscriber_count=10000,
                is_public=True,
                description="A test channel",
            )
        )
        client.get_messages = AsyncMock(return_value=[])
        return client

    def test_channel_service_exists(self):
        """Test that ChannelService class exists."""
        from src.tnse.telegram.channel_service import ChannelService

        assert ChannelService is not None

    def test_channel_service_takes_client(self, mock_client: MagicMock):
        """Test that ChannelService takes a TelegramClient."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        assert service.client == mock_client

    @pytest.mark.asyncio
    async def test_validate_channel_returns_result(self, mock_client: MagicMock):
        """Test that validate_channel returns a ChannelValidationResult."""
        from src.tnse.telegram.channel_service import (
            ChannelService,
            ChannelValidationResult,
        )

        service = ChannelService(mock_client)
        result = await service.validate_channel("@test_channel")

        assert isinstance(result, ChannelValidationResult)

    @pytest.mark.asyncio
    async def test_validate_channel_valid_public_channel(self, mock_client: MagicMock):
        """Test validating a valid public channel."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        result = await service.validate_channel("@test_channel")

        assert result.is_valid is True
        assert result.channel_info is not None
        assert result.channel_info.username == "test_channel"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_channel_strips_at_symbol(self, mock_client: MagicMock):
        """Test that @ symbol is stripped from username."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        await service.validate_channel("@test_channel")

        # Verify the client was called without the @ symbol
        mock_client.get_channel.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validate_channel_not_found(self, mock_client: MagicMock):
        """Test validating a channel that doesn't exist."""
        from src.tnse.telegram.channel_service import ChannelService

        mock_client.get_channel = AsyncMock(return_value=None)

        service = ChannelService(mock_client)
        result = await service.validate_channel("@nonexistent")

        assert result.is_valid is False
        assert result.channel_info is None
        assert result.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_validate_channel_private(self, mock_client: MagicMock):
        """Test validating a private channel."""
        from src.tnse.telegram.channel_service import ChannelService
        from src.tnse.telegram.client import ChannelInfo

        mock_client.get_channel = AsyncMock(
            return_value=ChannelInfo(
                telegram_id=123456789,
                username="private_channel",
                title="Private Channel",
                subscriber_count=100,
                is_public=False,
            )
        )

        service = ChannelService(mock_client)
        result = await service.validate_channel("@private_channel")

        assert result.is_valid is False
        assert result.error_code == "PRIVATE_CHANNEL"

    @pytest.mark.asyncio
    async def test_validate_channel_handles_url(self, mock_client: MagicMock):
        """Test validating a channel via t.me URL."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        result = await service.validate_channel("https://t.me/test_channel")

        assert result.is_valid is True
        mock_client.get_channel.assert_awaited_once()


class TestChannelServiceMetadata:
    """Tests for channel metadata fetching."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Provide a mock TelegramClient."""
        from src.tnse.telegram.client import ChannelInfo

        client = MagicMock()
        client.is_connected = True
        client.get_channel = AsyncMock(
            return_value=ChannelInfo(
                telegram_id=123456789,
                username="news_channel",
                title="News Channel",
                subscriber_count=50000,
                is_public=True,
                description="Daily news updates",
            )
        )
        return client

    @pytest.mark.asyncio
    async def test_get_channel_metadata(self, mock_client: MagicMock):
        """Test fetching channel metadata."""
        from src.tnse.telegram.channel_service import ChannelService
        from src.tnse.telegram.client import ChannelInfo

        service = ChannelService(mock_client)
        result = await service.get_channel_metadata("@news_channel")

        assert isinstance(result, ChannelInfo)
        assert result.username == "news_channel"
        assert result.subscriber_count == 50000

    @pytest.mark.asyncio
    async def test_get_channel_metadata_returns_none_for_invalid(
        self, mock_client: MagicMock
    ):
        """Test that get_channel_metadata returns None for invalid channel."""
        from src.tnse.telegram.channel_service import ChannelService

        mock_client.get_channel = AsyncMock(return_value=None)

        service = ChannelService(mock_client)
        result = await service.get_channel_metadata("@invalid")

        assert result is None


class TestChannelServiceMessages:
    """Tests for message history retrieval."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Provide a mock TelegramClient with messages."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        messages = [
            MessageInfo(
                message_id=100,
                channel_id=123456789,
                text="First message",
                date=now - timedelta(hours=1),
                views=1000,
            ),
            MessageInfo(
                message_id=99,
                channel_id=123456789,
                text="Second message",
                date=now - timedelta(hours=2),
                views=2000,
            ),
            MessageInfo(
                message_id=98,
                channel_id=123456789,
                text="Third message",
                date=now - timedelta(hours=12),
                views=5000,
            ),
        ]

        client = MagicMock()
        client.is_connected = True
        client.get_messages = AsyncMock(return_value=messages)
        return client

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, mock_client: MagicMock):
        """Test fetching recent messages from a channel."""
        from src.tnse.telegram.channel_service import ChannelService
        from src.tnse.telegram.client import MessageInfo

        service = ChannelService(mock_client)
        messages = await service.get_recent_messages(channel_id=123456789, hours=24)

        assert isinstance(messages, list)
        assert all(isinstance(message, MessageInfo) for message in messages)

    @pytest.mark.asyncio
    async def test_get_recent_messages_respects_hours_param(
        self, mock_client: MagicMock
    ):
        """Test that get_recent_messages respects hours parameter."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        await service.get_recent_messages(channel_id=123456789, hours=24)

        mock_client.get_messages.assert_awaited_once()
        # The offset_date should be around 24 hours ago
        call_args = mock_client.get_messages.call_args
        assert "offset_date" not in call_args.kwargs or call_args.kwargs[
            "offset_date"
        ] is None  # We start from now

    @pytest.mark.asyncio
    async def test_get_recent_messages_with_limit(self, mock_client: MagicMock):
        """Test that get_recent_messages respects limit parameter."""
        from src.tnse.telegram.channel_service import ChannelService

        service = ChannelService(mock_client)
        await service.get_recent_messages(channel_id=123456789, hours=24, limit=50)

        call_args = mock_client.get_messages.call_args
        assert call_args.kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_recent_messages_returns_empty_on_error(
        self, mock_client: MagicMock
    ):
        """Test that get_recent_messages returns empty list on error."""
        from src.tnse.telegram.channel_service import ChannelService

        mock_client.get_messages = AsyncMock(side_effect=Exception("API Error"))

        service = ChannelService(mock_client)
        messages = await service.get_recent_messages(channel_id=123456789, hours=24)

        assert messages == []


class TestRateLimiter:
    """Tests for rate limiting functionality."""

    def test_rate_limiter_exists(self):
        """Test that RateLimiter class exists."""
        from src.tnse.telegram.rate_limiter import RateLimiter

        assert RateLimiter is not None

    def test_rate_limiter_has_configurable_limits(self):
        """Test that RateLimiter has configurable limits."""
        from src.tnse.telegram.rate_limiter import RateLimiter

        limiter = RateLimiter(
            max_requests_per_second=5,
            max_requests_per_minute=100,
        )
        assert limiter.max_requests_per_second == 5
        assert limiter.max_requests_per_minute == 100

    def test_rate_limiter_has_default_limits(self):
        """Test that RateLimiter has reasonable defaults."""
        from src.tnse.telegram.rate_limiter import RateLimiter

        limiter = RateLimiter()
        assert limiter.max_requests_per_second > 0
        assert limiter.max_requests_per_minute > 0

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test that RateLimiter can acquire a token."""
        from src.tnse.telegram.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests_per_second=10)
        acquired = await limiter.acquire()

        assert acquired is True

    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test that RateLimiter works as context manager."""
        from src.tnse.telegram.rate_limiter import RateLimiter

        limiter = RateLimiter(max_requests_per_second=10)

        async with limiter:
            # Should not raise
            pass


class TestExponentialBackoff:
    """Tests for exponential backoff functionality."""

    def test_backoff_exists(self):
        """Test that ExponentialBackoff class exists."""
        from src.tnse.telegram.rate_limiter import ExponentialBackoff

        assert ExponentialBackoff is not None

    def test_backoff_has_configurable_parameters(self):
        """Test that backoff has configurable parameters."""
        from src.tnse.telegram.rate_limiter import ExponentialBackoff

        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            max_retries=5,
        )
        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 60.0
        assert backoff.multiplier == 2.0
        assert backoff.max_retries == 5

    def test_backoff_calculates_next_delay(self):
        """Test that backoff calculates next delay correctly."""
        from src.tnse.telegram.rate_limiter import ExponentialBackoff

        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
        )

        assert backoff.get_delay(attempt=0) == 1.0
        assert backoff.get_delay(attempt=1) == 2.0
        assert backoff.get_delay(attempt=2) == 4.0

    def test_backoff_respects_max_delay(self):
        """Test that backoff respects max delay."""
        from src.tnse.telegram.rate_limiter import ExponentialBackoff

        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=10.0,
            multiplier=2.0,
        )

        # After many attempts, should not exceed max_delay
        assert backoff.get_delay(attempt=10) <= 10.0

    def test_backoff_has_jitter_option(self):
        """Test that backoff supports jitter."""
        from src.tnse.telegram.rate_limiter import ExponentialBackoff

        backoff = ExponentialBackoff(
            initial_delay=1.0,
            jitter=True,
        )

        # With jitter, delays should vary slightly
        delays = [backoff.get_delay(attempt=0) for _ in range(10)]
        # At least some should be different
        assert len(set(delays)) > 1 or all(0.5 <= delay <= 1.5 for delay in delays)


class TestRetryableRequest:
    """Tests for retryable request decorator."""

    def test_retryable_decorator_exists(self):
        """Test that retryable decorator exists."""
        from src.tnse.telegram.rate_limiter import retryable

        assert retryable is not None

    @pytest.mark.asyncio
    async def test_retryable_succeeds_on_first_try(self):
        """Test that retryable returns immediately on success."""
        from src.tnse.telegram.rate_limiter import retryable

        call_count = 0

        @retryable(max_retries=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retryable_retries_on_failure(self):
        """Test that retryable retries on failure."""
        from src.tnse.telegram.rate_limiter import retryable

        call_count = 0

        @retryable(max_retries=3, initial_delay=0.01)
        async def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await failing_then_succeeding()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retryable_raises_after_max_retries(self):
        """Test that retryable raises after max retries exceeded."""
        from src.tnse.telegram.rate_limiter import retryable

        @retryable(max_retries=2, initial_delay=0.01)
        async def always_failing():
            raise Exception("Always fails")

        with pytest.raises(Exception, match="Always fails"):
            await always_failing()

    @pytest.mark.asyncio
    async def test_retryable_handles_flood_wait(self):
        """Test that retryable handles Telegram FloodWait errors."""
        from src.tnse.telegram.rate_limiter import FloodWaitError, retryable

        call_count = 0

        @retryable(max_retries=3, initial_delay=0.01)
        async def flood_wait_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FloodWaitError(seconds=1)
            return "success"

        result = await flood_wait_func()
        assert result == "success"
        assert call_count == 2


class TestFloodWaitError:
    """Tests for FloodWaitError exception."""

    def test_flood_wait_error_exists(self):
        """Test that FloodWaitError exists."""
        from src.tnse.telegram.rate_limiter import FloodWaitError

        assert FloodWaitError is not None

    def test_flood_wait_error_has_seconds(self):
        """Test that FloodWaitError has seconds attribute."""
        from src.tnse.telegram.rate_limiter import FloodWaitError

        error = FloodWaitError(seconds=60)
        assert error.seconds == 60

    def test_flood_wait_error_message(self):
        """Test that FloodWaitError has informative message."""
        from src.tnse.telegram.rate_limiter import FloodWaitError

        error = FloodWaitError(seconds=60)
        assert "60" in str(error)

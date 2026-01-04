"""
Tests for Groq Client Integration (WS-5.1)

Following TDD methodology: these tests are written BEFORE implementation.
The tests validate:
1. Groq settings configuration
2. Async client creation and management
3. Rate limiting (30 RPM free tier)
4. JSON mode support for structured extraction
5. Error handling and retries
6. Base abstraction for future LLM providers
"""

import asyncio
import os
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGroqSettings:
    """Tests for Groq configuration settings."""

    def test_default_groq_settings(self):
        """Test that Groq settings have sensible defaults."""
        from src.tnse.core.config import GroqSettings

        settings = GroqSettings()

        assert settings.api_key is None
        assert settings.model == "qwen-qwq-32b"
        assert settings.max_tokens == 1024
        assert settings.temperature == 0.1
        assert settings.enabled is False
        assert settings.rate_limit_rpm == 30
        assert settings.timeout_seconds == 30.0
        assert settings.max_retries == 3

    def test_groq_settings_from_environment(self):
        """Test that Groq settings can be loaded from environment variables."""
        from src.tnse.core.config import GroqSettings

        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "test-api-key-123",
                "GROQ_MODEL": "llama-3.1-70b-versatile",
                "GROQ_MAX_TOKENS": "2048",
                "GROQ_TEMPERATURE": "0.5",
                "GROQ_ENABLED": "true",
                "GROQ_RATE_LIMIT_RPM": "60",
                "GROQ_TIMEOUT_SECONDS": "45.0",
                "GROQ_MAX_RETRIES": "5",
            },
        ):
            settings = GroqSettings()

            assert settings.api_key == "test-api-key-123"
            assert settings.model == "llama-3.1-70b-versatile"
            assert settings.max_tokens == 2048
            assert settings.temperature == 0.5
            assert settings.enabled is True
            assert settings.rate_limit_rpm == 60
            assert settings.timeout_seconds == 45.0
            assert settings.max_retries == 5

    def test_groq_settings_in_main_settings(self):
        """Test that Groq settings are included in main Settings class."""
        from src.tnse.core.config import Settings

        settings = Settings()

        assert hasattr(settings, "groq")
        assert settings.groq is not None
        assert settings.groq.model == "qwen-qwq-32b"


class TestGroqClientCreation:
    """Tests for Groq client creation and lifecycle."""

    def test_client_creation_with_api_key(self):
        """Test that GroqClient can be created with an API key."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key")

        assert client is not None
        assert client.api_key == "test-key"

    def test_client_creation_without_api_key_raises_error(self):
        """Test that GroqClient raises error when API key is missing."""
        from src.tnse.llm.groq_client import GroqClient, GroqConfigurationError

        with pytest.raises(GroqConfigurationError, match="API key is required"):
            GroqClient(api_key=None)

    def test_client_creation_from_settings(self):
        """Test that GroqClient can be created from settings."""
        from src.tnse.llm.groq_client import GroqClient

        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "settings-key",
                "GROQ_MODEL": "test-model",
            },
        ):
            from src.tnse.core.config import GroqSettings

            settings = GroqSettings()
            client = GroqClient.from_settings(settings)

            assert client.api_key == "settings-key"
            assert client.model == "test-model"

    def test_client_default_model(self):
        """Test that client uses default model from settings."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key")

        assert client.model == "qwen-qwq-32b"

    def test_client_custom_model(self):
        """Test that client can use a custom model."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key", model="llama-3.1-70b-versatile")

        assert client.model == "llama-3.1-70b-versatile"


class TestGroqClientAsyncContext:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_client_as_async_context_manager(self):
        """Test that GroqClient can be used as an async context manager."""
        from src.tnse.llm.groq_client import GroqClient

        async with GroqClient(api_key="test-key") as client:
            assert client is not None
            assert client._initialized is True

    @pytest.mark.asyncio
    async def test_client_cleanup_on_exit(self):
        """Test that client resources are cleaned up on context exit."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key")
        async with client:
            pass
        # After exit, internal client should be closed
        assert client._closed is True


class TestGroqClientCompletion:
    """Tests for chat completion functionality."""

    @pytest.mark.asyncio
    async def test_simple_completion(self):
        """Test basic chat completion request."""
        from src.tnse.llm.groq_client import GroqClient, CompletionResult

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                result = await client.complete("Say hello")

                assert isinstance(result, CompletionResult)
                assert result.content == "Hello!"
                assert result.prompt_tokens == 10
                assert result.completion_tokens == 5
                assert result.total_tokens == 15

    @pytest.mark.asyncio
    async def test_completion_with_system_message(self):
        """Test completion with a system message."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=20, completion_tokens=5, total_tokens=25
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                await client.complete(
                    prompt="User message",
                    system_message="You are a helpful assistant.",
                )

                # Verify system message was included
                call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
                messages = call_kwargs["messages"]
                assert messages[0]["role"] == "system"
                assert messages[0]["content"] == "You are a helpful assistant."


class TestGroqClientJSONMode:
    """Tests for JSON mode support."""

    @pytest.mark.asyncio
    async def test_json_mode_completion(self):
        """Test completion with JSON mode enabled."""
        from src.tnse.llm.groq_client import GroqClient

        json_content = '{"name": "test", "value": 42}'
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=json_content))]
        mock_response.usage = MagicMock(
            prompt_tokens=15, completion_tokens=10, total_tokens=25
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                result = await client.complete_json(
                    prompt="Return JSON with name and value"
                )

                assert result.content == json_content
                assert result.parsed_json == {"name": "test", "value": 42}

    @pytest.mark.asyncio
    async def test_json_mode_sets_response_format(self):
        """Test that JSON mode sets correct response_format parameter."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="{}"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                await client.complete_json(prompt="Return JSON")

                call_kwargs = mock_groq_instance.chat.completions.create.call_args.kwargs
                assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_json_mode_parse_error_handling(self):
        """Test handling of invalid JSON responses."""
        from src.tnse.llm.groq_client import GroqClient, JSONParseError

        invalid_json = "This is not valid JSON"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=invalid_json))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                with pytest.raises(JSONParseError):
                    await client.complete_json(prompt="Return JSON")


class TestGroqClientRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test that rate limiter is initialized with correct limit."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key", rate_limit_rpm=30)

        assert client.rate_limit_rpm == 30
        assert client._rate_limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limiting_respects_rpm_limit(self):
        """Test that rate limiting respects requests per minute limit."""
        from src.tnse.llm.groq_client import GroqClient, RateLimiter

        # Test rate limiter directly
        limiter = RateLimiter(requests_per_minute=60)  # 1 per second

        # First request should be immediate
        start = time.monotonic()
        await limiter.acquire()
        first_duration = time.monotonic() - start
        assert first_duration < 0.1  # Should be nearly instant

        # Second request should wait approximately 1 second
        start = time.monotonic()
        await limiter.acquire()
        second_duration = time.monotonic() - start
        # Allow some tolerance, should wait ~1 second
        assert 0.9 <= second_duration <= 1.5

    @pytest.mark.asyncio
    async def test_client_applies_rate_limiting_on_requests(self):
        """Test that client applies rate limiting on completion requests."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            # Use a very low rate limit for testing
            async with GroqClient(api_key="test-key", rate_limit_rpm=60) as client:
                # Make two requests
                start = time.monotonic()
                await client.complete("First")
                await client.complete("Second")
                duration = time.monotonic() - start

                # Second request should have been delayed
                assert duration >= 0.9  # At least ~1 second delay


class TestGroqClientErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_error(self):
        """Test that client retries on rate limit errors from API."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )

        # Create a mock that fails first then succeeds
        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from groq import RateLimitError

                raise RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body=None,
                )
            return mock_response

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = mock_create

            async with GroqClient(api_key="test-key", max_retries=3) as client:
                result = await client.complete("Test prompt")

                assert result.content == "Success"
                assert call_count == 2  # One failure, one success

    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test handling of authentication errors."""
        from src.tnse.llm.groq_client import GroqClient, GroqAuthenticationError

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance

            from groq import AuthenticationError

            mock_groq_instance.chat.completions.create = AsyncMock(
                side_effect=AuthenticationError(
                    message="Invalid API key",
                    response=MagicMock(status_code=401),
                    body=None,
                )
            )

            async with GroqClient(api_key="invalid-key") as client:
                with pytest.raises(GroqAuthenticationError):
                    await client.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test handling of timeout errors."""
        from src.tnse.llm.groq_client import GroqClient, GroqTimeoutError

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance

            mock_groq_instance.chat.completions.create = AsyncMock(
                side_effect=asyncio.TimeoutError("Request timed out")
            )

            async with GroqClient(api_key="test-key", timeout_seconds=1.0) as client:
                with pytest.raises(GroqTimeoutError):
                    await client.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that error is raised when max retries are exceeded."""
        from src.tnse.llm.groq_client import GroqClient, GroqRateLimitError

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance

            from groq import RateLimitError

            mock_groq_instance.chat.completions.create = AsyncMock(
                side_effect=RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body=None,
                )
            )

            async with GroqClient(api_key="test-key", max_retries=2) as client:
                with pytest.raises(GroqRateLimitError):
                    await client.complete("Test prompt")


class TestGroqClientResponseTracking:
    """Tests for response metadata and tracking."""

    @pytest.mark.asyncio
    async def test_completion_result_includes_model(self):
        """Test that completion result includes the model used."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )
        mock_response.model = "qwen-qwq-32b"

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                result = await client.complete("Test")

                assert result.model == "qwen-qwq-32b"

    @pytest.mark.asyncio
    async def test_completion_result_includes_timing(self):
        """Test that completion result includes request timing."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )
        mock_response.model = "qwen-qwq-32b"

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                result = await client.complete("Test")

                assert result.duration_ms >= 0
                assert isinstance(result.created_at, datetime)


class TestLLMProviderAbstraction:
    """Tests for base LLM provider abstraction."""

    def test_base_provider_interface_exists(self):
        """Test that base LLM provider interface is defined."""
        from src.tnse.llm.base import LLMProvider, CompletionResult

        # Verify the abstract base class exists
        assert LLMProvider is not None
        assert CompletionResult is not None

    def test_groq_client_implements_provider_interface(self):
        """Test that GroqClient implements the LLMProvider interface."""
        from src.tnse.llm.base import LLMProvider
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key")

        assert isinstance(client, LLMProvider)

    def test_provider_has_required_methods(self):
        """Test that provider has all required abstract methods."""
        from src.tnse.llm.base import LLMProvider

        # Check that abstract methods are defined
        assert hasattr(LLMProvider, "complete")
        assert hasattr(LLMProvider, "complete_json")
        assert hasattr(LLMProvider, "is_available")


class TestGroqClientHealthCheck:
    """Tests for client health check functionality."""

    @pytest.mark.asyncio
    async def test_is_available_returns_true_when_configured(self):
        """Test that is_available returns True when properly configured."""
        from src.tnse.llm.groq_client import GroqClient

        client = GroqClient(api_key="test-key")

        assert await client.is_available() is True

    @pytest.mark.asyncio
    async def test_health_check_with_api_call(self):
        """Test health check that makes an actual API call."""
        from src.tnse.llm.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OK"))]
        mock_response.usage = MagicMock(
            prompt_tokens=5, completion_tokens=1, total_tokens=6
        )

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            async with GroqClient(api_key="test-key") as client:
                is_healthy = await client.health_check()

                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self):
        """Test that health check returns False on API error."""
        from src.tnse.llm.groq_client import GroqClient

        with patch("groq.AsyncGroq") as mock_groq:
            mock_groq_instance = AsyncMock()
            mock_groq.return_value = mock_groq_instance
            mock_groq_instance.chat.completions.create = AsyncMock(
                side_effect=Exception("API Error")
            )

            async with GroqClient(api_key="test-key") as client:
                is_healthy = await client.health_check()

                assert is_healthy is False

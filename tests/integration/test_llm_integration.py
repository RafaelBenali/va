"""
Integration Tests for LLM Module (WS-5.8)

End-to-end integration tests for the LLM enrichment pipeline.
These tests verify the complete flow from post content to enrichment storage.

Components tested:
- GroqClient with mocked API responses
- EnrichmentService processing full posts
- EnrichmentResult dataclass validation
- Rate limiting behavior
- Error handling across the pipeline

Note: These tests use mocked Groq API responses to avoid external dependencies
and ensure consistent test results.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMModuleImports:
    """Test that all LLM module components can be imported correctly."""

    def test_import_llm_module(self):
        """Test importing the main LLM module."""
        from src.tnse import llm
        assert llm is not None

    def test_import_groq_client(self):
        """Test importing GroqClient."""
        from src.tnse.llm import GroqClient
        assert GroqClient is not None

    def test_import_enrichment_service(self):
        """Test importing EnrichmentService."""
        from src.tnse.llm import EnrichmentService
        assert EnrichmentService is not None

    def test_import_enrichment_result(self):
        """Test importing EnrichmentResult."""
        from src.tnse.llm import EnrichmentResult
        assert EnrichmentResult is not None

    def test_import_completion_result(self):
        """Test importing CompletionResult."""
        from src.tnse.llm import CompletionResult
        assert CompletionResult is not None

    def test_import_llm_provider_interface(self):
        """Test importing LLMProvider interface."""
        from src.tnse.llm import LLMProvider
        assert LLMProvider is not None

    def test_import_exceptions(self):
        """Test importing all LLM exceptions."""
        from src.tnse.llm import (
            GroqAuthenticationError,
            GroqConfigurationError,
            GroqRateLimitError,
            GroqTimeoutError,
            JSONParseError,
        )
        assert GroqAuthenticationError is not None
        assert GroqConfigurationError is not None
        assert GroqRateLimitError is not None
        assert GroqTimeoutError is not None
        assert JSONParseError is not None


class TestGroqClientConfiguration:
    """Test GroqClient configuration and initialization."""

    def test_groq_client_requires_api_key(self):
        """Test that GroqClient raises error without API key."""
        from src.tnse.llm import GroqClient, GroqConfigurationError

        with pytest.raises(GroqConfigurationError):
            GroqClient(api_key=None)

    def test_groq_client_accepts_api_key(self):
        """Test that GroqClient accepts API key."""
        from src.tnse.llm import GroqClient

        client = GroqClient(api_key="test-api-key")
        assert client.api_key == "test-api-key"

    def test_groq_client_default_model(self):
        """Test GroqClient default model configuration."""
        from src.tnse.llm import GroqClient

        client = GroqClient(api_key="test-api-key")
        assert client.model == "qwen-qwq-32b"

    def test_groq_client_custom_model(self):
        """Test GroqClient with custom model."""
        from src.tnse.llm import GroqClient

        client = GroqClient(api_key="test-api-key", model="llama-3.1-70b-versatile")
        assert client.model == "llama-3.1-70b-versatile"

    def test_groq_client_default_temperature(self):
        """Test GroqClient default temperature."""
        from src.tnse.llm import GroqClient

        client = GroqClient(api_key="test-api-key")
        assert client.temperature == 0.1

    def test_groq_client_default_rate_limit(self):
        """Test GroqClient default rate limit."""
        from src.tnse.llm import GroqClient

        client = GroqClient(api_key="test-api-key")
        assert client.rate_limit_rpm == 30

    def test_groq_client_from_settings(self):
        """Test creating GroqClient from settings."""
        from src.tnse.llm import GroqClient
        from src.tnse.core.config import GroqSettings

        settings = GroqSettings(
            api_key="settings-api-key",
            model="llama-3.1-8b-instant",
            temperature=0.5,
            max_tokens=512,
        )

        client = GroqClient.from_settings(settings)
        assert client.api_key == "settings-api-key"
        assert client.model == "llama-3.1-8b-instant"
        assert client.temperature == 0.5
        assert client.max_tokens == 512


class TestEnrichmentServiceConfiguration:
    """Test EnrichmentService configuration."""

    def test_enrichment_service_with_default_settings(self):
        """Test EnrichmentService uses default settings."""
        from src.tnse.llm import EnrichmentService

        mock_client = MagicMock()
        service = EnrichmentService(llm_client=mock_client)

        assert service.settings is not None
        assert service.settings.batch_size == 10
        assert service.settings.rate_limit_per_minute == 30

    def test_enrichment_service_with_custom_settings(self):
        """Test EnrichmentService with custom settings."""
        from src.tnse.llm import EnrichmentService, EnrichmentSettings

        mock_client = MagicMock()
        settings = EnrichmentSettings(
            batch_size=20,
            rate_limit_per_minute=60,
            max_text_length=8000,
        )
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        assert service.settings.batch_size == 20
        assert service.settings.rate_limit_per_minute == 60
        assert service.settings.max_text_length == 8000


class TestEnrichmentPipelineIntegration:
    """Integration tests for the complete enrichment pipeline."""

    @pytest.fixture
    def mock_llm_response(self):
        """Standard mock LLM response for testing."""
        return {
            "explicit_keywords": ["minister", "corruption", "bribery"],
            "implicit_keywords": ["politics", "scandal", "government", "investigation"],
            "category": "politics",
            "sentiment": "negative",
            "entities": {
                "persons": ["Minister X"],
                "organizations": ["Ministry of Finance"],
                "locations": ["Capitol"],
            },
        }

    @pytest.fixture
    def mock_groq_client(self, mock_llm_response):
        """Create a mock GroqClient with predictable responses."""
        from src.tnse.llm import CompletionResult

        mock_completion = CompletionResult(
            content=json.dumps(mock_llm_response),
            prompt_tokens=150,
            completion_tokens=80,
            total_tokens=230,
            model="qwen-qwq-32b",
            duration_ms=250,
            created_at=datetime.now(timezone.utc),
            parsed_json=mock_llm_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)
        mock_client.is_available = AsyncMock(return_value=True)

        return mock_client

    @pytest.mark.asyncio
    async def test_full_enrichment_pipeline(self, mock_groq_client, mock_llm_response):
        """Test complete enrichment pipeline from text to result."""
        from src.tnse.llm import EnrichmentService, EnrichmentResult

        service = EnrichmentService(llm_client=mock_groq_client)

        result = await service.enrich_post(
            post_id=12345,
            text="Minister X was caught accepting bribes at the Capitol building yesterday."
        )

        # Verify result structure
        assert isinstance(result, EnrichmentResult)
        assert result.post_id == 12345
        assert result.success is True
        assert result.error_message is None

        # Verify extracted data
        assert "minister" in result.explicit_keywords
        assert "politics" in result.implicit_keywords
        assert result.category == "politics"
        assert result.sentiment == "negative"
        assert "Minister X" in result.entities.get("persons", [])

        # Verify token tracking
        assert result.input_tokens == 150
        assert result.output_tokens == 80
        assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_enrichment_pipeline_with_russian_text(self, mock_groq_client):
        """Test enrichment with Russian language content."""
        from src.tnse.llm import EnrichmentService

        service = EnrichmentService(llm_client=mock_groq_client)

        result = await service.enrich_post(
            post_id=67890,
            text="Министр был задержан при получении взятки в здании правительства."
        )

        assert result.success is True
        # LLM was called with the Russian text
        mock_groq_client.complete_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrichment_pipeline_handles_empty_text(self, mock_groq_client):
        """Test that empty text returns empty result without LLM call."""
        from src.tnse.llm import EnrichmentService

        service = EnrichmentService(llm_client=mock_groq_client)

        result = await service.enrich_post(post_id=11111, text="")

        assert result.success is True
        assert result.explicit_keywords == []
        assert result.implicit_keywords == []
        assert result.input_tokens == 0
        mock_groq_client.complete_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_enrichment_integration(self, mock_groq_client):
        """Test batch enrichment processes multiple posts."""
        from src.tnse.llm import EnrichmentService, EnrichmentSettings

        # Use high rate limit for faster test
        settings = EnrichmentSettings(rate_limit_per_minute=6000)
        service = EnrichmentService(llm_client=mock_groq_client, settings=settings)

        posts = [
            (1, "First post about technology news."),
            (2, "Second post about sports events."),
            (3, "Third post about economic trends."),
        ]

        results = await service.enrich_batch(posts)

        assert len(results) == 3
        assert all(result.success for result in results)
        assert results[0].post_id == 1
        assert results[1].post_id == 2
        assert results[2].post_id == 3
        assert mock_groq_client.complete_json.call_count == 3


class TestEnrichmentErrorHandling:
    """Test error handling in the enrichment pipeline."""

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self):
        """Test that rate limit errors are handled gracefully."""
        from src.tnse.llm import EnrichmentService, GroqRateLimitError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqRateLimitError("Rate limit exceeded")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.success is False
        assert "rate limit" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self):
        """Test that timeout errors are handled gracefully."""
        from src.tnse.llm import EnrichmentService, GroqTimeoutError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqTimeoutError("Request timed out after 30s")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.success is False
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_handles_json_parse_error(self):
        """Test that JSON parse errors are handled gracefully."""
        from src.tnse.llm import EnrichmentService, JSONParseError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=JSONParseError("Invalid JSON response")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.success is False
        assert "json" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_batch_continues_on_individual_failure(self):
        """Test that batch enrichment continues when individual posts fail."""
        from src.tnse.llm import (
            EnrichmentService,
            EnrichmentSettings,
            CompletionResult,
            GroqRateLimitError,
        )

        success_response = {
            "explicit_keywords": ["test"],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        success_completion = CompletionResult(
            content=json.dumps(success_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=success_response,
        )

        call_count = 0

        async def mock_complete_json(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                raise GroqRateLimitError("Rate limit exceeded")
            return success_completion

        mock_client = AsyncMock()
        mock_client.complete_json = mock_complete_json

        settings = EnrichmentSettings(rate_limit_per_minute=6000)
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        posts = [
            (1, "First post"),
            (2, "Second post - will fail"),
            (3, "Third post"),
        ]

        results = await service.enrich_batch(posts)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestEnrichmentResultValidation:
    """Test EnrichmentResult validation and normalization."""

    @pytest.mark.asyncio
    async def test_keywords_normalized_to_lowercase(self):
        """Test that keywords are normalized to lowercase."""
        from src.tnse.llm import EnrichmentService, CompletionResult

        mock_response = {
            "explicit_keywords": ["BITCOIN", "CryptoCurrency", "Trading"],
            "implicit_keywords": ["BLOCKCHAIN", "Finance"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Bitcoin news")

        # All keywords should be lowercase
        assert all(kw.islower() for kw in result.explicit_keywords)
        assert all(kw.islower() for kw in result.implicit_keywords)
        assert "bitcoin" in result.explicit_keywords
        assert "blockchain" in result.implicit_keywords

    @pytest.mark.asyncio
    async def test_duplicate_keywords_removed(self):
        """Test that duplicate keywords are removed."""
        from src.tnse.llm import EnrichmentService, CompletionResult

        mock_response = {
            "explicit_keywords": ["bitcoin", "Bitcoin", "BITCOIN"],
            "implicit_keywords": ["blockchain", "blockchain"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Bitcoin news")

        # Duplicates should be removed
        assert result.explicit_keywords.count("bitcoin") == 1
        assert result.implicit_keywords.count("blockchain") == 1

    @pytest.mark.asyncio
    async def test_invalid_category_defaults_to_other(self):
        """Test that invalid categories default to 'other'."""
        from src.tnse.llm import EnrichmentService, CompletionResult

        mock_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "INVALID_CATEGORY",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test")

        assert result.category == "other"

    @pytest.mark.asyncio
    async def test_invalid_sentiment_defaults_to_neutral(self):
        """Test that invalid sentiments default to 'neutral'."""
        from src.tnse.llm import EnrichmentService, CompletionResult

        mock_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "politics",
            "sentiment": "HAPPY",  # Invalid
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test")

        assert result.sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_missing_fields_use_defaults(self):
        """Test that missing response fields use defaults."""
        from src.tnse.llm import EnrichmentService, CompletionResult

        # Response with missing fields
        mock_response = {
            "explicit_keywords": ["test"],
            # Missing: implicit_keywords, category, sentiment, entities
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test")

        assert result.success is True
        assert result.explicit_keywords == ["test"]
        assert result.implicit_keywords == []
        assert result.category == "other"
        assert result.sentiment == "neutral"
        assert result.entities == {"persons": [], "organizations": [], "locations": []}


class TestTextTruncation:
    """Test text truncation for long content."""

    @pytest.mark.asyncio
    async def test_long_text_is_truncated(self):
        """Test that very long text is truncated."""
        from src.tnse.llm import EnrichmentService, EnrichmentSettings, CompletionResult

        mock_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        # Set max_text_length to a small value for testing
        settings = EnrichmentSettings(max_text_length=100)
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        # Create text longer than max_text_length
        long_text = "A" * 500

        await service.enrich_post(post_id=1, text=long_text)

        # Verify the prompt was called with truncated text
        call_args = mock_client.complete_json.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")

        # The prompt should NOT contain the full 500 'A' characters
        assert prompt.count("A") < 500


class TestPromptTemplateIntegration:
    """Test the enrichment prompt template."""

    def test_prompt_template_includes_required_fields(self):
        """Test that the prompt template requests all required fields."""
        from src.tnse.llm import ENRICHMENT_PROMPT

        # Check for required field requests
        assert "explicit_keywords" in ENRICHMENT_PROMPT
        assert "implicit_keywords" in ENRICHMENT_PROMPT
        assert "category" in ENRICHMENT_PROMPT
        assert "sentiment" in ENRICHMENT_PROMPT
        assert "entities" in ENRICHMENT_PROMPT

    def test_prompt_template_explains_implicit_keywords(self):
        """Test that the prompt explains implicit keywords concept."""
        from src.tnse.llm import ENRICHMENT_PROMPT

        # Should explain that implicit keywords are NOT in the text
        prompt_lower = ENRICHMENT_PROMPT.lower()
        has_not_explanation = (
            "not in" in prompt_lower or
            "not directly" in prompt_lower or
            "not mentioned" in prompt_lower
        )
        assert has_not_explanation

    def test_prompt_template_lists_categories(self):
        """Test that the prompt lists valid categories."""
        from src.tnse.llm import ENRICHMENT_PROMPT

        prompt_lower = ENRICHMENT_PROMPT.lower()
        assert "politics" in prompt_lower
        assert "economics" in prompt_lower
        assert "technology" in prompt_lower

    def test_prompt_template_lists_sentiments(self):
        """Test that the prompt lists valid sentiments."""
        from src.tnse.llm import ENRICHMENT_PROMPT

        prompt_lower = ENRICHMENT_PROMPT.lower()
        assert "positive" in prompt_lower
        assert "negative" in prompt_lower
        assert "neutral" in prompt_lower

    def test_prompt_template_requests_json(self):
        """Test that the prompt requests JSON output."""
        from src.tnse.llm import ENRICHMENT_PROMPT

        assert "json" in ENRICHMENT_PROMPT.lower()


class TestCompletionResultDataclass:
    """Test CompletionResult dataclass."""

    def test_completion_result_creation(self):
        """Test creating a CompletionResult."""
        from src.tnse.llm import CompletionResult

        result = CompletionResult(
            content='{"test": true}',
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json={"test": True},
        )

        assert result.content == '{"test": true}'
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        assert result.total_tokens == 150
        assert result.model == "qwen-qwq-32b"
        assert result.duration_ms == 200
        assert result.parsed_json == {"test": True}

    def test_completion_result_default_values(self):
        """Test CompletionResult default values."""
        from src.tnse.llm import CompletionResult

        result = CompletionResult(
            content="test",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )

        assert result.model == ""
        assert result.duration_ms == 0
        assert result.parsed_json is None
        assert result.created_at is not None


class TestRateLimiter:
    """Test the rate limiter functionality."""

    def test_rate_limiter_creation(self):
        """Test creating a RateLimiter."""
        from src.tnse.llm import RateLimiter

        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.requests_per_minute == 30
        assert limiter.min_interval == 2.0  # 60 / 30 = 2 seconds

    @pytest.mark.asyncio
    async def test_rate_limiter_first_request_no_delay(self):
        """Test that first request has no delay."""
        import time
        from src.tnse.llm import RateLimiter

        limiter = RateLimiter(requests_per_minute=30)

        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # First request should be nearly instant
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delay(self):
        """Test that rate limiter enforces delay between requests."""
        import time
        from src.tnse.llm import RateLimiter

        # High rate limit = short delay for faster test
        limiter = RateLimiter(requests_per_minute=120)  # 0.5 second delay

        await limiter.acquire()  # First request
        start = time.monotonic()
        await limiter.acquire()  # Second request
        elapsed = time.monotonic() - start

        # Should have waited at least 0.4 seconds (0.5s - tolerance)
        assert elapsed >= 0.4


class TestEnrichmentServiceRateLimiting:
    """Test EnrichmentService rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_batch_respects_rate_limit(self):
        """Test that batch enrichment respects rate limits."""
        import time
        from src.tnse.llm import EnrichmentService, EnrichmentSettings, CompletionResult

        mock_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=50,
            parsed_json=mock_response,
        )

        call_times = []

        async def mock_complete(*args, **kwargs):
            call_times.append(time.monotonic())
            return mock_completion

        mock_client = AsyncMock()
        mock_client.complete_json = mock_complete

        # Use 60 RPM = 1 second delay between requests
        settings = EnrichmentSettings(rate_limit_per_minute=60)
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        posts = [
            (1, "First"),
            (2, "Second"),
            (3, "Third"),
        ]

        await service.enrich_batch(posts)

        # Verify delays between calls
        assert len(call_times) == 3
        for index in range(1, len(call_times)):
            delay = call_times[index] - call_times[index - 1]
            # Should have at least 0.8 second delay (1s - tolerance)
            assert delay >= 0.8, f"Delay was only {delay:.2f}s"

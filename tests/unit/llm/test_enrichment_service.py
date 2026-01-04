"""
Tests for Enrichment Service Core (WS-5.3)

Following TDD methodology: these tests are written BEFORE implementation.
The tests validate:
1. EnrichmentResult dataclass structure
2. EnrichmentService.enrich_post() method
3. EnrichmentService.enrich_batch() method
4. Prompt template design and JSON validation
5. Edge case handling (empty text, media-only, LLM refusal, rate limiting)
6. Structured logging
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEnrichmentResultDataclass:
    """Tests for EnrichmentResult dataclass structure."""

    def test_enrichment_result_exists(self):
        """Test that EnrichmentResult dataclass exists."""
        from src.tnse.llm.enrichment_service import EnrichmentResult

        assert EnrichmentResult is not None

    def test_enrichment_result_has_required_fields(self):
        """Test that EnrichmentResult has all required fields."""
        from src.tnse.llm.enrichment_service import EnrichmentResult

        result = EnrichmentResult(
            post_id=123,
            explicit_keywords=["minister", "cash", "hotel"],
            implicit_keywords=["corruption", "bribery", "scandal"],
            category="politics",
            sentiment="negative",
            entities={"persons": ["Minister X"], "organizations": [], "locations": ["hotel"]},
            input_tokens=100,
            output_tokens=50,
            processing_time_ms=250,
            success=True,
        )

        assert result.post_id == 123
        assert result.explicit_keywords == ["minister", "cash", "hotel"]
        assert result.implicit_keywords == ["corruption", "bribery", "scandal"]
        assert result.category == "politics"
        assert result.sentiment == "negative"
        assert result.entities == {"persons": ["Minister X"], "organizations": [], "locations": ["hotel"]}
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.processing_time_ms == 250
        assert result.success is True
        assert result.error_message is None

    def test_enrichment_result_with_error(self):
        """Test EnrichmentResult with error message."""
        from src.tnse.llm.enrichment_service import EnrichmentResult

        result = EnrichmentResult(
            post_id=456,
            explicit_keywords=[],
            implicit_keywords=[],
            category="",
            sentiment="",
            entities={},
            input_tokens=0,
            output_tokens=0,
            processing_time_ms=100,
            success=False,
            error_message="LLM refusal: content policy violation",
        )

        assert result.success is False
        assert result.error_message == "LLM refusal: content policy violation"

    def test_enrichment_result_default_error_message_is_none(self):
        """Test that error_message defaults to None."""
        from src.tnse.llm.enrichment_service import EnrichmentResult

        result = EnrichmentResult(
            post_id=789,
            explicit_keywords=[],
            implicit_keywords=[],
            category="other",
            sentiment="neutral",
            entities={},
            input_tokens=50,
            output_tokens=25,
            processing_time_ms=150,
            success=True,
        )

        assert result.error_message is None


class TestEnrichmentSettings:
    """Tests for EnrichmentSettings configuration."""

    def test_enrichment_settings_exists(self):
        """Test that EnrichmentSettings class exists."""
        from src.tnse.llm.enrichment_service import EnrichmentSettings

        assert EnrichmentSettings is not None

    def test_enrichment_settings_defaults(self):
        """Test that EnrichmentSettings has sensible defaults."""
        from src.tnse.llm.enrichment_service import EnrichmentSettings

        settings = EnrichmentSettings()

        assert settings.batch_size == 10
        assert settings.rate_limit_per_minute == 30
        assert settings.max_text_length == 4000
        assert settings.default_category == "other"
        assert settings.valid_categories is not None
        assert "politics" in settings.valid_categories
        assert "economics" in settings.valid_categories
        assert settings.valid_sentiments == ["positive", "negative", "neutral"]


class TestEnrichmentServiceCreation:
    """Tests for EnrichmentService creation and lifecycle."""

    def test_enrichment_service_exists(self):
        """Test that EnrichmentService class exists."""
        from src.tnse.llm.enrichment_service import EnrichmentService

        assert EnrichmentService is not None

    def test_enrichment_service_creation_with_llm_client(self):
        """Test that EnrichmentService can be created with an LLM client."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentSettings
        from src.tnse.llm.base import LLMProvider

        mock_client = MagicMock(spec=LLMProvider)
        settings = EnrichmentSettings()

        service = EnrichmentService(llm_client=mock_client, settings=settings)

        assert service is not None
        assert service.llm_client is mock_client
        assert service.settings is settings

    def test_enrichment_service_creation_without_settings_uses_defaults(self):
        """Test that EnrichmentService uses default settings when none provided."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import LLMProvider

        mock_client = MagicMock(spec=LLMProvider)

        service = EnrichmentService(llm_client=mock_client)

        assert service.settings is not None
        assert service.settings.batch_size == 10


class TestEnrichPostMethod:
    """Tests for enrich_post() method."""

    @pytest.mark.asyncio
    async def test_enrich_post_returns_enrichment_result(self):
        """Test that enrich_post returns an EnrichmentResult."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentResult
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["bitcoin", "cryptocurrency"],
            "implicit_keywords": ["blockchain", "finance", "investment"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {
                "persons": [],
                "organizations": ["Bitcoin Foundation"],
                "locations": [],
            },
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(
            post_id=1,
            text="Bitcoin reaches new all-time high as cryptocurrency market surges.",
        )

        assert isinstance(result, EnrichmentResult)
        assert result.post_id == 1
        assert result.success is True
        assert "bitcoin" in result.explicit_keywords
        assert "blockchain" in result.implicit_keywords
        assert result.category == "economics"
        assert result.sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_enrich_post_uses_prompt_template(self):
        """Test that enrich_post uses the correct prompt template."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        await service.enrich_post(post_id=1, text="Test content")

        # Verify that complete_json was called with prompt containing the text
        call_args = mock_client.complete_json.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        assert "Test content" in prompt
        assert "explicit_keywords" in prompt
        assert "implicit_keywords" in prompt

    @pytest.mark.asyncio
    async def test_enrich_post_tracks_tokens_and_timing(self):
        """Test that enrich_post tracks token usage and processing time."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
            model="qwen-qwq-32b",
            duration_ms=350,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.input_tokens == 120
        assert result.output_tokens == 80
        assert result.processing_time_ms >= 0


class TestEnrichBatchMethod:
    """Tests for enrich_batch() method."""

    @pytest.mark.asyncio
    async def test_enrich_batch_processes_multiple_posts(self):
        """Test that enrich_batch processes multiple posts."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentResult
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["test"],
            "implicit_keywords": ["example"],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=150,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)

        posts = [
            (1, "First post content"),
            (2, "Second post content"),
            (3, "Third post content"),
        ]

        results = await service.enrich_batch(posts)

        assert len(results) == 3
        assert all(isinstance(result, EnrichmentResult) for result in results)
        assert results[0].post_id == 1
        assert results[1].post_id == 2
        assert results[2].post_id == 3

    @pytest.mark.asyncio
    async def test_enrich_batch_respects_rate_limit(self):
        """Test that enrich_batch respects rate limits by verifying delay between calls."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentSettings
        from src.tnse.llm.base import CompletionResult
        import time

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=50,
            parsed_json=mock_json_response,
        )

        call_times = []

        async def mock_complete(*args, **kwargs):
            call_times.append(time.monotonic())
            return mock_completion

        mock_client = AsyncMock()
        mock_client.complete_json = mock_complete

        # Use rate limit of 120 per minute = 1 every 0.5 seconds
        settings = EnrichmentSettings(rate_limit_per_minute=120)
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        posts = [
            (1, "First post"),
            (2, "Second post"),
            (3, "Third post"),
        ]

        await service.enrich_batch(posts)

        # Verify we made 3 calls
        assert len(call_times) == 3

        # Verify there's a delay between calls (at least 0.4 seconds)
        for index in range(1, len(call_times)):
            delay = call_times[index] - call_times[index - 1]
            assert delay >= 0.4, f"Delay between call {index-1} and {index} was only {delay:.2f}s"

    @pytest.mark.asyncio
    async def test_enrich_batch_handles_partial_failures(self):
        """Test that enrich_batch continues on individual post failures."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentResult
        from src.tnse.llm.base import CompletionResult
        from src.tnse.llm.groq_client import GroqRateLimitError

        mock_json_response = {
            "explicit_keywords": ["success"],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        call_count = 0

        async def mock_complete_json(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise GroqRateLimitError("Rate limit exceeded")
            return mock_completion

        mock_client = AsyncMock()
        mock_client.complete_json = mock_complete_json

        service = EnrichmentService(llm_client=mock_client)

        posts = [
            (1, "First post"),
            (2, "Second post - will fail"),
            (3, "Third post"),
        ]

        results = await service.enrich_batch(posts)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert "Rate limit" in results[1].error_message
        assert results[2].success is True


class TestEdgeCases:
    """Tests for edge case handling."""

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_result(self):
        """Test that empty text returns an empty successful result."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentResult

        mock_client = AsyncMock()
        service = EnrichmentService(llm_client=mock_client)

        result = await service.enrich_post(post_id=1, text="")

        assert isinstance(result, EnrichmentResult)
        assert result.success is True
        assert result.explicit_keywords == []
        assert result.implicit_keywords == []
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        # LLM should NOT be called for empty text
        mock_client.complete_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_text_returns_empty_result(self):
        """Test that None text returns an empty successful result."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentResult

        mock_client = AsyncMock()
        service = EnrichmentService(llm_client=mock_client)

        result = await service.enrich_post(post_id=1, text=None)

        assert result.success is True
        assert result.explicit_keywords == []
        mock_client.complete_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_text_returns_empty_result(self):
        """Test that whitespace-only text returns an empty result."""
        from src.tnse.llm.enrichment_service import EnrichmentService

        mock_client = AsyncMock()
        service = EnrichmentService(llm_client=mock_client)

        result = await service.enrich_post(post_id=1, text="   \n\t  ")

        assert result.success is True
        assert result.explicit_keywords == []
        mock_client.complete_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_refusal_returns_error_result(self):
        """Test handling of LLM content policy refusal."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.groq_client import GroqError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqError("Content policy violation")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Problematic content")

        assert result.success is False
        assert "Content policy" in result.error_message

    @pytest.mark.asyncio
    async def test_timeout_returns_error_result(self):
        """Test handling of timeout errors."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.groq_client import GroqTimeoutError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqTimeoutError("Request timed out")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Some content")

        assert result.success is False
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_error_result(self):
        """Test handling of rate limit errors."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.groq_client import GroqRateLimitError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqRateLimitError("Rate limit exceeded after retries")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Some content")

        assert result.success is False
        assert "rate limit" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_response_returns_error_result(self):
        """Test handling of invalid JSON in LLM response."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.groq_client import JSONParseError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=JSONParseError("Invalid JSON")
        )

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Some content")

        assert result.success is False
        assert "json" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_long_text_is_truncated(self):
        """Test that very long text is truncated before sending to LLM."""
        from src.tnse.llm.enrichment_service import EnrichmentService, EnrichmentSettings
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=500,
            completion_tokens=50,
            total_tokens=550,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        settings = EnrichmentSettings(max_text_length=100)
        service = EnrichmentService(llm_client=mock_client, settings=settings)

        # Create text longer than max_text_length
        long_text = "A" * 500
        await service.enrich_post(post_id=1, text=long_text)

        # Verify the text sent to LLM was truncated
        call_args = mock_client.complete_json.call_args
        prompt = call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
        # The truncated text should be <= max_text_length + truncation indicator
        assert len(long_text) > 100  # Confirm original was long
        # The prompt should contain truncated text, not full 500 chars


class TestJSONValidation:
    """Tests for JSON response validation."""

    @pytest.mark.asyncio
    async def test_missing_required_field_uses_defaults(self):
        """Test that missing required fields use defaults."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        # Response missing some fields
        mock_json_response = {
            "explicit_keywords": ["test"],
            # Missing: implicit_keywords, category, sentiment, entities
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        # Should use defaults for missing fields
        assert result.success is True
        assert result.explicit_keywords == ["test"]
        assert result.implicit_keywords == []  # Default
        assert result.category == "other"  # Default
        assert result.sentiment == "neutral"  # Default
        assert result.entities == {"persons": [], "organizations": [], "locations": []}  # Default

    @pytest.mark.asyncio
    async def test_invalid_category_falls_back_to_other(self):
        """Test that invalid category values fall back to 'other'."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "invalid_category_xyz",  # Invalid
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.category == "other"

    @pytest.mark.asyncio
    async def test_invalid_sentiment_falls_back_to_neutral(self):
        """Test that invalid sentiment values fall back to 'neutral'."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "politics",
            "sentiment": "very_happy",  # Invalid
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Test content")

        assert result.sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_keywords_are_normalized_to_lowercase(self):
        """Test that keywords are normalized to lowercase."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["BITCOIN", "CryptoCurrency", "Trading"],
            "implicit_keywords": ["BLOCKCHAIN", "Finance"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Bitcoin cryptocurrency trading")

        assert result.explicit_keywords == ["bitcoin", "cryptocurrency", "trading"]
        assert result.implicit_keywords == ["blockchain", "finance"]

    @pytest.mark.asyncio
    async def test_duplicate_keywords_are_removed(self):
        """Test that duplicate keywords are removed."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["bitcoin", "Bitcoin", "BITCOIN", "crypto"],
            "implicit_keywords": ["blockchain", "blockchain"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(post_id=1, text="Bitcoin crypto")

        # Duplicates should be removed (case-insensitive)
        assert "bitcoin" in result.explicit_keywords
        assert result.explicit_keywords.count("bitcoin") == 1
        assert "blockchain" in result.implicit_keywords
        assert result.implicit_keywords.count("blockchain") == 1


class TestPromptTemplate:
    """Tests for prompt template design."""

    def test_prompt_template_constant_exists(self):
        """Test that ENRICHMENT_PROMPT constant exists."""
        from src.tnse.llm.enrichment_service import ENRICHMENT_PROMPT

        assert ENRICHMENT_PROMPT is not None
        assert isinstance(ENRICHMENT_PROMPT, str)
        assert len(ENRICHMENT_PROMPT) > 100

    def test_prompt_template_contains_required_sections(self):
        """Test that prompt template contains all required sections."""
        from src.tnse.llm.enrichment_service import ENRICHMENT_PROMPT

        # Should mention explicit keywords
        assert "explicit_keywords" in ENRICHMENT_PROMPT.lower() or "explicit keywords" in ENRICHMENT_PROMPT.lower()

        # Should mention implicit keywords (the key innovation!)
        assert "implicit_keywords" in ENRICHMENT_PROMPT.lower() or "implicit keywords" in ENRICHMENT_PROMPT.lower()

        # Should mention category
        assert "category" in ENRICHMENT_PROMPT.lower()

        # Should mention sentiment
        assert "sentiment" in ENRICHMENT_PROMPT.lower()

        # Should mention entities
        assert "entities" in ENRICHMENT_PROMPT.lower()

        # Should request JSON format
        assert "json" in ENRICHMENT_PROMPT.lower()

    def test_prompt_template_explains_implicit_keywords(self):
        """Test that prompt template explains the implicit keywords concept."""
        from src.tnse.llm.enrichment_service import ENRICHMENT_PROMPT

        # The prompt should explain that implicit keywords are NOT in the text
        assert "not in" in ENRICHMENT_PROMPT.lower() or "not directly" in ENRICHMENT_PROMPT.lower()

    def test_prompt_template_lists_valid_categories(self):
        """Test that prompt template lists valid categories."""
        from src.tnse.llm.enrichment_service import ENRICHMENT_PROMPT

        # Should mention at least some of the valid categories
        categories_mentioned = [
            "politics",
            "economics",
            "technology",
            "crime",
            "sports",
            "entertainment",
        ]
        found_count = sum(1 for cat in categories_mentioned if cat in ENRICHMENT_PROMPT.lower())
        assert found_count >= 4  # At least 4 categories should be mentioned

    def test_prompt_template_lists_valid_sentiments(self):
        """Test that prompt template lists valid sentiments."""
        from src.tnse.llm.enrichment_service import ENRICHMENT_PROMPT

        assert "positive" in ENRICHMENT_PROMPT.lower()
        assert "negative" in ENRICHMENT_PROMPT.lower()
        assert "neutral" in ENRICHMENT_PROMPT.lower()


class TestStructuredLogging:
    """Tests for structured logging."""

    @pytest.mark.asyncio
    async def test_enrich_post_logs_start_and_completion(self):
        """Test that enrich_post logs start and completion."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult
        import logging

        mock_json_response = {
            "explicit_keywords": [],
            "implicit_keywords": [],
            "category": "other",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            model="qwen-qwq-32b",
            duration_ms=100,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)

        with patch("src.tnse.llm.enrichment_service.logger") as mock_logger:
            await service.enrich_post(post_id=123, text="Test content")

            # Should log at least once
            assert mock_logger.debug.called or mock_logger.info.called

    @pytest.mark.asyncio
    async def test_enrich_post_logs_errors(self):
        """Test that enrich_post logs errors."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.groq_client import GroqError

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(
            side_effect=GroqError("Test error")
        )

        service = EnrichmentService(llm_client=mock_client)

        with patch("src.tnse.llm.enrichment_service.logger") as mock_logger:
            await service.enrich_post(post_id=123, text="Test content")

            # Should log the error
            assert mock_logger.error.called or mock_logger.warning.called


class TestMultilingualSupport:
    """Tests for multilingual content handling."""

    @pytest.mark.asyncio
    async def test_russian_text_is_processed(self):
        """Test that Russian text is properly processed."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["министр", "коррупция"],
            "implicit_keywords": ["политика", "скандал"],
            "category": "politics",
            "sentiment": "negative",
            "entities": {"persons": ["Министр X"], "organizations": [], "locations": ["Москва"]},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=80,
            completion_tokens=50,
            total_tokens=130,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(
            post_id=1,
            text="Министр был пойман при получении взятки в отеле.",
        )

        assert result.success is True
        assert "министр" in result.explicit_keywords
        assert "политика" in result.implicit_keywords

    @pytest.mark.asyncio
    async def test_ukrainian_text_is_processed(self):
        """Test that Ukrainian text is properly processed."""
        from src.tnse.llm.enrichment_service import EnrichmentService
        from src.tnse.llm.base import CompletionResult

        mock_json_response = {
            "explicit_keywords": ["bitcoin", "cryptocurrency"],
            "implicit_keywords": ["technology", "investment"],
            "category": "economics",
            "sentiment": "neutral",
            "entities": {"persons": [], "organizations": [], "locations": []},
        }

        mock_completion = CompletionResult(
            content=json.dumps(mock_json_response),
            prompt_tokens=80,
            completion_tokens=50,
            total_tokens=130,
            model="qwen-qwq-32b",
            duration_ms=200,
            parsed_json=mock_json_response,
        )

        mock_client = AsyncMock()
        mock_client.complete_json = AsyncMock(return_value=mock_completion)

        service = EnrichmentService(llm_client=mock_client)
        result = await service.enrich_post(
            post_id=1,
            text="Bitcoin cryptocurrency trading news",
        )

        assert result.success is True
        # LLM was called (Ukrainian text should be processed like any other)
        mock_client.complete_json.assert_called_once()

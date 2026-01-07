"""
Enrichment Service Core (WS-5.3)

Service for extracting metadata from post content via LLM.
Implements the core RAG-without-vectors approach by extracting both
explicit keywords (in text) and implicit keywords (related concepts NOT in text).

This is the key innovation for semantic search without vector databases.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.tnse.llm.base import CompletionResult, LLMProvider
from src.tnse.llm.groq_client import (
    GroqError,
    GroqRateLimitError,
    GroqTimeoutError,
    JSONParseError,
)

logger = logging.getLogger(__name__)


# Prompt template for LLM enrichment
# This is the key component that instructs the LLM to extract metadata
ENRICHMENT_PROMPT = """Проанализируй этот пост из Telegram. Извлеки структурированную информацию.

СОДЕРЖАНИЕ ПОСТА:
{text_content}

Верни результат в формате JSON:
{{
    "explicit_keywords": ["список ключевых слов/фраз, которые присутствуют непосредственно в тексте"],
    "implicit_keywords": ["список связанных понятий, тем, сущностей, которых НЕТ в тексте, но они семантически релевантны"],
    "category": "основная категория темы (politics, economics, technology, sports, entertainment, health, military, crime, society, other)",
    "sentiment": "positive|negative|neutral",
    "entities": {{
        "persons": ["имена упомянутых или подразумеваемых людей"],
        "organizations": ["названия организаций, компаний, учреждений"],
        "locations": ["географические локации"]
    }}
}}

ВАЖНО для implicit_keywords (неявные ключевые слова):
- Это понятия, которые читатель ассоциирует с контентом, но они НЕ упоминаются напрямую в тексте
- Включай связанные термины, синонимы, более широкие категории, контекстные ассоциации
- Пример: Если пост упоминает "iPhone", неявные ключевые слова могут включать ["Apple", "смартфон", "iOS", "гаджет"]
- Пример: Если пост о "Министр пойман при получении взятки", неявные слова: ["коррупция", "взяточничество", "скандал", "политика"]

ВАЖНО для explicit_keywords (явные ключевые слова):
- Извлекай ключевые слова и фразы, которые фактически присутствуют в тексте
- Фокусируйся на существительных, именах собственных и значимых терминах

КРИТИЧЕСКИ ВАЖНО:
- Все ключевые слова (explicit и implicit) ДОЛЖНЫ быть на русском языке
- Имена собственные оставляй как в оригинале
- Возвращай ТОЛЬКО валидный JSON, без объяснений и дополнительного текста"""


class EnrichmentSettings(BaseSettings):
    """Configuration for post enrichment service.

    Attributes:
        batch_size: Number of posts to process in a batch
        rate_limit_per_minute: Max requests per minute to respect API limits
        max_text_length: Maximum text length before truncation
        default_category: Default category when extraction fails
        valid_categories: List of valid category values
        valid_sentiments: List of valid sentiment values
    """

    model_config = SettingsConfigDict(env_prefix="ENRICHMENT_")

    batch_size: int = Field(default=10, description="Batch size for enrichment")
    rate_limit_per_minute: int = Field(default=30, description="Requests per minute limit")
    max_text_length: int = Field(default=4000, description="Max text length before truncation")
    default_category: str = Field(default="other", description="Default category")
    valid_categories: list[str] = Field(
        default=[
            "politics",
            "economics",
            "technology",
            "sports",
            "entertainment",
            "health",
            "military",
            "crime",
            "society",
            "other",
        ],
        description="Valid category values",
    )
    valid_sentiments: list[str] = Field(
        default=["positive", "negative", "neutral"],
        description="Valid sentiment values",
    )


@dataclass
class EnrichmentResult:
    """Result from LLM enrichment for a single post.

    Stores both explicit keywords (in text) and implicit keywords
    (related concepts NOT in text) - the key RAG innovation.

    Attributes:
        post_id: ID of the enriched post
        explicit_keywords: Keywords directly present in the text
        implicit_keywords: Related concepts NOT in text (key for RAG)
        category: Primary topic category
        sentiment: Sentiment classification (positive/negative/neutral)
        entities: Named entities (persons, organizations, locations)
        input_tokens: Prompt tokens used
        output_tokens: Completion tokens used
        processing_time_ms: Time taken for processing
        success: Whether enrichment succeeded
        error_message: Error message if failed
    """

    post_id: int
    explicit_keywords: list[str]
    implicit_keywords: list[str]
    category: str
    sentiment: str
    entities: dict[str, list[str]]
    input_tokens: int
    output_tokens: int
    processing_time_ms: int
    success: bool
    error_message: str | None = None


class EnrichmentService:
    """Service for enriching posts with LLM-extracted metadata.

    Uses an LLM to extract:
    - Explicit keywords (words/phrases actually in the text)
    - Implicit keywords (related concepts NOT in text) - KEY INNOVATION
    - Category (politics, economics, technology, etc.)
    - Sentiment (positive, negative, neutral)
    - Named entities (persons, organizations, locations)

    Usage:
        async with GroqClient(api_key="your-key") as client:
            service = EnrichmentService(llm_client=client)
            result = await service.enrich_post(post_id=123, text="Post content...")
    """

    def __init__(
        self,
        llm_client: LLMProvider,
        settings: EnrichmentSettings | None = None,
    ) -> None:
        """Initialize the enrichment service.

        Args:
            llm_client: LLM provider for making completion requests
            settings: Optional settings; uses defaults if not provided
        """
        self.llm_client = llm_client
        self.settings = settings or EnrichmentSettings()
        self._last_request_time: float = 0.0
        self._rate_limit_lock = asyncio.Lock()

    async def _wait_for_rate_limit(self) -> None:
        """Wait to respect rate limiting between requests."""
        if self.settings.rate_limit_per_minute <= 0:
            return

        min_interval = 60.0 / self.settings.rate_limit_per_minute

        async with self._rate_limit_lock:
            now = time.monotonic()

            # Only wait if we've made at least one request
            if self._last_request_time > 0:
                elapsed = now - self._last_request_time
                wait_time = min_interval - elapsed

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            # Always update the last request time
            self._last_request_time = time.monotonic()

    def _truncate_text(self, text: str) -> str:
        """Truncate text if it exceeds max length.

        Args:
            text: Text to potentially truncate

        Returns:
            Truncated text with indicator if truncated
        """
        if len(text) <= self.settings.max_text_length:
            return text

        truncated = text[: self.settings.max_text_length]
        # Try to break at a word boundary
        last_space = truncated.rfind(" ")
        if last_space > self.settings.max_text_length * 0.8:
            truncated = truncated[:last_space]

        return truncated + "... [truncated]"

    def _normalize_keywords(self, keywords: list[Any]) -> list[str]:
        """Normalize keywords: lowercase and remove duplicates.

        Args:
            keywords: List of keyword values

        Returns:
            Normalized list of unique lowercase keywords
        """
        seen = set()
        normalized = []

        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            lower = keyword.lower().strip()
            if lower and lower not in seen:
                seen.add(lower)
                normalized.append(lower)

        return normalized

    def _validate_category(self, category: Any) -> str:
        """Validate and normalize category value.

        Args:
            category: Category value from LLM response

        Returns:
            Valid category or default
        """
        if not isinstance(category, str):
            return self.settings.default_category

        lower = category.lower().strip()
        if lower in self.settings.valid_categories:
            return lower

        return self.settings.default_category

    def _validate_sentiment(self, sentiment: Any) -> str:
        """Validate and normalize sentiment value.

        Args:
            sentiment: Sentiment value from LLM response

        Returns:
            Valid sentiment or 'neutral' default
        """
        if not isinstance(sentiment, str):
            return "neutral"

        lower = sentiment.lower().strip()
        if lower in self.settings.valid_sentiments:
            return lower

        return "neutral"

    def _validate_entities(self, entities: Any) -> dict[str, list[str]]:
        """Validate and normalize entities structure.

        Args:
            entities: Entities dict from LLM response

        Returns:
            Validated entities dict with required keys
        """
        default = {"persons": [], "organizations": [], "locations": []}

        if not isinstance(entities, dict):
            return default

        result = {}
        for key in ["persons", "organizations", "locations"]:
            value = entities.get(key, [])
            if isinstance(value, list):
                result[key] = [str(item) for item in value if item]
            else:
                result[key] = []

        return result

    def _parse_llm_response(self, completion: CompletionResult) -> dict[str, Any]:
        """Parse and validate LLM response.

        Args:
            completion: CompletionResult from LLM

        Returns:
            Validated dict with enrichment data
        """
        parsed = completion.parsed_json or {}

        return {
            "explicit_keywords": self._normalize_keywords(
                parsed.get("explicit_keywords", [])
            ),
            "implicit_keywords": self._normalize_keywords(
                parsed.get("implicit_keywords", [])
            ),
            "category": self._validate_category(parsed.get("category")),
            "sentiment": self._validate_sentiment(parsed.get("sentiment")),
            "entities": self._validate_entities(parsed.get("entities")),
        }

    def _create_empty_result(
        self,
        post_id: int,
        success: bool = True,
        error_message: str | None = None,
    ) -> EnrichmentResult:
        """Create an empty enrichment result.

        Args:
            post_id: Post ID
            success: Whether this is a success (empty text) or failure
            error_message: Optional error message

        Returns:
            EnrichmentResult with empty/default values
        """
        return EnrichmentResult(
            post_id=post_id,
            explicit_keywords=[],
            implicit_keywords=[],
            category=self.settings.default_category,
            sentiment="neutral",
            entities={"persons": [], "organizations": [], "locations": []},
            input_tokens=0,
            output_tokens=0,
            processing_time_ms=0,
            success=success,
            error_message=error_message,
        )

    async def enrich_post(
        self,
        post_id: int,
        text: str | None,
    ) -> EnrichmentResult:
        """Enrich a single post with LLM-extracted metadata.

        Args:
            post_id: ID of the post to enrich
            text: Text content to analyze

        Returns:
            EnrichmentResult with extracted metadata
        """
        # Handle empty/missing text
        if not text or not text.strip():
            logger.debug(
                "Skipping enrichment for post %s: empty text",
                post_id,
            )
            return self._create_empty_result(post_id)

        # Truncate long text
        text = self._truncate_text(text.strip())

        # Build prompt
        prompt = ENRICHMENT_PROMPT.format(text_content=text)

        logger.debug(
            "Starting enrichment for post %s (text length: %d)",
            post_id,
            len(text),
        )

        start_time = time.monotonic()

        try:
            # Make LLM call
            completion = await self.llm_client.complete_json(
                prompt=prompt,
                system_message="Ты - ассистент для анализа контента. Извлекай структурированные метаданные из постов Telegram. Всегда отвечай на русском языке. Возвращай только валидный JSON.",
            )

            processing_time_ms = int((time.monotonic() - start_time) * 1000)

            # Parse and validate response
            parsed = self._parse_llm_response(completion)

            logger.info(
                "Enriched post %s: category=%s, sentiment=%s, "
                "explicit_keywords=%d, implicit_keywords=%d",
                post_id,
                parsed["category"],
                parsed["sentiment"],
                len(parsed["explicit_keywords"]),
                len(parsed["implicit_keywords"]),
            )

            return EnrichmentResult(
                post_id=post_id,
                explicit_keywords=parsed["explicit_keywords"],
                implicit_keywords=parsed["implicit_keywords"],
                category=parsed["category"],
                sentiment=parsed["sentiment"],
                entities=parsed["entities"],
                input_tokens=completion.prompt_tokens,
                output_tokens=completion.completion_tokens,
                processing_time_ms=processing_time_ms,
                success=True,
            )

        except GroqRateLimitError as error:
            error_msg = f"Rate limit exceeded: {error}"
            logger.warning("Post %s enrichment failed: %s", post_id, error_msg)
            return self._create_empty_result(
                post_id,
                success=False,
                error_message=error_msg,
            )

        except GroqTimeoutError as error:
            error_msg = f"Request timed out: {error}"
            logger.warning("Post %s enrichment failed: %s", post_id, error_msg)
            return self._create_empty_result(
                post_id,
                success=False,
                error_message=error_msg,
            )

        except JSONParseError as error:
            error_msg = f"Invalid JSON response: {error}"
            logger.warning("Post %s enrichment failed: %s", post_id, error_msg)
            return self._create_empty_result(
                post_id,
                success=False,
                error_message=error_msg,
            )

        except GroqError as error:
            error_msg = f"LLM error: {error}"
            logger.error("Post %s enrichment failed: %s", post_id, error_msg)
            return self._create_empty_result(
                post_id,
                success=False,
                error_message=error_msg,
            )

        except Exception as error:
            error_msg = f"Unexpected error: {error}"
            logger.error(
                "Post %s enrichment failed with unexpected error: %s",
                post_id,
                error_msg,
                exc_info=True,
            )
            return self._create_empty_result(
                post_id,
                success=False,
                error_message=error_msg,
            )

    async def enrich_batch(
        self,
        posts: list[tuple[int, str]],
    ) -> list[EnrichmentResult]:
        """Enrich multiple posts, respecting rate limits.

        Processes posts sequentially with rate limiting to avoid
        overwhelming the LLM API.

        Args:
            posts: List of (post_id, text) tuples to enrich

        Returns:
            List of EnrichmentResult objects for each post
        """
        results: list[EnrichmentResult] = []

        logger.info("Starting batch enrichment for %d posts", len(posts))

        for index, (post_id, text) in enumerate(posts):
            # Wait for rate limit (for every request)
            # The rate limiter handles first request specially
            await self._wait_for_rate_limit()

            result = await self.enrich_post(post_id, text)
            results.append(result)

            if not result.success:
                logger.warning(
                    "Batch enrichment: post %s failed: %s",
                    post_id,
                    result.error_message,
                )

        successful = sum(1 for result in results if result.success)
        logger.info(
            "Batch enrichment complete: %d/%d successful",
            successful,
            len(posts),
        )

        return results

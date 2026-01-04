"""
TNSE LLM Enrichment Tasks (WS-5.4)

Celery tasks for enriching posts with LLM-extracted metadata.

Work Stream: WS-5.4 - Celery Tasks for Post Enrichment
Dependencies: WS-5.3 (EnrichmentService), WS-8.1 (Celery pipeline)

Requirements addressed:
- Async tasks for enriching posts via Celery
- Rate limiting (10 requests/minute default)
- Retry logic with exponential backoff
- Metrics logging (posts processed, tokens used, time taken)
- Celery beat schedule for enrich_new_posts (every 5 min)
- Store enrichment results in database
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload

from src.tnse.core.config import get_settings
from src.tnse.core.logging import get_logger
from src.tnse.db.models import (
    LLMUsageLog,
    Post,
    PostContent,
    PostEnrichment,
)
from src.tnse.llm.enrichment_service import EnrichmentResult, EnrichmentService
from src.tnse.llm.groq_client import (
    GroqAuthenticationError,
    GroqClient,
    GroqRateLimitError,
    GroqTimeoutError,
)

# Module-level logger for task logging
logger = get_logger(__name__)

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    GroqRateLimitError,
    GroqTimeoutError,
)

# Groq model pricing (per 1M tokens) - as of January 2026
# These are estimates and should be updated based on actual pricing
GROQ_PRICING = {
    "qwen-qwq-32b": {"input": 0.15, "output": 0.60},  # Placeholder pricing
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "default": {"input": 0.15, "output": 0.60},
}


def get_enrichment_rate_limit() -> int:
    """Get the enrichment rate limit from environment or default.

    Returns:
        Rate limit in requests per minute (default: 10).
    """
    return int(os.environ.get("ENRICHMENT_RATE_LIMIT", "10"))


def create_db_session() -> async_sessionmaker[AsyncSession]:
    """Create an async database session factory for Celery tasks.

    Returns:
        Async session factory for database operations.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database.async_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_enrichment_service() -> EnrichmentService | None:
    """Create an EnrichmentService instance with Groq client.

    Returns:
        EnrichmentService instance, or None if LLM not configured.
    """
    settings = get_settings()

    # Check if Groq API is configured
    if not settings.groq.api_key:
        logger.warning(
            "Groq API key not configured - LLM enrichment disabled",
            hint="Set GROQ_API_KEY environment variable"
        )
        return None

    try:
        client = GroqClient.from_settings(settings.groq)
        return EnrichmentService(llm_client=client)
    except Exception as error:
        logger.error(
            "Failed to create EnrichmentService",
            error=str(error)
        )
        return None


def _estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "qwen-qwq-32b"
) -> Decimal:
    """Estimate the cost of an LLM call.

    Args:
        prompt_tokens: Number of prompt tokens.
        completion_tokens: Number of completion tokens.
        model: Model identifier.

    Returns:
        Estimated cost in USD.
    """
    pricing = GROQ_PRICING.get(model, GROQ_PRICING["default"])
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return Decimal(str(round(input_cost + output_cost, 6)))


async def _store_enrichment_result(
    session: AsyncSession,
    result: EnrichmentResult,
    model_used: str,
) -> None:
    """Store enrichment result in database.

    Creates PostEnrichment and LLMUsageLog records for successful enrichments.

    Args:
        session: Database session.
        result: EnrichmentResult from enrichment service.
        model_used: LLM model identifier.
    """
    if not result.success:
        # Don't store failed enrichments in PostEnrichment
        # But we might want to log the attempt
        logger.debug(
            "Skipping storage for failed enrichment",
            post_id=result.post_id,
            error=result.error_message
        )
        return

    # Create PostEnrichment record
    enrichment = PostEnrichment(
        post_id=str(result.post_id),
        explicit_keywords=result.explicit_keywords,
        implicit_keywords=result.implicit_keywords,
        category=result.category,
        sentiment=result.sentiment,
        entities=result.entities,
        model_used=model_used,
        token_count=result.input_tokens + result.output_tokens,
        processing_time_ms=result.processing_time_ms,
        enriched_at=datetime.now(timezone.utc),
    )
    session.add(enrichment)

    # Create LLMUsageLog record
    estimated_cost = _estimate_cost(
        result.input_tokens,
        result.output_tokens,
        model_used
    )
    usage_log = LLMUsageLog(
        model=model_used,
        prompt_tokens=result.input_tokens,
        completion_tokens=result.output_tokens,
        total_tokens=result.input_tokens + result.output_tokens,
        estimated_cost_usd=estimated_cost,
        task_name="enrich_post",
        posts_processed=1,
        created_at=datetime.now(timezone.utc),
    )
    session.add(usage_log)


async def _enrich_post_async(
    post_id: int,
    service: EnrichmentService,
    session_factory: async_sessionmaker[AsyncSession],
    model_used: str,
) -> dict[str, Any]:
    """Async implementation of single post enrichment.

    Args:
        post_id: ID of the post to enrich.
        service: EnrichmentService instance.
        session_factory: Database session factory.
        model_used: LLM model identifier.

    Returns:
        Dictionary with enrichment results.
    """
    async with session_factory() as session:
        # Get the post with its content
        result = await session.execute(
            select(Post)
            .options(joinedload(Post.content))
            .where(Post.id == str(post_id))
        )
        post = result.scalar_one_or_none()

        if post is None:
            logger.warning(
                "Post not found for enrichment",
                post_id=post_id
            )
            return {
                "status": "error",
                "post_id": post_id,
                "errors": ["Post not found"],
            }

        # Check if already enriched
        existing = await session.execute(
            select(PostEnrichment).where(PostEnrichment.post_id == str(post_id))
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug(
                "Post already enriched, skipping",
                post_id=post_id
            )
            return {
                "status": "skipped",
                "post_id": post_id,
                "reason": "Already enriched",
            }

        # Get text content
        text_content = None
        if post.content:
            text_content = post.content.text_content

        if not text_content:
            logger.debug(
                "Post has no text content, skipping enrichment",
                post_id=post_id
            )
            return {
                "status": "skipped",
                "post_id": post_id,
                "reason": "No text content",
            }

        # Perform enrichment
        try:
            enrichment_result = await service.enrich_post(
                post_id=post_id,
                text=text_content,
            )
        except Exception as error:
            logger.error(
                "Enrichment failed for post",
                post_id=post_id,
                error=str(error)
            )
            return {
                "status": "error",
                "post_id": post_id,
                "errors": [str(error)],
            }

        # Store result in database
        try:
            await _store_enrichment_result(session, enrichment_result, model_used)
            await session.commit()
        except Exception as error:
            logger.error(
                "Failed to store enrichment result",
                post_id=post_id,
                error=str(error)
            )
            await session.rollback()
            return {
                "status": "error",
                "post_id": post_id,
                "errors": [f"Storage error: {error}"],
            }

        logger.info(
            "Post enriched successfully",
            post_id=post_id,
            category=enrichment_result.category,
            sentiment=enrichment_result.sentiment,
            tokens_used=enrichment_result.input_tokens + enrichment_result.output_tokens,
            processing_time_ms=enrichment_result.processing_time_ms,
        )

        return {
            "status": "completed" if enrichment_result.success else "error",
            "post_id": post_id,
            "tokens_used": enrichment_result.input_tokens + enrichment_result.output_tokens,
            "processing_time_ms": enrichment_result.processing_time_ms,
            "category": enrichment_result.category,
            "sentiment": enrichment_result.sentiment,
        }


async def _enrich_new_posts_async(
    limit: int,
    service: EnrichmentService,
    session_factory: async_sessionmaker[AsyncSession],
    model_used: str,
) -> dict[str, Any]:
    """Async implementation of batch enrichment for new posts.

    Finds posts that don't have enrichment data yet and enriches them.

    Args:
        limit: Maximum number of posts to process.
        service: EnrichmentService instance.
        session_factory: Database session factory.
        model_used: LLM model identifier.

    Returns:
        Dictionary with batch processing results.
    """
    posts_processed = 0
    posts_enriched = 0
    posts_failed = 0
    total_tokens = 0
    errors: list[dict[str, Any]] = []

    async with session_factory() as session:
        # Find posts without enrichment that have content
        # Using a subquery to find posts not in post_enrichments
        subquery = select(PostEnrichment.post_id)
        result = await session.execute(
            select(Post)
            .options(joinedload(Post.content))
            .where(Post.id.notin_(subquery))
            .limit(limit)
        )
        posts = result.scalars().unique().all()

    logger.info(
        "Starting batch enrichment",
        posts_found=len(posts),
        limit=limit
    )

    if not posts:
        return {
            "status": "completed",
            "posts_processed": 0,
            "posts_enriched": 0,
            "posts_failed": 0,
            "total_tokens": 0,
        }

    rate_limit = get_enrichment_rate_limit()
    min_interval = 60.0 / rate_limit if rate_limit > 0 else 0

    last_request_time = 0.0

    for post in posts:
        posts_processed += 1

        # Apply rate limiting
        if min_interval > 0 and last_request_time > 0:
            elapsed = time.monotonic() - last_request_time
            wait_time = min_interval - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        last_request_time = time.monotonic()

        # Enrich the post
        try:
            result = await _enrich_post_async(
                post_id=post.id,
                service=service,
                session_factory=session_factory,
                model_used=model_used,
            )

            if result["status"] == "completed":
                posts_enriched += 1
                total_tokens += result.get("tokens_used", 0)
            elif result["status"] == "error":
                posts_failed += 1
                errors.append({
                    "post_id": str(post.id),
                    "errors": result.get("errors", []),
                })
        except Exception as error:
            posts_failed += 1
            errors.append({
                "post_id": str(post.id),
                "errors": [str(error)],
            })

    status = "completed"
    if posts_failed > 0 and posts_enriched == 0:
        status = "error"
    elif posts_failed > 0:
        status = "partial"

    logger.info(
        "Batch enrichment complete",
        posts_processed=posts_processed,
        posts_enriched=posts_enriched,
        posts_failed=posts_failed,
        total_tokens=total_tokens,
        status=status,
    )

    return {
        "status": status,
        "posts_processed": posts_processed,
        "posts_enriched": posts_enriched,
        "posts_failed": posts_failed,
        "total_tokens": total_tokens,
        "errors": errors,
    }


async def _enrich_channel_posts_async(
    channel_id: str,
    limit: int,
    service: EnrichmentService,
    session_factory: async_sessionmaker[AsyncSession],
    model_used: str,
) -> dict[str, Any]:
    """Async implementation of channel-specific batch enrichment.

    Finds unenriched posts from a specific channel and enriches them.

    Args:
        channel_id: UUID of the channel.
        limit: Maximum number of posts to process.
        service: EnrichmentService instance.
        session_factory: Database session factory.
        model_used: LLM model identifier.

    Returns:
        Dictionary with batch processing results.
    """
    posts_processed = 0
    posts_enriched = 0
    posts_failed = 0
    total_tokens = 0
    errors: list[dict[str, Any]] = []

    try:
        channel_uuid = UUID(channel_id)
    except ValueError as error:
        logger.error(
            "Invalid channel ID format",
            channel_id=channel_id,
            error=str(error)
        )
        return {
            "status": "error",
            "channel_id": channel_id,
            "posts_processed": 0,
            "errors": [f"Invalid channel ID: {error}"],
        }

    async with session_factory() as session:
        # Find posts from channel without enrichment
        subquery = select(PostEnrichment.post_id)
        result = await session.execute(
            select(Post)
            .options(joinedload(Post.content))
            .where(
                Post.channel_id == channel_uuid,
                Post.id.notin_(subquery)
            )
            .limit(limit)
        )
        posts = result.scalars().unique().all()

    logger.info(
        "Starting channel enrichment",
        channel_id=channel_id,
        posts_found=len(posts),
        limit=limit
    )

    if not posts:
        return {
            "status": "completed",
            "channel_id": channel_id,
            "posts_processed": 0,
            "posts_enriched": 0,
            "posts_failed": 0,
            "total_tokens": 0,
        }

    rate_limit = get_enrichment_rate_limit()
    min_interval = 60.0 / rate_limit if rate_limit > 0 else 0

    last_request_time = 0.0

    for post in posts:
        posts_processed += 1

        # Apply rate limiting
        if min_interval > 0 and last_request_time > 0:
            elapsed = time.monotonic() - last_request_time
            wait_time = min_interval - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        last_request_time = time.monotonic()

        # Enrich the post
        try:
            result = await _enrich_post_async(
                post_id=post.id,
                service=service,
                session_factory=session_factory,
                model_used=model_used,
            )

            if result["status"] == "completed":
                posts_enriched += 1
                total_tokens += result.get("tokens_used", 0)
            elif result["status"] == "error":
                posts_failed += 1
                errors.append({
                    "post_id": str(post.id),
                    "errors": result.get("errors", []),
                })
        except Exception as error:
            posts_failed += 1
            errors.append({
                "post_id": str(post.id),
                "errors": [str(error)],
            })

    status = "completed"
    if posts_failed > 0 and posts_enriched == 0:
        status = "error"
    elif posts_failed > 0:
        status = "partial"

    logger.info(
        "Channel enrichment complete",
        channel_id=channel_id,
        posts_processed=posts_processed,
        posts_enriched=posts_enriched,
        posts_failed=posts_failed,
        total_tokens=total_tokens,
        status=status,
    )

    return {
        "status": status,
        "channel_id": channel_id,
        "posts_processed": posts_processed,
        "posts_enriched": posts_enriched,
        "posts_failed": posts_failed,
        "total_tokens": total_tokens,
        "errors": errors,
    }


@shared_task(
    name="src.tnse.llm.tasks.enrich_post",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=RETRYABLE_EXCEPTIONS,
)
def enrich_post(self, post_id: int) -> dict[str, Any]:
    """Enrich a single post with LLM-extracted metadata.

    This Celery task fetches a post from the database, sends it to the
    LLM for enrichment, and stores the results.

    Args:
        post_id: ID of the post to enrich.

    Returns:
        Dictionary with enrichment results.
    """
    start_time = time.time()
    logger.info(
        "Starting enrich_post task",
        post_id=post_id
    )

    # Create service dependencies
    try:
        session_factory = create_db_session()
    except Exception as error:
        logger.exception(
            "Failed to create database session",
            post_id=post_id,
            error=str(error)
        )
        return {
            "status": "error",
            "post_id": post_id,
            "errors": [f"Database error: {error}"],
            "duration_seconds": round(time.time() - start_time, 2),
        }

    service = create_enrichment_service()

    if service is None:
        logger.warning(
            "EnrichmentService not available - skipping enrichment",
            post_id=post_id,
            hint="Configure GROQ_API_KEY environment variable"
        )
        return {
            "status": "skipped",
            "post_id": post_id,
            "reason": "LLM not configured - set GROQ_API_KEY",
        }

    settings = get_settings()
    model_used = settings.groq.model

    try:
        # Run the async enrichment
        result = asyncio.run(_enrich_post_async(
            post_id=post_id,
            service=service,
            session_factory=session_factory,
            model_used=model_used,
        ))

        elapsed = time.time() - start_time
        result["duration_seconds"] = round(elapsed, 2)

        logger.info(
            "enrich_post task completed",
            post_id=post_id,
            duration_seconds=result["duration_seconds"],
            status=result["status"]
        )

        return result

    except Exception as error:
        elapsed = time.time() - start_time
        logger.exception(
            "enrich_post task failed",
            post_id=post_id,
            error=str(error),
            duration_seconds=round(elapsed, 2)
        )
        return {
            "status": "error",
            "post_id": post_id,
            "errors": [str(error)],
            "duration_seconds": round(elapsed, 2),
        }


@shared_task(
    name="src.tnse.llm.tasks.enrich_new_posts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
)
def enrich_new_posts(self, limit: int = 100) -> dict[str, Any]:
    """Find and enrich posts that don't have enrichment data yet.

    This Celery task queries the database for posts without enrichment
    records and processes them in a batch with rate limiting.

    Args:
        limit: Maximum number of posts to process (default: 100).

    Returns:
        Dictionary with batch processing statistics.
    """
    start_time = time.time()
    logger.info(
        "Starting enrich_new_posts task",
        limit=limit
    )

    # Create service dependencies
    try:
        session_factory = create_db_session()
    except Exception as error:
        logger.exception(
            "Failed to create database session",
            error=str(error)
        )
        return {
            "status": "error",
            "posts_processed": 0,
            "errors": [f"Database error: {error}"],
            "duration_seconds": round(time.time() - start_time, 2),
        }

    service = create_enrichment_service()

    if service is None:
        logger.warning(
            "EnrichmentService not available - skipping batch enrichment",
            hint="Configure GROQ_API_KEY environment variable"
        )
        return {
            "status": "skipped",
            "posts_processed": 0,
            "reason": "LLM not configured - set GROQ_API_KEY",
        }

    settings = get_settings()
    model_used = settings.groq.model

    try:
        # Run the async batch enrichment
        result = asyncio.run(_enrich_new_posts_async(
            limit=limit,
            service=service,
            session_factory=session_factory,
            model_used=model_used,
        ))

        elapsed = time.time() - start_time
        result["duration_seconds"] = round(elapsed, 2)

        logger.info(
            "enrich_new_posts task completed",
            duration_seconds=result["duration_seconds"],
            posts_processed=result["posts_processed"],
            posts_enriched=result["posts_enriched"],
            status=result["status"]
        )

        return result

    except Exception as error:
        elapsed = time.time() - start_time
        logger.exception(
            "enrich_new_posts task failed",
            error=str(error),
            duration_seconds=round(elapsed, 2)
        )
        return {
            "status": "error",
            "posts_processed": 0,
            "errors": [str(error)],
            "duration_seconds": round(elapsed, 2),
        }


@shared_task(
    name="src.tnse.llm.tasks.enrich_channel_posts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
)
def enrich_channel_posts(self, channel_id: str, limit: int = 50) -> dict[str, Any]:
    """Enrich all unenriched posts from a specific channel.

    This Celery task queries the database for unenriched posts from
    a specific channel and processes them with rate limiting.

    Args:
        channel_id: UUID of the channel to process.
        limit: Maximum number of posts to process (default: 50).

    Returns:
        Dictionary with batch processing statistics.
    """
    start_time = time.time()
    logger.info(
        "Starting enrich_channel_posts task",
        channel_id=channel_id,
        limit=limit
    )

    # Create service dependencies
    try:
        session_factory = create_db_session()
    except Exception as error:
        logger.exception(
            "Failed to create database session",
            channel_id=channel_id,
            error=str(error)
        )
        return {
            "status": "error",
            "channel_id": channel_id,
            "posts_processed": 0,
            "errors": [f"Database error: {error}"],
            "duration_seconds": round(time.time() - start_time, 2),
        }

    service = create_enrichment_service()

    if service is None:
        logger.warning(
            "EnrichmentService not available - skipping channel enrichment",
            channel_id=channel_id,
            hint="Configure GROQ_API_KEY environment variable"
        )
        return {
            "status": "skipped",
            "channel_id": channel_id,
            "posts_processed": 0,
            "reason": "LLM not configured - set GROQ_API_KEY",
        }

    settings = get_settings()
    model_used = settings.groq.model

    try:
        # Run the async channel enrichment
        result = asyncio.run(_enrich_channel_posts_async(
            channel_id=channel_id,
            limit=limit,
            service=service,
            session_factory=session_factory,
            model_used=model_used,
        ))

        elapsed = time.time() - start_time
        result["duration_seconds"] = round(elapsed, 2)

        logger.info(
            "enrich_channel_posts task completed",
            channel_id=channel_id,
            duration_seconds=result["duration_seconds"],
            posts_processed=result["posts_processed"],
            posts_enriched=result.get("posts_enriched", 0),
            status=result["status"]
        )

        return result

    except Exception as error:
        elapsed = time.time() - start_time
        logger.exception(
            "enrich_channel_posts task failed",
            channel_id=channel_id,
            error=str(error),
            duration_seconds=round(elapsed, 2)
        )
        return {
            "status": "error",
            "channel_id": channel_id,
            "posts_processed": 0,
            "errors": [str(error)],
            "duration_seconds": round(elapsed, 2),
        }

"""
TNSE Content Collection Tasks

Celery tasks for collecting content from monitored Telegram channels.

Work Stream: WS-1.6 - Content Collection Pipeline
Work Stream: WS-8.1 - Wire Celery Tasks to ContentCollector

Requirements addressed:
- Create content collection job
- Implement 24-hour content window
- Extract text content
- Extract media metadata
- Detect forwarded messages
- Store in database
- Schedule periodic runs (every 15-30 min)
- Wire Celery tasks to ContentCollector
- Add proper error handling and retry logic
- Add metrics/logging for collection job status
"""

import asyncio
import time
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.tnse.core.config import get_settings
from src.tnse.core.logging import get_logger
from src.tnse.db.models import (
    Channel,
    ChannelHealthLog,
    ChannelStatus,
    Post,
    PostContent,
    PostMedia,
    EngagementMetrics,
    ReactionCount,
)
from src.tnse.pipeline.collector import ContentCollector
from src.tnse.pipeline.storage import ContentStorage
from src.tnse.telegram.client import TelegramClientConfig, TelethonClient

# Module-level logger for task logging
logger = get_logger(__name__)


def create_db_session() -> async_sessionmaker[AsyncSession]:
    """Create an async database session factory for Celery tasks.

    Returns:
        Async session factory for database operations.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database.async_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_content_collector() -> ContentCollector | None:
    """Create a ContentCollector instance with Telegram client.

    Returns:
        ContentCollector instance, or None if Telegram credentials not configured.
    """
    settings = get_settings()

    # Check if Telegram API credentials are configured
    if not settings.telegram.api_id or not settings.telegram.api_hash:
        logger.warning(
            "Telegram API credentials not configured - content collection disabled",
            hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH"
        )
        return None

    config = TelegramClientConfig.from_settings(settings)
    client = TelethonClient(config)
    return ContentCollector(
        telegram_client=client,
        content_window_hours=settings.content_window_hours,
    )


def create_content_storage(session_factory: async_sessionmaker[AsyncSession]) -> ContentStorage:
    """Create a ContentStorage instance with database session factory.

    Args:
        session_factory: Async session factory for database operations.

    Returns:
        ContentStorage instance for persisting content.
    """
    return ContentStorage(session_factory=session_factory)


# Alias functions for test compatibility
get_telegram_client = create_content_collector
get_db_session = create_db_session
get_content_storage = create_content_storage


async def _collect_channel_content_async(
    channel_id: str,
    collector: ContentCollector,
    storage: ContentStorage,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """Async implementation of channel content collection.

    Args:
        channel_id: UUID of the channel to collect content from.
        collector: ContentCollector instance for fetching messages.
        storage: ContentStorage instance for persisting content.
        session_factory: Database session factory.

    Returns:
        Dictionary with collection results.
    """
    posts_collected = 0
    errors: list[str] = []

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
            "posts_collected": 0,
            "errors": [f"Invalid channel ID: {error}"],
        }

    async with session_factory() as session:
        # Get channel from database
        result = await session.execute(
            select(Channel).where(Channel.id == channel_uuid)
        )
        channel = result.scalar_one_or_none()

        if channel is None:
            logger.warning(
                "Channel not found in database",
                channel_id=channel_id
            )
            return {
                "status": "error",
                "channel_id": channel_id,
                "posts_collected": 0,
                "errors": ["Channel not found in database"],
            }

        logger.info(
            "Collecting content from channel",
            channel_id=channel_id,
            channel_username=channel.username,
            telegram_id=channel.telegram_id
        )

        # Collect messages from Telegram
        collection_health_status = ChannelStatus.HEALTHY
        collection_error_message = None
        try:
            collection_result = await collector.collect_channel_messages(
                telegram_channel_id=channel.telegram_id,
                channel_uuid=channel_uuid,
                limit=100,
            )
            messages = collection_result.get("messages", [])
        except Exception as error:
            logger.error(
                "Failed to collect messages from Telegram",
                channel_id=channel_id,
                error=str(error)
            )
            # Determine health status based on error type
            error_str = str(error).lower()
            if "rate" in error_str or "flood" in error_str:
                collection_health_status = ChannelStatus.RATE_LIMITED
            elif "not found" in error_str or "invalid" in error_str:
                collection_health_status = ChannelStatus.INACCESSIBLE
            else:
                collection_health_status = ChannelStatus.INACCESSIBLE
            collection_error_message = str(error)

            # Log health status for failed collection
            health_log = ChannelHealthLog(
                channel_id=channel_uuid,
                status=collection_health_status.value,
                error_message=collection_error_message,
            )
            session.add(health_log)
            await session.commit()

            return {
                "status": "error",
                "channel_id": channel_id,
                "posts_collected": 0,
                "errors": [f"Telegram collection error: {error}"],
            }

        # Store each message in the database
        for message_data in messages:
            try:
                # Check if post already exists
                existing = await session.execute(
                    select(Post).where(
                        Post.channel_id == channel_uuid,
                        Post.telegram_message_id == message_data["telegram_message_id"]
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    logger.debug(
                        "Post already exists, skipping",
                        telegram_message_id=message_data["telegram_message_id"]
                    )
                    continue

                # Create post record
                post_record = storage.create_post_record(message_data)
                post = Post(**post_record)
                session.add(post)
                await session.flush()  # Get the post ID

                # Create content record
                content_record = storage.create_content_record(post.id, message_data)
                content = PostContent(**content_record)
                session.add(content)

                # Create media records
                media_records = storage.create_media_records(post.id, message_data)
                for media_record in media_records:
                    media = PostMedia(**media_record)
                    session.add(media)

                # Create engagement metrics
                engagement_record = storage.create_engagement_record(
                    post.id,
                    message_data,
                    subscriber_count=channel.subscriber_count,
                )
                engagement = EngagementMetrics(**engagement_record)
                session.add(engagement)
                await session.flush()  # Get the engagement ID

                # Create reaction count records
                reactions = message_data.get("reactions", {})
                reaction_records = storage.create_reaction_records(
                    engagement.id,
                    reactions,
                )
                for reaction_record in reaction_records:
                    reaction = ReactionCount(**reaction_record)
                    session.add(reaction)

                posts_collected += 1

            except Exception as error:
                logger.error(
                    "Failed to store message",
                    telegram_message_id=message_data.get("telegram_message_id"),
                    error=str(error)
                )
                errors.append(f"Storage error for message {message_data.get('telegram_message_id')}: {error}")

        # Log health status for successful/partial collection
        health_status = ChannelStatus.HEALTHY if not errors else ChannelStatus.HEALTHY
        health_error_message = None if not errors else f"{len(errors)} storage errors"
        health_log = ChannelHealthLog(
            channel_id=channel_uuid,
            status=health_status.value,
            error_message=health_error_message,
        )
        session.add(health_log)

        # Commit all changes including health log
        await session.commit()

    status = "completed" if not errors else "partial"
    logger.info(
        "Content collection completed",
        channel_id=channel_id,
        posts_collected=posts_collected,
        errors_count=len(errors),
        status=status
    )

    return {
        "status": status,
        "channel_id": channel_id,
        "posts_collected": posts_collected,
        "errors": errors,
    }


async def _collect_all_channels_async(
    collector: ContentCollector,
    storage: ContentStorage,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """Async implementation of all channels content collection.

    Args:
        collector: ContentCollector instance for fetching messages.
        storage: ContentStorage instance for persisting content.
        session_factory: Database session factory.

    Returns:
        Dictionary with collection statistics.
    """
    channels_processed = 0
    total_posts_collected = 0
    errors: list[dict[str, Any]] = []

    async with session_factory() as session:
        # Get all active channels
        result = await session.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = result.scalars().all()

    logger.info(
        "Starting collection for all channels",
        total_channels=len(channels)
    )

    for channel in channels:
        channel_result = await _collect_channel_content_async(
            channel_id=str(channel.id),
            collector=collector,
            storage=storage,
            session_factory=session_factory,
        )

        channels_processed += 1
        total_posts_collected += channel_result.get("posts_collected", 0)

        if channel_result.get("errors"):
            errors.append({
                "channel_id": str(channel.id),
                "channel_username": channel.username,
                "errors": channel_result["errors"],
            })

    status = "completed"
    if errors and channels_processed == len(errors):
        status = "error"
    elif errors:
        status = "partial"

    logger.info(
        "Collection completed for all channels",
        channels_processed=channels_processed,
        total_posts_collected=total_posts_collected,
        channels_with_errors=len(errors),
        status=status
    )

    return {
        "status": status,
        "channels_processed": channels_processed,
        "posts_collected": total_posts_collected,
        "errors": errors,
    }


@shared_task(
    name="src.tnse.pipeline.tasks.collect_all_channels",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def collect_all_channels(self) -> dict[str, Any]:
    """Collect content from all active monitored channels.

    This is the main periodic task that triggers collection for all channels.
    Wired to ContentCollector and ContentStorage for actual content fetching.

    Returns:
        Dictionary with collection statistics.
    """
    start_time = time.time()
    logger.info("Starting collect_all_channels task")

    # Create service dependencies
    session_factory = create_db_session()
    collector = create_content_collector()
    storage = create_content_storage(session_factory)

    if collector is None:
        logger.warning(
            "ContentCollector not available - skipping collection",
            hint="Configure TELEGRAM_API_ID and TELEGRAM_API_HASH"
        )
        return {
            "status": "skipped",
            "channels_processed": 0,
            "posts_collected": 0,
            "reason": "Telegram API credentials not configured",
        }

    try:
        # Run the async collection
        result = asyncio.run(_collect_all_channels_async(
            collector=collector,
            storage=storage,
            session_factory=session_factory,
        ))

        elapsed = time.time() - start_time
        result["duration_seconds"] = round(elapsed, 2)

        logger.info(
            "collect_all_channels task completed",
            duration_seconds=result["duration_seconds"],
            channels_processed=result["channels_processed"],
            posts_collected=result["posts_collected"]
        )

        return result

    except Exception as error:
        elapsed = time.time() - start_time
        logger.exception(
            "collect_all_channels task failed",
            error=str(error),
            duration_seconds=round(elapsed, 2)
        )
        return {
            "status": "error",
            "channels_processed": 0,
            "posts_collected": 0,
            "errors": [str(error)],
            "duration_seconds": round(elapsed, 2),
        }


@shared_task(
    name="src.tnse.pipeline.tasks.collect_channel_content",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def collect_channel_content(self, channel_id: str) -> dict[str, Any]:
    """Collect content from a specific channel.

    Wired to ContentCollector and ContentStorage for actual content fetching.

    Args:
        channel_id: UUID of the channel to collect content from.

    Returns:
        Dictionary with collection results for the channel.
    """
    start_time = time.time()
    logger.info(
        "Starting collect_channel_content task",
        channel_id=channel_id
    )

    # Create service dependencies
    session_factory = create_db_session()
    collector = create_content_collector()
    storage = create_content_storage(session_factory)

    if collector is None:
        logger.warning(
            "ContentCollector not available - skipping collection",
            channel_id=channel_id,
            hint="Configure TELEGRAM_API_ID and TELEGRAM_API_HASH"
        )
        return {
            "status": "skipped",
            "channel_id": channel_id,
            "posts_collected": 0,
            "reason": "Telegram API credentials not configured",
        }

    try:
        # Run the async collection
        result = asyncio.run(_collect_channel_content_async(
            channel_id=channel_id,
            collector=collector,
            storage=storage,
            session_factory=session_factory,
        ))

        elapsed = time.time() - start_time
        result["duration_seconds"] = round(elapsed, 2)

        logger.info(
            "collect_channel_content task completed",
            channel_id=channel_id,
            duration_seconds=result["duration_seconds"],
            posts_collected=result["posts_collected"]
        )

        return result

    except Exception as error:
        elapsed = time.time() - start_time
        logger.exception(
            "collect_channel_content task failed",
            channel_id=channel_id,
            error=str(error),
            duration_seconds=round(elapsed, 2)
        )
        return {
            "status": "error",
            "channel_id": channel_id,
            "posts_collected": 0,
            "errors": [str(error)],
            "duration_seconds": round(elapsed, 2),
        }

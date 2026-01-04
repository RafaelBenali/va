"""
TNSE Telegram Bot Sync Command Handlers

Provides command handlers for manual channel synchronization.
Work Stream: WS-9.2 - Manual Channel Sync Command

Commands:
- /sync - Trigger content collection for all monitored channels
- /sync @channel - Trigger content collection for specific channel

Requirements:
- Progress feedback (typing indicator, status messages)
- Rate limiting to prevent abuse (max 1 sync per 5 minutes)
- Restrict to admin users (configurable whitelist)
"""

import re
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger
from src.tnse.db.models import Channel
from src.tnse.pipeline.tasks import collect_all_channels, collect_channel_content

logger = get_logger(__name__)


# Type alias for handler functions
HandlerFunc = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]


# Regex pattern for extracting username from various formats
TME_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/)?([a-zA-Z0-9_]+)"
)


class SyncRateLimiter:
    """Rate limiter for sync commands to prevent abuse.

    Tracks the last sync timestamp per user and enforces a cooldown period
    between sync requests.

    Args:
        cooldown_seconds: Minimum seconds between sync requests per user.
            Defaults to 300 (5 minutes).

    Example:
        >>> limiter = SyncRateLimiter(cooldown_seconds=300)
        >>> limiter.can_sync(user_id=123)
        True
        >>> limiter.record_sync(user_id=123)
        >>> limiter.can_sync(user_id=123)
        False
    """

    def __init__(self, cooldown_seconds: int = 300) -> None:
        """Initialize the rate limiter.

        Args:
            cooldown_seconds: Minimum seconds between sync requests.
        """
        self.cooldown_seconds = cooldown_seconds
        self._last_sync: dict[int, datetime] = {}

    def can_sync(self, user_id: int) -> bool:
        """Check if user is allowed to sync.

        Args:
            user_id: Telegram user ID to check.

        Returns:
            True if user can sync, False if still in cooldown.
        """
        last_sync = self._last_sync.get(user_id)
        if last_sync is None:
            return True

        elapsed = datetime.now(timezone.utc) - last_sync
        return elapsed >= timedelta(seconds=self.cooldown_seconds)

    def record_sync(self, user_id: int) -> None:
        """Record a sync request for rate limiting.

        Args:
            user_id: Telegram user ID that initiated the sync.
        """
        self._last_sync[user_id] = datetime.now(timezone.utc)

    def get_remaining_cooldown(self, user_id: int) -> int:
        """Get remaining cooldown time in seconds.

        Args:
            user_id: Telegram user ID to check.

        Returns:
            Remaining cooldown seconds, or 0 if no cooldown active.
        """
        last_sync = self._last_sync.get(user_id)
        if last_sync is None:
            return 0

        elapsed = datetime.now(timezone.utc) - last_sync
        remaining = self.cooldown_seconds - elapsed.total_seconds()
        return max(0, int(remaining))


def extract_channel_username(identifier: str) -> str:
    """
    Extract channel username from various input formats.

    Handles:
    - @username
    - username
    - https://t.me/username
    - https://telegram.me/username

    Args:
        identifier: Channel identifier in any format

    Returns:
        Clean username without @ or URL prefix
    """
    # Strip whitespace first
    identifier = identifier.strip()

    # Check if it's a URL
    url_match = TME_URL_PATTERN.match(identifier)
    if url_match:
        return url_match.group(1)

    # Strip @ prefix if present
    return identifier.lstrip("@")


def format_cooldown_time(seconds: int) -> str:
    """Format cooldown time for display.

    Args:
        seconds: Number of seconds remaining.

    Returns:
        Human-readable time string.
    """
    if seconds >= 60:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''} and {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{seconds} second{'s' if seconds != 1 else ''}"


async def sync_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /sync command.

    Triggers content collection for channels. Without arguments, syncs all
    monitored channels. With a channel argument, syncs only that channel.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    logger.info(
        "Sync command received",
        user_id=user_id,
        args=context.args if context.args else []
    )

    # Get database session factory from bot_data
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        await update.message.reply_text(
            "Sync is not configured.\n\n"
            "The database connection is required for channel synchronization.\n\n"
            "Please contact the administrator to check the database configuration."
        )
        logger.error(
            "Database session factory not configured in bot_data",
            hint="Check POSTGRES_* environment variables"
        )
        return

    # Get rate limiter from bot_data
    rate_limiter = context.bot_data.get("sync_rate_limiter")

    if rate_limiter and user_id:
        if not rate_limiter.can_sync(user_id):
            remaining = rate_limiter.get_remaining_cooldown(user_id)
            await update.message.reply_text(
                f"Rate limit exceeded.\n\n"
                f"Please wait {remaining} seconds before syncing again.\n\n"
                f"This cooldown helps prevent overloading the Telegram API."
            )
            logger.info(
                "Sync rate limited",
                user_id=user_id,
                remaining_seconds=remaining
            )
            return

    # Send typing indicator to show progress
    if chat_id:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Determine if syncing specific channel or all channels
    if context.args and len(context.args) > 0:
        # Sync specific channel
        channel_identifier = context.args[0]
        username = extract_channel_username(channel_identifier)

        await _sync_specific_channel(
            update=update,
            context=context,
            username=username,
            db_session_factory=db_session_factory,
            rate_limiter=rate_limiter,
            user_id=user_id,
        )
    else:
        # Sync all channels
        await _sync_all_channels(
            update=update,
            context=context,
            db_session_factory=db_session_factory,
            rate_limiter=rate_limiter,
            user_id=user_id,
        )


async def _sync_specific_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    username: str,
    db_session_factory: Any,
    rate_limiter: SyncRateLimiter | None,
    user_id: int | None,
) -> None:
    """Sync a specific channel by username.

    Args:
        update: The Telegram update object.
        context: The callback context.
        username: Channel username to sync.
        db_session_factory: Database session factory.
        rate_limiter: Rate limiter instance.
        user_id: Telegram user ID.
    """
    logger.info(
        "Syncing specific channel",
        username=username,
        user_id=user_id
    )

    try:
        async with db_session_factory() as session:
            # Find the channel
            query = select(Channel).where(Channel.username == username)
            result = await session.execute(query)
            channel = result.scalar_one_or_none()

            if not channel:
                await update.message.reply_text(
                    f"Channel @{username} is not monitored.\n\n"
                    f"Use /addchannel @{username} to add it first, "
                    f"or use /channels to see all monitored channels."
                )
                logger.info("Channel not found for sync", username=username)
                return

            # Trigger Celery task for this channel
            channel_id = str(channel.id)
            task_result = collect_channel_content.delay(channel_id)

            # Record the sync for rate limiting
            if rate_limiter and user_id:
                rate_limiter.record_sync(user_id)

            await update.message.reply_text(
                f"Sync started for @{channel.username}!\n\n"
                f"Channel: {channel.title}\n"
                f"Task ID: {task_result.id}\n\n"
                f"Content collection is running in the background. "
                f"New posts will appear in search results shortly."
            )

            logger.info(
                "Channel sync task started",
                channel_id=channel_id,
                channel_username=channel.username,
                task_id=task_result.id
            )

    except Exception as error:
        await update.message.reply_text(
            f"Error syncing channel @{username}.\n\n"
            f"Please try again later."
        )
        logger.error(
            "Error syncing specific channel",
            username=username,
            error=str(error)
        )


async def _sync_all_channels(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_session_factory: Any,
    rate_limiter: SyncRateLimiter | None,
    user_id: int | None,
) -> None:
    """Sync all monitored channels.

    Args:
        update: The Telegram update object.
        context: The callback context.
        db_session_factory: Database session factory.
        rate_limiter: Rate limiter instance.
        user_id: Telegram user ID.
    """
    logger.info(
        "Syncing all channels",
        user_id=user_id
    )

    try:
        async with db_session_factory() as session:
            # Get all active channels to count them
            query = select(Channel).where(Channel.is_active == True)
            result = await session.execute(query)
            channels = result.scalars().all()

            if not channels:
                await update.message.reply_text(
                    "No channels to sync.\n\n"
                    "Add a channel first with /addchannel @username"
                )
                logger.info("No channels found for sync")
                return

            channel_count = len(channels)

            # Trigger Celery task for all channels
            task_result = collect_all_channels.delay()

            # Record the sync for rate limiting
            if rate_limiter and user_id:
                rate_limiter.record_sync(user_id)

            await update.message.reply_text(
                f"Sync started for {channel_count} channel{'s' if channel_count != 1 else ''}!\n\n"
                f"Task ID: {task_result.id}\n\n"
                f"Content collection is running in the background. "
                f"New posts will appear in search results shortly."
            )

            logger.info(
                "All channels sync task started",
                channel_count=channel_count,
                task_id=task_result.id
            )

    except Exception as error:
        await update.message.reply_text(
            "Error syncing channels.\n\n"
            "Please try again later."
        )
        logger.error(
            "Error syncing all channels",
            error=str(error)
        )

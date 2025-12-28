"""
TNSE Telegram Bot Channel Management Command Handlers

Provides command handlers for channel management operations.
Work Stream: WS-1.5 - Channel Management (Bot Commands)

Commands:
- /addchannel @username - Add channel to monitor
- /removechannel @username - Remove from monitoring
- /channels - List all monitored channels
- /channelinfo @username - Show channel details
"""

import re
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger

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


def format_subscriber_count(count: int) -> str:
    """
    Format subscriber count for display.

    Args:
        count: Number of subscribers

    Returns:
        Formatted string (e.g., "50K", "1.2M")
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


async def addchannel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /addchannel command.

    Adds a new channel to the monitored list after validating it exists
    and is accessible.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for username argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /addchannel @username\n\n"
            "Example: /addchannel @telegram_news"
        )
        logger.info("addchannel called without arguments", user_id=user_id)
        return

    channel_identifier = context.args[0]
    username = extract_channel_username(channel_identifier)

    logger.info(
        "Adding channel",
        user_id=user_id,
        channel_identifier=channel_identifier,
        username=username
    )

    # Get channel service and database session from bot_data
    channel_service = context.bot_data.get("channel_service")
    db_session_factory = context.bot_data.get("db_session_factory")

    if not channel_service or not db_session_factory:
        await update.message.reply_text(
            "Channel service is not available. Please try again later."
        )
        logger.error("Channel service or database not configured in bot_data")
        return

    # Validate the channel
    try:
        validation_result = await channel_service.validate_channel(username)

        if not validation_result.is_valid:
            error_message = validation_result.error or "Unknown error"
            await update.message.reply_text(
                f"Cannot add channel @{username}.\n\n"
                f"Error: {error_message}"
            )
            logger.warning(
                "Channel validation failed",
                username=username,
                error=error_message
            )
            return

        channel_info = validation_result.channel_info
    except Exception as error:
        await update.message.reply_text(
            f"Error validating channel @{username}.\n\n"
            f"Please check the channel name and try again."
        )
        logger.error(
            "Channel validation exception",
            username=username,
            error=str(error)
        )
        return

    # Check if channel already exists in database
    try:
        from sqlalchemy import select
        from src.tnse.db.models import Channel

        session = db_session_factory()

        # Check for existing channel by username or telegram_id
        query = select(Channel).where(
            (Channel.username == username) |
            (Channel.telegram_id == channel_info.telegram_id)
        )
        result = await session.execute(query)
        existing_channel = result.scalar_one_or_none()

        if existing_channel:
            await update.message.reply_text(
                f"Channel @{existing_channel.username} is already being monitored.\n\n"
                f"Use /channelinfo @{existing_channel.username} to see details."
            )
            logger.info(
                "Channel already exists",
                username=username,
                existing_username=existing_channel.username
            )
            return

        # Create new channel record
        new_channel = Channel(
            telegram_id=channel_info.telegram_id,
            username=channel_info.username,
            title=channel_info.title,
            description=channel_info.description,
            subscriber_count=channel_info.subscriber_count,
            photo_url=channel_info.photo_url,
            invite_link=channel_info.invite_link,
            is_active=True,
        )

        session.add(new_channel)
        await session.commit()

        subscriber_display = format_subscriber_count(channel_info.subscriber_count)

        await update.message.reply_text(
            f"Channel successfully added!\n\n"
            f"Title: {channel_info.title}\n"
            f"Username: @{channel_info.username}\n"
            f"Subscribers: {subscriber_display}\n\n"
            f"The channel is now being monitored for content."
        )

        logger.info(
            "Channel added successfully",
            username=channel_info.username,
            telegram_id=channel_info.telegram_id
        )

    except Exception as error:
        await update.message.reply_text(
            f"Error adding channel @{username} to database.\n\n"
            f"Please try again later."
        )
        logger.error(
            "Database error adding channel",
            username=username,
            error=str(error)
        )


async def removechannel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /removechannel command.

    Removes a channel from monitoring.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for username argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /removechannel @username\n\n"
            "Example: /removechannel @telegram_news"
        )
        logger.info("removechannel called without arguments", user_id=user_id)
        return

    channel_identifier = context.args[0]
    username = extract_channel_username(channel_identifier)

    logger.info(
        "Removing channel",
        user_id=user_id,
        username=username
    )

    # Get database session from bot_data
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        await update.message.reply_text(
            "Database is not available. Please try again later."
        )
        logger.error("Database session factory not configured in bot_data")
        return

    try:
        from sqlalchemy import select
        from src.tnse.db.models import Channel

        session = db_session_factory()

        # Find the channel
        query = select(Channel).where(Channel.username == username)
        result = await session.execute(query)
        existing_channel = result.scalar_one_or_none()

        if not existing_channel:
            await update.message.reply_text(
                f"Channel @{username} is not being monitored.\n\n"
                f"Use /channels to see all monitored channels."
            )
            logger.info("Channel not found for removal", username=username)
            return

        channel_title = existing_channel.title

        # Delete the channel
        await session.delete(existing_channel)
        await session.commit()

        await update.message.reply_text(
            f"Channel removed successfully!\n\n"
            f"Title: {channel_title}\n"
            f"Username: @{username}\n\n"
            f"Content from this channel will no longer be collected."
        )

        logger.info(
            "Channel removed successfully",
            username=username,
            title=channel_title
        )

    except Exception as error:
        await update.message.reply_text(
            f"Error removing channel @{username}.\n\n"
            f"Please try again later."
        )
        logger.error(
            "Database error removing channel",
            username=username,
            error=str(error)
        )


async def channels_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /channels command.

    Lists all monitored channels with their status.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    logger.info("Listing channels", user_id=user_id)

    # Get database session from bot_data
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        await update.message.reply_text(
            "Database is not available. Please try again later."
        )
        logger.error("Database session factory not configured in bot_data")
        return

    try:
        from sqlalchemy import select
        from src.tnse.db.models import Channel

        session = db_session_factory()

        # Get all active channels
        query = select(Channel).where(Channel.is_active == True).order_by(Channel.title)
        result = await session.execute(query)
        channels = result.scalars().all()

        if not channels:
            await update.message.reply_text(
                "No channels are currently being monitored.\n\n"
                "Use /addchannel @username to add a channel."
            )
            logger.info("No channels found")
            return

        # Build channel list message
        channel_count = len(channels)
        message_lines = [
            f"Monitored Channels ({channel_count}):\n"
        ]

        for index, channel in enumerate(channels, start=1):
            subscriber_display = format_subscriber_count(channel.subscriber_count)
            status_indicator = "[Active]" if channel.is_active else "[Inactive]"

            message_lines.append(
                f"{index}. {channel.title}\n"
                f"   @{channel.username} | {subscriber_display} subscribers\n"
                f"   {status_indicator}"
            )

        message_lines.append(
            f"\nUse /channelinfo @username for detailed information."
        )

        await update.message.reply_text("\n".join(message_lines))

        logger.info(
            "Listed channels",
            count=channel_count
        )

    except Exception as error:
        await update.message.reply_text(
            "Error loading channels.\n\n"
            "Please try again later."
        )
        logger.error(
            "Database error listing channels",
            error=str(error)
        )


async def channelinfo_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /channelinfo command.

    Shows detailed information about a monitored channel including
    metadata and health status.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for username argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /channelinfo @username\n\n"
            "Example: /channelinfo @telegram_news"
        )
        logger.info("channelinfo called without arguments", user_id=user_id)
        return

    channel_identifier = context.args[0]
    username = extract_channel_username(channel_identifier)

    logger.info(
        "Getting channel info",
        user_id=user_id,
        username=username
    )

    # Get database session from bot_data
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        await update.message.reply_text(
            "Database is not available. Please try again later."
        )
        logger.error("Database session factory not configured in bot_data")
        return

    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.tnse.db.models import Channel

        session = db_session_factory()

        # Find the channel with health logs
        query = (
            select(Channel)
            .options(selectinload(Channel.health_logs))
            .where(Channel.username == username)
        )
        result = await session.execute(query)
        channel = result.scalar_one_or_none()

        if not channel:
            await update.message.reply_text(
                f"Channel @{username} is not being monitored.\n\n"
                f"Use /addchannel @{username} to start monitoring."
            )
            logger.info("Channel not found for info", username=username)
            return

        # Format channel information
        subscriber_display = format_subscriber_count(channel.subscriber_count)
        status_text = "Active" if channel.is_active else "Inactive"

        # Get latest health status
        health_status = "Unknown"
        last_check = "Never"
        if channel.health_logs:
            # Sort by checked_at descending and get the first
            sorted_logs = sorted(
                channel.health_logs,
                key=lambda log: log.checked_at,
                reverse=True
            )
            latest_log = sorted_logs[0]
            health_status = latest_log.status.replace("_", " ").title()
            last_check = latest_log.checked_at.strftime("%Y-%m-%d %H:%M UTC")

        # Build message
        message_lines = [
            f"Channel Information\n",
            f"Title: {channel.title}",
            f"Username: @{channel.username}",
            f"Subscribers: {subscriber_display}",
            f"Status: {status_text}",
            f"",
            f"Health Status: {health_status}",
            f"Last Check: {last_check}",
            f"",
            f"Added: {channel.created_at.strftime('%Y-%m-%d')}",
        ]

        if channel.description:
            # Truncate description if too long
            description = channel.description
            if len(description) > 200:
                description = description[:197] + "..."
            message_lines.insert(4, f"Description: {description}")

        await update.message.reply_text("\n".join(message_lines))

        logger.info(
            "Showed channel info",
            username=username,
            health_status=health_status
        )

    except Exception as error:
        await update.message.reply_text(
            f"Error loading information for @{username}.\n\n"
            f"Please try again later."
        )
        logger.error(
            "Database error getting channel info",
            username=username,
            error=str(error)
        )

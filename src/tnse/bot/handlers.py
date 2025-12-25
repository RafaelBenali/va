"""
TNSE Telegram Bot Command Handlers

Provides command handlers for the Telegram bot interface.
Includes /start, /help, /settings commands and access control.
"""

from functools import wraps
from typing import Any, Callable, Coroutine

from telegram import Update
from telegram.ext import ContextTypes

from src.tnse.bot.config import BotConfig
from src.tnse.core.logging import get_logger

logger = get_logger(__name__)


# Type alias for handler functions
HandlerFunc = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]


async def check_user_access(user_id: int, config: BotConfig) -> bool:
    """
    Check if a user is allowed to access the bot.

    Args:
        user_id: The Telegram user ID to check.
        config: The bot configuration with allowed users list.

    Returns:
        True if user is allowed, False otherwise.
        If allowed_users is empty, all users are allowed.
    """
    if not config.allowed_users:
        return True
    return user_id in config.allowed_users


async def access_denied_handler(update: Update) -> None:
    """
    Send access denied message to unauthorized user.

    Args:
        update: The Telegram update object.
    """
    await update.message.reply_text(
        "Access denied. You are not authorized to use this bot.\n\n"
        "If you believe this is an error, please contact the bot administrator."
    )


def require_access(handler: HandlerFunc) -> HandlerFunc:
    """
    Decorator to require user access for a command handler.

    Checks if the user is in the allowed users list (if configured).
    If access is denied, sends a denial message instead of executing the handler.

    Args:
        handler: The handler function to wrap.

    Returns:
        Wrapped handler function with access control.
    """
    @wraps(handler)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Any:
        user_id = update.effective_user.id

        # Get config from bot_data
        config = context.bot_data.get("config")
        if config is None:
            logger.warning(
                "Bot config not found in context, allowing access by default",
                user_id=user_id
            )
            return await handler(update, context)

        if not await check_user_access(user_id, config):
            logger.warning(
                "Access denied for user",
                user_id=user_id,
                allowed_users=config.allowed_users
            )
            await access_denied_handler(update)
            return None

        return await handler(update, context)

    return wrapper


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /start command.

    Sends a welcome message to the user with information about the bot
    and how to get started.

    Args:
        update: The Telegram update object.
        context: The callback context.
    """
    user = update.effective_user
    first_name = user.first_name if user else "User"

    welcome_message = f"""Welcome to TNSE - Telegram News Search Engine, {first_name}!

This bot helps you search and discover news from public Telegram channels.

To get started:
- Use /help to see all available commands
- Use /settings to view and configure bot settings

Happy searching!"""

    await update.message.reply_text(welcome_message)
    logger.info(
        "User started bot",
        user_id=user.id if user else None,
        username=user.username if user else None
    )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /help command.

    Displays a list of all available commands and their descriptions.

    Args:
        update: The Telegram update object.
        context: The callback context.
    """
    help_message = """TNSE Bot - Available Commands

Basic Commands:
/start - Start the bot and see welcome message
/help - Show this help message
/settings - View and configure bot settings

Channel Management:
/addchannel @username - Add a channel to monitor
/removechannel @username - Remove a channel from monitoring
/channels - List all monitored channels
/channelinfo @username - Show channel details and health status

Search Commands (coming soon):
/search <query> - Search for news by keyword
/export - Export search results to CSV

Topic Management (coming soon):
/savetopic <name> - Save current search configuration
/topics - List your saved topics
/topic <name> - Run a saved topic search
/templates - Show pre-built topic templates

For more information, visit the documentation or contact the bot administrator."""

    await update.message.reply_text(help_message)
    logger.info(
        "User requested help",
        user_id=update.effective_user.id if update.effective_user else None
    )


async def settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /settings command.

    Displays current bot settings including access mode and configuration.

    Args:
        update: The Telegram update object.
        context: The callback context.
    """
    config = context.bot_data.get("config")

    if config is None:
        settings_message = """Bot Settings

Configuration is not available.
Please contact the administrator if you need to view settings."""
    else:
        # Determine access mode
        if config.allowed_users:
            access_mode = f"Restricted (whitelist of {len(config.allowed_users)} users)"
        else:
            access_mode = "Open (all users allowed)"

        # Determine connection mode
        connection_mode = "Polling" if config.polling_mode else "Webhook"

        settings_message = f"""Bot Settings

Access Mode: {access_mode}
Connection Mode: {connection_mode}

Your User ID: {update.effective_user.id if update.effective_user else 'Unknown'}

To modify settings, update the environment configuration and restart the bot."""

    await update.message.reply_text(settings_message)
    logger.info(
        "User viewed settings",
        user_id=update.effective_user.id if update.effective_user else None
    )


async def error_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle errors in the bot.

    Logs the error and optionally notifies the user.

    Args:
        update: The Telegram update object.
        context: The callback context containing the error.
    """
    logger.error(
        "Exception while handling update",
        error=str(context.error),
        update=str(update) if update else None,
        exc_info=context.error
    )

    # Notify user if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An error occurred while processing your request. "
                "Please try again later."
            )
        except Exception as notification_error:
            logger.error(
                "Failed to send error notification to user",
                error=str(notification_error)
            )

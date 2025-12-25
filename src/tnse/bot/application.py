"""
TNSE Telegram Bot Application

Provides the main bot application setup and runner functions.
This is the primary interface for starting and running the bot.
"""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.tnse.bot.advanced_channel_handlers import (
    health_command,
    import_command,
)
from src.tnse.bot.channel_handlers import (
    addchannel_command,
    channels_command,
    channelinfo_command,
    removechannel_command,
)
from src.tnse.bot.config import BotConfig, create_bot_config
from src.tnse.bot.export_handlers import export_command
from src.tnse.bot.handlers import (
    error_handler,
    help_command,
    require_access,
    settings_command,
    start_command,
)
from src.tnse.bot.search_handlers import (
    pagination_callback,
    search_command,
    SEARCH_CALLBACK_PREFIX,
)
from src.tnse.bot.topic_handlers import (
    savetopic_command,
    topics_command,
    topic_command,
    deletetopic_command,
    templates_command,
    use_template_command,
)
from src.tnse.core.logging import configure_logging, get_logger

# Configure logging for the bot
configure_logging()
logger = get_logger(__name__)


def create_bot_application(config: BotConfig) -> Application:
    """
    Create and configure a Telegram bot Application.

    Sets up all command handlers and stores configuration in bot_data
    for access by handlers.

    Args:
        config: The bot configuration.

    Returns:
        Configured Application instance.

    Example:
        >>> config = BotConfig(token="123:abc")
        >>> app = create_bot_application(config)
        >>> app.run_polling()
    """
    logger.info(
        "Creating bot application",
        polling_mode=config.polling_mode,
        allowed_users_count=len(config.allowed_users),
    )

    # Build the application
    builder = Application.builder().token(config.token)
    application = builder.build()

    # Store config in bot_data for handlers to access
    application.bot_data["config"] = config

    # Register command handlers with access control
    # Wrap handlers with require_access for protected commands
    application.add_handler(CommandHandler("start", require_access(start_command)))
    application.add_handler(CommandHandler("help", require_access(help_command)))
    application.add_handler(CommandHandler("settings", require_access(settings_command)))

    # Channel management commands (WS-1.5)
    application.add_handler(CommandHandler("addchannel", require_access(addchannel_command)))
    application.add_handler(CommandHandler("removechannel", require_access(removechannel_command)))
    application.add_handler(CommandHandler("channels", require_access(channels_command)))
    application.add_handler(CommandHandler("channelinfo", require_access(channelinfo_command)))

    # Advanced channel management commands (WS-3.2)
    application.add_handler(CommandHandler("import", require_access(import_command)))
    application.add_handler(CommandHandler("health", require_access(health_command)))

    # Search commands (WS-2.4)
    application.add_handler(CommandHandler("search", require_access(search_command)))

    # Export commands (WS-2.5)
    application.add_handler(CommandHandler("export", require_access(export_command)))

    # Topic management commands (WS-3.1)
    application.add_handler(CommandHandler("savetopic", require_access(savetopic_command)))
    application.add_handler(CommandHandler("topics", require_access(topics_command)))
    application.add_handler(CommandHandler("topic", require_access(topic_command)))
    application.add_handler(CommandHandler("deletetopic", require_access(deletetopic_command)))
    application.add_handler(CommandHandler("templates", require_access(templates_command)))
    application.add_handler(CommandHandler("usetemplate", require_access(use_template_command)))

    # Callback query handlers for pagination
    application.add_handler(
        CallbackQueryHandler(pagination_callback, pattern=f"^{SEARCH_CALLBACK_PREFIX}|^noop$")
    )

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("Bot application created successfully")

    return application


def create_bot_from_env() -> Application:
    """
    Create a bot Application from environment variables.

    Reads configuration from environment and creates a fully configured
    bot application.

    Returns:
        Configured Application instance.

    Raises:
        BotTokenMissingError: If TELEGRAM_BOT_TOKEN is not set.

    Example:
        >>> app = create_bot_from_env()
        >>> app.run_polling()
    """
    config = create_bot_config()
    return create_bot_application(config)


def run_bot_polling(config: BotConfig) -> None:
    """
    Run the bot using long polling mode.

    This is the simpler mode suitable for development and most deployments.
    The bot continuously polls Telegram servers for updates.

    Args:
        config: The bot configuration.
    """
    logger.info("Starting bot in polling mode")
    application = create_bot_application(config)
    application.run_polling(allowed_updates=["message", "callback_query"])


def run_bot_webhook(config: BotConfig) -> None:
    """
    Run the bot using webhook mode.

    This mode is more efficient for production deployments with high traffic.
    Requires a publicly accessible HTTPS endpoint.

    Args:
        config: The bot configuration.

    Raises:
        ValueError: If webhook_url is not configured.
    """
    if not config.webhook_url:
        raise ValueError("webhook_url must be set when using webhook mode")

    logger.info(
        "Starting bot in webhook mode",
        webhook_url=config.webhook_url
    )
    application = create_bot_application(config)

    # Parse webhook URL to get host and port
    from urllib.parse import urlparse
    parsed = urlparse(config.webhook_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=parsed.path or "/webhook",
        webhook_url=config.webhook_url,
    )


async def run_bot(config: BotConfig) -> None:
    """
    Run the bot in the configured mode (polling or webhook).

    This is an async function that can be integrated with other
    async applications.

    Args:
        config: The bot configuration.
    """
    if config.polling_mode:
        run_bot_polling(config)
    else:
        run_bot_webhook(config)

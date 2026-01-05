"""
TNSE Telegram Bot Application

Provides the main bot application setup and runner functions.
This is the primary interface for starting and running the bot.
"""

from collections.abc import Callable
from typing import Any

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
from src.tnse.bot.llm_handlers import (
    mode_command,
    enrich_command,
    stats_llm_command,
)
from src.tnse.bot.search_handlers import (
    pagination_callback,
    search_command,
    SEARCH_CALLBACK_PREFIX,
)
from src.tnse.bot.sync_handlers import (
    sync_command,
    SyncRateLimiter,
)
from src.tnse.bot.topic_handlers import (
    savetopic_command,
    topics_command,
    topic_command,
    deletetopic_command,
    templates_command,
    use_template_command,
)
from src.tnse.bot.menu import setup_bot_menu
from src.tnse.core.logging import configure_logging, get_logger

# Configure logging for the bot
configure_logging()
logger = get_logger(__name__)


async def _post_init(application: Application) -> None:
    """
    Post-initialization callback for the bot application.

    Called after the application is initialized but before it starts
    processing updates. Sets up the bot menu and commands.

    Args:
        application: The initialized Application instance.
    """
    logger.info("Running post-init callback")
    await setup_bot_menu(application.bot)


def create_bot_application(
    config: BotConfig,
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,
    topic_service: Any | None = None,
) -> Application:
    """
    Create and configure a Telegram bot Application.

    Sets up all command handlers and stores configuration and services
    in bot_data for access by handlers.

    Args:
        config: The bot configuration.
        channel_service: Service for channel validation and metadata.
        db_session_factory: Factory function that creates database sessions.
        search_service: Service for searching posts.
        topic_service: Service for managing saved topics.

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

    # Build the application with post_init callback for menu setup
    builder = Application.builder().token(config.token).post_init(_post_init)
    application = builder.build()

    # Store config and services in bot_data for handlers to access
    application.bot_data["config"] = config
    if channel_service is not None:
        application.bot_data["channel_service"] = channel_service
    if db_session_factory is not None:
        application.bot_data["db_session_factory"] = db_session_factory
    if search_service is not None:
        application.bot_data["search_service"] = search_service
    if topic_service is not None:
        application.bot_data["topic_service"] = topic_service

    # Create and store sync rate limiter (5 minute cooldown)
    application.bot_data["sync_rate_limiter"] = SyncRateLimiter(cooldown_seconds=300)

    # Register command handlers with access control
    # Wrap handlers with require_access for protected commands
    application.add_handler(CommandHandler("start", require_access(start_command)))
    # Help command with /h alias for quick access
    application.add_handler(CommandHandler(["help", "h"], require_access(help_command)))
    application.add_handler(CommandHandler("settings", require_access(settings_command)))

    # Channel management commands (WS-1.5)
    application.add_handler(CommandHandler("addchannel", require_access(addchannel_command)))
    application.add_handler(CommandHandler("removechannel", require_access(removechannel_command)))
    # Channels list with /ch alias for quick access
    application.add_handler(CommandHandler(["channels", "ch"], require_access(channels_command)))
    application.add_handler(CommandHandler("channelinfo", require_access(channelinfo_command)))

    # Advanced channel management commands (WS-3.2)
    application.add_handler(CommandHandler("import", require_access(import_command)))
    application.add_handler(CommandHandler("health", require_access(health_command)))

    # Search commands (WS-2.4) with /s alias for quick access
    application.add_handler(CommandHandler(["search", "s"], require_access(search_command)))

    # Export commands (WS-2.5) with /e alias for quick access
    application.add_handler(CommandHandler(["export", "e"], require_access(export_command)))

    # Topic management commands (WS-3.1) with /t alias for quick access
    application.add_handler(CommandHandler("savetopic", require_access(savetopic_command)))
    application.add_handler(CommandHandler(["topics", "t"], require_access(topics_command)))
    application.add_handler(CommandHandler("topic", require_access(topic_command)))
    application.add_handler(CommandHandler("deletetopic", require_access(deletetopic_command)))
    application.add_handler(CommandHandler("templates", require_access(templates_command)))
    application.add_handler(CommandHandler("usetemplate", require_access(use_template_command)))

    # Sync command (WS-9.2) - triggers manual content collection
    application.add_handler(CommandHandler("sync", require_access(sync_command)))

    # LLM commands (WS-5.6) - mode switching and enrichment
    # /mode with /m alias for quick access
    application.add_handler(CommandHandler(["mode", "m"], require_access(mode_command)))
    application.add_handler(CommandHandler("enrich", require_access(enrich_command)))
    application.add_handler(CommandHandler("llmstats", require_access(stats_llm_command)))

    # Callback query handlers for pagination
    application.add_handler(
        CallbackQueryHandler(pagination_callback, pattern=f"^{SEARCH_CALLBACK_PREFIX}|^noop$")
    )

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("Bot application created successfully")

    return application


def create_bot_from_env(
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,
    topic_service: Any | None = None,
) -> Application:
    """
    Create a bot Application from environment variables.

    Reads configuration from environment and creates a fully configured
    bot application. Optional service dependencies can be provided for
    dependency injection.

    Args:
        channel_service: Optional channel service for validation.
        db_session_factory: Optional database session factory.
        search_service: Optional search service.
        topic_service: Optional topic service.

    Returns:
        Configured Application instance.

    Raises:
        BotTokenMissingError: If TELEGRAM_BOT_TOKEN is not set.

    Example:
        >>> app = create_bot_from_env()
        >>> app.run_polling()
    """
    config = create_bot_config()
    return create_bot_application(
        config,
        channel_service=channel_service,
        db_session_factory=db_session_factory,
        search_service=search_service,
        topic_service=topic_service,
    )


def run_bot_polling(
    config: BotConfig,
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,
    topic_service: Any | None = None,
) -> None:
    """
    Run the bot using long polling mode.

    This is the simpler mode suitable for development and most deployments.
    The bot continuously polls Telegram servers for updates.

    Args:
        config: The bot configuration.
        channel_service: Optional channel service for validation.
        db_session_factory: Optional database session factory.
        search_service: Optional search service.
        topic_service: Optional topic service.
    """
    logger.info("Starting bot in polling mode")
    application = create_bot_application(
        config,
        channel_service=channel_service,
        db_session_factory=db_session_factory,
        search_service=search_service,
        topic_service=topic_service,
    )
    application.run_polling(allowed_updates=["message", "callback_query"])


def run_bot_webhook(
    config: BotConfig,
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,
    topic_service: Any | None = None,
) -> None:
    """
    Run the bot using webhook mode.

    This mode is more efficient for production deployments with high traffic.
    Requires a publicly accessible HTTPS endpoint.

    Args:
        config: The bot configuration.
        channel_service: Optional channel service for validation.
        db_session_factory: Optional database session factory.
        search_service: Optional search service.
        topic_service: Optional topic service.

    Raises:
        ValueError: If webhook_url is not configured.
    """
    if not config.webhook_url:
        raise ValueError("webhook_url must be set when using webhook mode")

    logger.info(
        "Starting bot in webhook mode",
        webhook_url=config.webhook_url
    )
    application = create_bot_application(
        config,
        channel_service=channel_service,
        db_session_factory=db_session_factory,
        search_service=search_service,
        topic_service=topic_service,
    )

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


async def run_bot(
    config: BotConfig,
    channel_service: Any | None = None,
    db_session_factory: Callable[[], Any] | None = None,
    search_service: Any | None = None,
    topic_service: Any | None = None,
) -> None:
    """
    Run the bot in the configured mode (polling or webhook).

    This is an async function that can be integrated with other
    async applications.

    Args:
        config: The bot configuration.
        channel_service: Optional channel service for validation.
        db_session_factory: Optional database session factory.
        search_service: Optional search service.
        topic_service: Optional topic service.
    """
    if config.polling_mode:
        run_bot_polling(
            config,
            channel_service=channel_service,
            db_session_factory=db_session_factory,
            search_service=search_service,
            topic_service=topic_service,
        )
    else:
        run_bot_webhook(
            config,
            channel_service=channel_service,
            db_session_factory=db_session_factory,
            search_service=search_service,
            topic_service=topic_service,
        )

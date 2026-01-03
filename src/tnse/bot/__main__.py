"""
TNSE Telegram Bot Entry Point

Run the bot directly with: python -m src.tnse.bot

This module provides the main entry point for running the Telegram bot.
"""

import sys

from dotenv import load_dotenv

# Load .env file before any settings are read
load_dotenv()

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.tnse.bot.application import create_bot_from_env
from src.tnse.bot.config import BotTokenMissingError
from src.tnse.core.config import get_settings
from src.tnse.core.logging import configure_logging, get_logger
from src.tnse.telegram.channel_service import ChannelService
from src.tnse.telegram.client import TelegramClientConfig, TelethonClient

# Configure logging
configure_logging()
logger = get_logger(__name__)


def create_db_session_factory():
    """Create an async database session factory."""
    settings = get_settings()
    engine = create_async_engine(settings.database.async_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


def validate_telegram_credentials() -> bool:
    """
    Check if Telegram API credentials are properly configured.

    Returns:
        True if both TELEGRAM_API_ID and TELEGRAM_API_HASH are set, False otherwise.
    """
    settings = get_settings()
    return bool(settings.telegram.api_id and settings.telegram.api_hash)


def log_service_status(
    channel_service: ChannelService | None = None,
    db_session_factory: object | None = None,
) -> None:
    """
    Log the status of all services at startup.

    Provides clear information about which services are available and which
    features will be disabled due to missing configuration.

    Args:
        channel_service: The channel service instance, or None if unavailable.
        db_session_factory: The database session factory, or None if unavailable.
    """
    # Log channel service status
    if channel_service is not None:
        logger.info(
            "Channel service initialized",
            status="available",
            feature="/addchannel, /channelinfo enabled"
        )
    else:
        logger.warning(
            "Channel service not available - /addchannel command will not work",
            hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH to enable channel management",
            disabled_commands=["/addchannel", "/import"]
        )

    # Log database status
    if db_session_factory is not None:
        logger.info(
            "Database connection initialized",
            status="available"
        )
    else:
        logger.warning(
            "Database not available - channel and search features will not work",
            hint="Check database configuration (POSTGRES_* environment variables)"
        )


def create_channel_service() -> ChannelService | None:
    """Create the channel service with Telegram client.

    Returns None if Telegram API credentials are not configured.
    """
    settings = get_settings()

    # Check if Telegram API credentials are configured
    if not settings.telegram.api_id or not settings.telegram.api_hash:
        logger.warning(
            "Telegram API credentials not configured",
            hint="Set TELEGRAM_API_ID and TELEGRAM_API_HASH for channel validation"
        )
        return None

    config = TelegramClientConfig.from_settings(settings)
    client = TelethonClient(config)
    return ChannelService(client)


def main() -> int:
    """
    Main entry point for the bot.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        logger.info("Starting TNSE Telegram Bot")

        # Create service dependencies
        logger.info("Initializing database connection...")
        db_session_factory = create_db_session_factory()

        logger.info("Initializing channel service...")
        channel_service = create_channel_service()

        # Log service availability summary
        log_service_status(
            channel_service=channel_service,
            db_session_factory=db_session_factory,
        )

        # Create application from environment with dependencies
        application = create_bot_from_env(
            channel_service=channel_service,
            db_session_factory=db_session_factory,
        )

        # Run the bot with polling (default mode)
        logger.info("Bot starting in polling mode...")
        application.run_polling(allowed_updates=["message", "callback_query"])

        logger.info("Bot stopped")
        return 0

    except BotTokenMissingError as error:
        logger.error(
            "Bot token not configured",
            error=str(error),
            hint="Set TELEGRAM_BOT_TOKEN environment variable",
        )
        print(
            "ERROR: TELEGRAM_BOT_TOKEN is not set.\n"
            "Please set the TELEGRAM_BOT_TOKEN environment variable.\n"
            "See docs/BOTFATHER_SETUP.md for instructions on getting a bot token.",
            file=sys.stderr,
        )
        return 1

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0

    except Exception as error:
        logger.exception("Bot crashed with unexpected error", error=str(error))
        print(f"ERROR: Bot crashed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
TNSE Telegram Bot Entry Point

Run the bot directly with: python -m src.tnse.bot

This module provides the main entry point for running the Telegram bot.
"""

import sys

from dotenv import load_dotenv

# Load .env file before any settings are read
load_dotenv()

from src.tnse.bot.application import create_bot_from_env
from src.tnse.bot.config import BotTokenMissingError
from src.tnse.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


def main() -> int:
    """
    Main entry point for the bot.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        logger.info("Starting TNSE Telegram Bot")

        # Create application from environment
        application = create_bot_from_env()

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

"""
TNSE Telegram Bot Module

This module provides the Telegram bot interface for the TNSE application.
The bot is the PRIMARY user interface - there is no web frontend.
"""

from src.tnse.bot.config import BotConfig, BotTokenMissingError, create_bot_config
from src.tnse.bot.application import (
    create_bot_application,
    create_bot_from_env,
    run_bot,
    run_bot_polling,
    run_bot_webhook,
)

__all__ = [
    "BotConfig",
    "BotTokenMissingError",
    "create_bot_config",
    "create_bot_application",
    "create_bot_from_env",
    "run_bot",
    "run_bot_polling",
    "run_bot_webhook",
]

"""
TNSE Telegram Bot Module

This module provides the Telegram bot interface for the TNSE application.
The bot is the PRIMARY user interface - there is no web frontend.
"""

from src.tnse.bot.config import BotConfig, BotTokenMissingError, create_bot_config

__all__ = ["BotConfig", "BotTokenMissingError", "create_bot_config"]

"""
TNSE Telegram Bot Menu Setup (WS-9.1)

Provides functionality for setting up the bot menu button and commands.
Commands are organized by category for better discoverability.

Telegram Bot API References:
- setMyCommands: https://core.telegram.org/bots/api#setmycommands
- MenuButton: https://core.telegram.org/bots/api#menubutton
"""

from telegram import Bot, BotCommand, MenuButtonCommands
from telegram.error import TelegramError

from src.tnse.core.logging import get_logger

logger = get_logger(__name__)


# Command categories with command name and description
COMMAND_CATEGORIES: dict[str, list[dict[str, str]]] = {
    "Basic": [
        {"command": "start", "description": "Start the bot and see welcome message"},
        {"command": "help", "description": "Show help message with all commands"},
        {"command": "settings", "description": "View and configure bot settings"},
    ],
    "Channel": [
        {"command": "addchannel", "description": "Add a channel to monitor"},
        {"command": "removechannel", "description": "Remove a channel from monitoring"},
        {"command": "channels", "description": "List all monitored channels"},
        {"command": "channelinfo", "description": "Show channel details and health"},
    ],
    "Search": [
        {"command": "search", "description": "Search for news by keyword"},
    ],
    "Topic": [
        {"command": "savetopic", "description": "Save current search configuration"},
        {"command": "topics", "description": "List your saved topics"},
        {"command": "topic", "description": "Run a saved topic search"},
        {"command": "deletetopic", "description": "Delete a saved topic"},
        {"command": "templates", "description": "Show pre-built topic templates"},
        {"command": "usetemplate", "description": "Run a pre-built template search"},
    ],
    "Export": [
        {"command": "export", "description": "Export search results to file"},
    ],
    "Advanced": [
        {"command": "import", "description": "Bulk import channels from file"},
        {"command": "health", "description": "Show health status of all channels"},
        {"command": "sync", "description": "Trigger content sync for channels"},
    ],
}


def get_command_categories() -> dict[str, list[dict[str, str]]]:
    """
    Get command definitions organized by category.

    Returns a dictionary where keys are category names and values are lists
    of command information dictionaries with 'command' and 'description' keys.

    Returns:
        Dictionary mapping category names to lists of command info.

    Example:
        >>> categories = get_command_categories()
        >>> categories["Basic"]
        [{"command": "start", "description": "Start the bot..."}]
    """
    return COMMAND_CATEGORIES


def get_bot_commands() -> list[BotCommand]:
    """
    Get all bot commands as a flat list of BotCommand objects.

    Commands are collected from all categories and returned as a single list
    suitable for passing to Bot.set_my_commands().

    Returns:
        List of BotCommand objects representing all available commands.

    Example:
        >>> commands = get_bot_commands()
        >>> [cmd.command for cmd in commands]
        ['start', 'help', 'settings', 'addchannel', ...]
    """
    commands: list[BotCommand] = []

    for category_commands in COMMAND_CATEGORIES.values():
        for command_info in category_commands:
            commands.append(
                BotCommand(
                    command=command_info["command"],
                    description=command_info["description"],
                )
            )

    return commands


async def setup_bot_commands(bot: Bot) -> bool:
    """
    Set up bot commands via the Telegram Bot API.

    Registers all bot commands with Telegram so they appear in the
    command menu when users type / in the chat.

    Args:
        bot: The Telegram Bot instance.

    Returns:
        True if commands were set successfully, False otherwise.

    Example:
        >>> success = await setup_bot_commands(application.bot)
        >>> if not success:
        ...     logger.warning("Failed to set up bot commands")
    """
    try:
        commands = get_bot_commands()
        await bot.set_my_commands(commands=commands)
        logger.info(
            "Bot commands registered successfully",
            command_count=len(commands),
        )
        return True
    except TelegramError as error:
        logger.error(
            "Failed to set bot commands",
            error=str(error),
        )
        return False


async def setup_menu_button(bot: Bot) -> bool:
    """
    Set up the menu button to show bot commands.

    Configures the bot's menu button to display the command list
    when clicked, making commands more discoverable for users.

    Args:
        bot: The Telegram Bot instance.

    Returns:
        True if menu button was set successfully, False otherwise.

    Example:
        >>> success = await setup_menu_button(application.bot)
    """
    try:
        menu_button = MenuButtonCommands()
        await bot.set_chat_menu_button(menu_button=menu_button)
        logger.info("Menu button configured successfully")
        return True
    except TelegramError as error:
        logger.error(
            "Failed to set menu button",
            error=str(error),
        )
        return False


async def setup_bot_menu(bot: Bot) -> bool:
    """
    Set up both bot commands and menu button.

    This is the main entry point for menu setup. It configures both
    the command list and the menu button to ensure full discoverability.

    Args:
        bot: The Telegram Bot instance.

    Returns:
        True if both operations succeeded, False if either failed.

    Example:
        >>> async def post_init(application):
        ...     await setup_bot_menu(application.bot)
    """
    logger.info("Setting up bot menu and commands...")

    commands_success = await setup_bot_commands(bot)
    if not commands_success:
        logger.warning("Bot menu setup incomplete - commands registration failed")
        return False

    menu_success = await setup_menu_button(bot)
    if not menu_success:
        logger.warning("Bot menu setup incomplete - menu button configuration failed")
        return False

    logger.info("Bot menu setup completed successfully")
    return True

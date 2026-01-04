"""
Tests for TNSE Telegram bot menu button setup (WS-9.1).

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover:
- Command definitions grouped by category
- Bot commands registration via Telegram API
- Menu button configuration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import BotCommand


class TestCommandDefinitions:
    """Tests for command definitions and grouping."""

    def test_get_bot_commands_function_exists(self):
        """Test that get_bot_commands function exists."""
        from src.tnse.bot.menu import get_bot_commands

        assert callable(get_bot_commands)

    def test_get_bot_commands_returns_list_of_bot_command(self):
        """Test that get_bot_commands returns a list of BotCommand objects."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()

        assert isinstance(commands, list)
        assert len(commands) > 0
        assert all(isinstance(command, BotCommand) for command in commands)

    def test_get_bot_commands_includes_basic_commands(self):
        """Test that basic commands (start, help, settings) are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "start" in command_names
        assert "help" in command_names
        assert "settings" in command_names

    def test_get_bot_commands_includes_channel_commands(self):
        """Test that channel management commands are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "addchannel" in command_names
        assert "removechannel" in command_names
        assert "channels" in command_names
        assert "channelinfo" in command_names

    def test_get_bot_commands_includes_search_commands(self):
        """Test that search commands are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "search" in command_names

    def test_get_bot_commands_includes_topic_commands(self):
        """Test that topic management commands are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "savetopic" in command_names
        assert "topics" in command_names
        assert "topic" in command_names
        assert "deletetopic" in command_names
        assert "templates" in command_names
        assert "usetemplate" in command_names

    def test_get_bot_commands_includes_export_commands(self):
        """Test that export commands are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "export" in command_names

    def test_get_bot_commands_includes_advanced_commands(self):
        """Test that advanced commands are included."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()
        command_names = [cmd.command for cmd in commands]

        assert "import" in command_names
        assert "health" in command_names

    def test_get_bot_commands_descriptions_not_empty(self):
        """Test that all commands have non-empty descriptions."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()

        for command in commands:
            assert command.description
            assert len(command.description) >= 3
            assert len(command.description) <= 256  # Telegram limit

    def test_get_bot_commands_names_lowercase(self):
        """Test that all command names are lowercase and valid."""
        from src.tnse.bot.menu import get_bot_commands

        commands = get_bot_commands()

        for command in commands:
            assert command.command == command.command.lower()
            # Telegram allows lowercase letters, digits, underscores
            assert all(c.islower() or c.isdigit() or c == "_" for c in command.command)


class TestCommandCategories:
    """Tests for command categorization."""

    def test_get_command_categories_function_exists(self):
        """Test that get_command_categories function exists."""
        from src.tnse.bot.menu import get_command_categories

        assert callable(get_command_categories)

    def test_get_command_categories_returns_dict(self):
        """Test that get_command_categories returns a dictionary."""
        from src.tnse.bot.menu import get_command_categories

        categories = get_command_categories()

        assert isinstance(categories, dict)

    def test_get_command_categories_has_expected_categories(self):
        """Test that expected category names are present."""
        from src.tnse.bot.menu import get_command_categories

        categories = get_command_categories()
        category_names = list(categories.keys())

        assert "Basic" in category_names
        assert "Channel" in category_names
        assert "Search" in category_names
        assert "Topic" in category_names
        assert "Export" in category_names
        assert "Advanced" in category_names

    def test_get_command_categories_values_are_lists(self):
        """Test that category values are lists of command info."""
        from src.tnse.bot.menu import get_command_categories

        categories = get_command_categories()

        for category_name, commands in categories.items():
            assert isinstance(commands, list), f"Category {category_name} should be a list"
            assert len(commands) > 0, f"Category {category_name} should not be empty"

    def test_basic_category_contains_start_help_settings(self):
        """Test that Basic category contains core commands."""
        from src.tnse.bot.menu import get_command_categories

        categories = get_command_categories()
        basic_commands = [cmd["command"] for cmd in categories["Basic"]]

        assert "start" in basic_commands
        assert "help" in basic_commands
        assert "settings" in basic_commands

    def test_channel_category_contains_channel_commands(self):
        """Test that Channel category contains channel management commands."""
        from src.tnse.bot.menu import get_command_categories

        categories = get_command_categories()
        channel_commands = [cmd["command"] for cmd in categories["Channel"]]

        assert "addchannel" in channel_commands
        assert "removechannel" in channel_commands
        assert "channels" in channel_commands
        assert "channelinfo" in channel_commands


class TestBotMenuSetup:
    """Tests for setting up bot menu via Telegram API."""

    def test_setup_bot_commands_function_exists(self):
        """Test that setup_bot_commands function exists."""
        from src.tnse.bot.menu import setup_bot_commands

        assert callable(setup_bot_commands)

    @pytest.mark.asyncio
    async def test_setup_bot_commands_calls_set_my_commands(self):
        """Test that setup_bot_commands calls bot.set_my_commands."""
        from src.tnse.bot.menu import setup_bot_commands

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(return_value=True)

        result = await setup_bot_commands(mock_bot)

        mock_bot.set_my_commands.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_setup_bot_commands_passes_command_list(self):
        """Test that setup_bot_commands passes the command list to set_my_commands."""
        from src.tnse.bot.menu import setup_bot_commands, get_bot_commands

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(return_value=True)

        await setup_bot_commands(mock_bot)

        # Check that commands were passed
        call_args = mock_bot.set_my_commands.call_args
        commands_arg = call_args.kwargs.get("commands") or call_args.args[0]

        expected_commands = get_bot_commands()
        assert len(commands_arg) == len(expected_commands)

    @pytest.mark.asyncio
    async def test_setup_bot_commands_handles_api_error(self):
        """Test that setup_bot_commands handles API errors gracefully."""
        from src.tnse.bot.menu import setup_bot_commands
        from telegram.error import TelegramError

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(side_effect=TelegramError("API Error"))

        result = await setup_bot_commands(mock_bot)

        assert result is False


class TestMenuButtonSetup:
    """Tests for setting up menu button via Telegram API."""

    def test_setup_menu_button_function_exists(self):
        """Test that setup_menu_button function exists."""
        from src.tnse.bot.menu import setup_menu_button

        assert callable(setup_menu_button)

    @pytest.mark.asyncio
    async def test_setup_menu_button_calls_set_chat_menu_button(self):
        """Test that setup_menu_button calls bot.set_chat_menu_button."""
        from src.tnse.bot.menu import setup_menu_button

        mock_bot = AsyncMock()
        mock_bot.set_chat_menu_button = AsyncMock(return_value=True)

        result = await setup_menu_button(mock_bot)

        mock_bot.set_chat_menu_button.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_setup_menu_button_uses_menu_button_commands(self):
        """Test that setup_menu_button uses MenuButtonCommands type."""
        from src.tnse.bot.menu import setup_menu_button
        from telegram import MenuButtonCommands

        mock_bot = AsyncMock()
        mock_bot.set_chat_menu_button = AsyncMock(return_value=True)

        await setup_menu_button(mock_bot)

        call_args = mock_bot.set_chat_menu_button.call_args
        menu_button_arg = call_args.kwargs.get("menu_button") or (call_args.args[0] if call_args.args else None)

        assert isinstance(menu_button_arg, MenuButtonCommands)

    @pytest.mark.asyncio
    async def test_setup_menu_button_handles_api_error(self):
        """Test that setup_menu_button handles API errors gracefully."""
        from src.tnse.bot.menu import setup_menu_button
        from telegram.error import TelegramError

        mock_bot = AsyncMock()
        mock_bot.set_chat_menu_button = AsyncMock(side_effect=TelegramError("API Error"))

        result = await setup_menu_button(mock_bot)

        assert result is False


class TestBotMenuIntegration:
    """Tests for complete menu setup integration."""

    def test_setup_bot_menu_function_exists(self):
        """Test that setup_bot_menu function exists."""
        from src.tnse.bot.menu import setup_bot_menu

        assert callable(setup_bot_menu)

    @pytest.mark.asyncio
    async def test_setup_bot_menu_sets_commands_and_menu_button(self):
        """Test that setup_bot_menu sets both commands and menu button."""
        from src.tnse.bot.menu import setup_bot_menu

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(return_value=True)
        mock_bot.set_chat_menu_button = AsyncMock(return_value=True)

        result = await setup_bot_menu(mock_bot)

        mock_bot.set_my_commands.assert_called_once()
        mock_bot.set_chat_menu_button.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_setup_bot_menu_returns_false_if_commands_fail(self):
        """Test that setup_bot_menu returns False if setting commands fails."""
        from src.tnse.bot.menu import setup_bot_menu
        from telegram.error import TelegramError

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(side_effect=TelegramError("API Error"))
        mock_bot.set_chat_menu_button = AsyncMock(return_value=True)

        result = await setup_bot_menu(mock_bot)

        assert result is False

    @pytest.mark.asyncio
    async def test_setup_bot_menu_returns_false_if_menu_button_fails(self):
        """Test that setup_bot_menu returns False if setting menu button fails."""
        from src.tnse.bot.menu import setup_bot_menu
        from telegram.error import TelegramError

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(return_value=True)
        mock_bot.set_chat_menu_button = AsyncMock(side_effect=TelegramError("API Error"))

        result = await setup_bot_menu(mock_bot)

        assert result is False


class TestApplicationMenuSetup:
    """Tests for menu setup as part of application lifecycle."""

    @pytest.mark.asyncio
    async def test_post_init_callback_sets_up_menu(self):
        """Test that application post_init callback sets up menu."""
        from telegram.ext import Application
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.config import BotConfig

        config = BotConfig(token="123456789:ABCdefTestToken")

        with patch("src.tnse.bot.menu.setup_bot_menu") as mock_setup:
            mock_setup.return_value = True
            app = create_bot_application(config)

            # The post_init should be registered to set up menu
            # We verify by checking if post_init is set
            assert app.post_init is not None

    @pytest.mark.asyncio
    async def test_menu_setup_logged_on_startup(self):
        """Test that menu setup is logged during bot startup."""
        from src.tnse.bot.menu import setup_bot_menu

        mock_bot = AsyncMock()
        mock_bot.set_my_commands = AsyncMock(return_value=True)
        mock_bot.set_chat_menu_button = AsyncMock(return_value=True)

        # Patch the logger object directly on the menu module
        with patch("src.tnse.bot.menu.logger") as mock_logger:
            await setup_bot_menu(mock_bot)

            # Verify logging was called
            assert mock_logger.info.called or mock_logger.debug.called

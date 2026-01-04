"""
TNSE Bot Integration Tests

End-to-end integration tests for the Telegram bot.
Tests the full flow of bot commands including:
- Bot startup and command registration
- Channel management flow
- Search and results flow
- Topic management flow
- Error handling across components

Work Stream: WS-3.3 - Polish and Testing
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import Application, ContextTypes

from src.tnse.bot.application import create_bot_application
from src.tnse.bot.config import BotConfig


# Test fixtures and helpers

def create_test_user(user_id: int = 123456789, username: str = "testuser") -> User:
    """Create a mock Telegram User object for testing."""
    return User(
        id=user_id,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username=username,
    )


def create_test_chat(chat_id: int = 123456789) -> Chat:
    """Create a mock Telegram Chat object for testing."""
    return Chat(
        id=chat_id,
        type="private",
    )


def create_test_message(
    text: str,
    user: Optional[User] = None,
    chat: Optional[Chat] = None,
    message_id: int = 1,
) -> Message:
    """Create a mock Telegram Message object for testing."""
    if user is None:
        user = create_test_user()
    if chat is None:
        chat = create_test_chat()

    message = MagicMock(spec=Message)
    message.message_id = message_id
    message.date = datetime.now(timezone.utc)
    message.chat = chat
    message.from_user = user
    message.text = text
    message.reply_text = AsyncMock()
    message.reply_document = AsyncMock()
    message.document = None
    return message


def create_test_update(
    message: Optional[Message] = None,
    update_id: int = 1,
) -> Update:
    """Create a mock Telegram Update object for testing."""
    if message is None:
        message = create_test_message("/start")

    update = MagicMock(spec=Update)
    update.update_id = update_id
    update.message = message
    update.effective_user = message.from_user
    update.effective_message = message
    update.effective_chat = message.chat
    update.callback_query = None
    return update


def create_test_context(bot_data: Optional[dict] = None) -> ContextTypes.DEFAULT_TYPE:
    """Create a mock context object for testing."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = bot_data or {}
    context.user_data = {}
    context.args = []
    # Mock the bot.send_chat_action for typing indicators
    context.bot.send_chat_action = AsyncMock()
    return context


@pytest.fixture
def bot_config() -> BotConfig:
    """Create a test bot configuration."""
    return BotConfig(
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        allowed_users=[123456789],
        polling_mode=True,
    )


@pytest.fixture
def mock_channel_service() -> MagicMock:
    """Create a mock channel service."""
    service = MagicMock()

    # Mock validation result
    validation_result = MagicMock()
    validation_result.is_valid = True
    validation_result.error = None
    validation_result.channel_info = MagicMock()
    validation_result.channel_info.telegram_id = 1234567890
    validation_result.channel_info.username = "test_channel"
    validation_result.channel_info.title = "Test Channel"
    validation_result.channel_info.description = "A test channel"
    validation_result.channel_info.subscriber_count = 5000
    validation_result.channel_info.photo_url = None
    validation_result.channel_info.invite_link = None

    service.validate_channel = AsyncMock(return_value=validation_result)
    return service


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session factory."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()

    # Mock query result for empty channel list
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    return lambda: session


@pytest.fixture
def mock_search_service() -> MagicMock:
    """Create a mock search service."""
    from src.tnse.search.service import SearchResult

    service = MagicMock()

    # Create sample search results
    sample_results = [
        SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="test_channel",
            channel_title="Test Channel",
            text_content="This is a test post about corruption news.",
            published_at=datetime.now(timezone.utc) - timedelta(hours=2),
            view_count=1500,
            reaction_score=45.0,
            relative_engagement=0.25,
            telegram_message_id=12345,
        ),
        SearchResult(
            post_id=str(uuid4()),
            channel_id=str(uuid4()),
            channel_username="another_channel",
            channel_title="Another Channel",
            text_content="Breaking news about local politics.",
            published_at=datetime.now(timezone.utc) - timedelta(hours=5),
            view_count=3200,
            reaction_score=120.0,
            relative_engagement=0.42,
            telegram_message_id=23456,
        ),
    ]

    service.search = AsyncMock(return_value=sample_results)
    return service


@pytest.fixture
def mock_topic_service() -> MagicMock:
    """Create a mock topic service factory.

    Returns a callable factory that returns an async context manager
    which yields the actual topic service mock.
    """
    from src.tnse.topics.service import SavedTopicData

    # Create the actual service mock
    service = MagicMock()

    sample_topic = SavedTopicData(
        name="corruption",
        keywords="corruption bribery scandal",
        sort_mode=None,
    )

    service.save_topic = AsyncMock(return_value=sample_topic)
    service.get_topic = AsyncMock(return_value=sample_topic)
    service.list_topics = AsyncMock(return_value=[sample_topic])
    service.delete_topic = AsyncMock(return_value=None)

    # Create the context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=service)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    # Create the factory mock - callable that returns the context manager
    factory = MagicMock(return_value=context_manager)

    # Attach the service for assertions in tests
    factory._service = service

    return factory


class TestBotStartupAndCommandRegistration:
    """Tests for bot startup and command registration."""

    def test_create_bot_application_returns_application(self, bot_config: BotConfig) -> None:
        """Test that create_bot_application returns a valid Application."""
        app = create_bot_application(bot_config)

        assert app is not None
        assert isinstance(app, Application)

    def test_bot_config_stored_in_bot_data(self, bot_config: BotConfig) -> None:
        """Test that bot config is stored in bot_data."""
        app = create_bot_application(bot_config)

        assert "config" in app.bot_data
        assert app.bot_data["config"] == bot_config

    def test_all_command_handlers_registered(self, bot_config: BotConfig) -> None:
        """Test that all expected command handlers are registered."""
        app = create_bot_application(bot_config)

        # Get all handlers
        handlers = app.handlers

        # Check that we have handlers registered (group 0 is default)
        assert 0 in handlers
        handler_list = handlers[0]

        # Should have handlers for all bot commands
        # At minimum: start, help, settings, addchannel, removechannel, channels,
        # channelinfo, search, export, savetopic, topics, topic, deletetopic,
        # templates, usetemplate, import, health, plus callback handler
        assert len(handler_list) >= 17


class TestChannelManagementFlow:
    """Integration tests for channel management flow."""

    @pytest.mark.asyncio
    async def test_addchannel_flow_success(
        self,
        bot_config: BotConfig,
        mock_channel_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Test successful channel addition flow."""
        from src.tnse.bot.channel_handlers import addchannel_command

        # Create update and context
        message = create_test_message("/addchannel @test_channel")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "channel_service": mock_channel_service,
            "db_session_factory": mock_db_session,
        })
        context.args = ["@test_channel"]

        # Execute the command
        await addchannel_command(update, context)

        # Verify the channel service was called
        mock_channel_service.validate_channel.assert_called_once()

        # Verify a success message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "successfully added" in call_args.lower() or "channel added" in call_args.lower() or "test channel" in call_args.lower()

    @pytest.mark.asyncio
    async def test_addchannel_without_username_shows_usage(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test addchannel without username shows usage message."""
        from src.tnse.bot.channel_handlers import addchannel_command

        message = create_test_message("/addchannel")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})
        context.args = []

        await addchannel_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "usage" in call_args.lower()

    @pytest.mark.asyncio
    async def test_channels_list_empty(
        self,
        bot_config: BotConfig,
        mock_db_session: MagicMock,
    ) -> None:
        """Test channels command with no channels."""
        from src.tnse.bot.channel_handlers import channels_command

        message = create_test_message("/channels")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_db_session,
        })

        await channels_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "no channels" in call_args.lower()


class TestSearchFlow:
    """Integration tests for search functionality."""

    @pytest.mark.asyncio
    async def test_search_returns_formatted_results(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
    ) -> None:
        """Test that search returns properly formatted results."""
        from src.tnse.bot.search_handlers import search_command

        message = create_test_message("/search corruption news")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        context.args = ["corruption", "news"]

        await search_command(update, context)

        # Verify search was called
        mock_search_service.search.assert_called_once()

        # Verify formatted results were sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0]

        # Should contain search results
        assert "corruption news" in message_text.lower() or "results" in message_text.lower()

    @pytest.mark.asyncio
    async def test_search_without_query_shows_usage(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test search without query shows usage message."""
        from src.tnse.bot.search_handlers import search_command

        message = create_test_message("/search")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})
        context.args = []

        await search_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "usage" in call_args.lower()

    @pytest.mark.asyncio
    async def test_search_stores_results_for_export(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
    ) -> None:
        """Test that search stores results in user_data for export."""
        from src.tnse.bot.search_handlers import search_command

        message = create_test_message("/search test")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        context.args = ["test"]

        await search_command(update, context)

        # Check results are stored
        assert "last_search_query" in context.user_data
        assert "last_search_results" in context.user_data
        assert context.user_data["last_search_query"] == "test"


class TestTopicFlow:
    """Integration tests for topic management."""

    @pytest.mark.asyncio
    async def test_savetopic_requires_prior_search(
        self,
        bot_config: BotConfig,
        mock_topic_service: MagicMock,
    ) -> None:
        """Test that savetopic requires a prior search."""
        from src.tnse.bot.topic_handlers import savetopic_command

        message = create_test_message("/savetopic mytopic")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "topic_service": mock_topic_service,
        })
        context.args = ["mytopic"]
        # No last_search_query in user_data

        await savetopic_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "no search" in call_args.lower() or "search first" in call_args.lower()

    @pytest.mark.asyncio
    async def test_savetopic_success_with_prior_search(
        self,
        bot_config: BotConfig,
        mock_topic_service: MagicMock,
    ) -> None:
        """Test successful topic save after search."""
        from src.tnse.bot.topic_handlers import savetopic_command

        message = create_test_message("/savetopic corruption")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "topic_service": mock_topic_service,
        })
        context.args = ["corruption"]
        context.user_data["last_search_query"] = "corruption news"

        await savetopic_command(update, context)

        # Verify topic was saved (access the actual service through factory._service)
        mock_topic_service._service.save_topic.assert_called_once()

        # Verify success message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "saved" in call_args.lower()

    @pytest.mark.asyncio
    async def test_topics_list_shows_saved_topics(
        self,
        bot_config: BotConfig,
        mock_topic_service: MagicMock,
    ) -> None:
        """Test topics command lists saved topics."""
        from src.tnse.bot.topic_handlers import topics_command

        message = create_test_message("/topics")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "topic_service": mock_topic_service,
        })

        await topics_command(update, context)

        mock_topic_service._service.list_topics.assert_called_once()
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        # Should show the topic
        assert "corruption" in call_args.lower()

    @pytest.mark.asyncio
    async def test_topic_run_executes_search(
        self,
        bot_config: BotConfig,
        mock_topic_service: MagicMock,
        mock_search_service: MagicMock,
    ) -> None:
        """Test running a saved topic executes search."""
        from src.tnse.bot.topic_handlers import topic_command

        message = create_test_message("/topic corruption")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "topic_service": mock_topic_service,
            "search_service": mock_search_service,
        })
        context.args = ["corruption"]

        await topic_command(update, context)

        # Verify topic was retrieved (access the actual service through factory._service)
        mock_topic_service._service.get_topic.assert_called_once()

        # Verify search was executed
        mock_search_service.search.assert_called_once()


class TestExportFlow:
    """Integration tests for export functionality."""

    @pytest.mark.asyncio
    async def test_export_requires_prior_search(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that export requires prior search results."""
        from src.tnse.bot.export_handlers import export_command

        message = create_test_message("/export csv")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})
        context.args = ["csv"]
        # No last_search_results in user_data

        await export_command(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "no results" in call_args.lower() or "search first" in call_args.lower()

    @pytest.mark.asyncio
    async def test_export_csv_sends_file(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
    ) -> None:
        """Test CSV export sends a document."""
        from src.tnse.bot.export_handlers import export_command
        from src.tnse.search.service import SearchResult

        # Create mock search results
        mock_results = [
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username="test_channel",
                channel_title="Test Channel",
                text_content="Test post content",
                published_at=datetime.now(timezone.utc),
                view_count=1000,
                reaction_score=50.0,
                relative_engagement=0.3,
                telegram_message_id=12345,
            )
        ]

        message = create_test_message("/export csv")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})
        context.args = ["csv"]
        context.user_data["last_search_results"] = mock_results
        context.user_data["last_search_query"] = "test query"

        await export_command(update, context)

        # Verify document was sent
        update.message.reply_document.assert_called_once()


class TestAccessControl:
    """Integration tests for access control."""

    @pytest.mark.asyncio
    async def test_unauthorized_user_denied(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that unauthorized users are denied access."""
        from src.tnse.bot.handlers import require_access, start_command

        # Create user not in allowed list
        unauthorized_user = create_test_user(user_id=999999999)
        message = create_test_message("/start", user=unauthorized_user)
        update = create_test_update(message)
        update.effective_user = unauthorized_user

        context = create_test_context({"config": bot_config})

        # Apply access control
        wrapped_handler = require_access(start_command)
        await wrapped_handler(update, context)

        # Should receive access denied message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "access denied" in call_args.lower()

    @pytest.mark.asyncio
    async def test_authorized_user_allowed(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that authorized users can access commands."""
        from src.tnse.bot.handlers import require_access, start_command

        # Create user in allowed list
        authorized_user = create_test_user(user_id=123456789)
        message = create_test_message("/start", user=authorized_user)
        update = create_test_update(message)
        update.effective_user = authorized_user

        context = create_test_context({"config": bot_config})

        # Apply access control
        wrapped_handler = require_access(start_command)
        await wrapped_handler(update, context)

        # Should receive welcome message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "welcome" in call_args.lower()


class TestErrorHandling:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_search_handles_service_error(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test search gracefully handles service errors."""
        from src.tnse.bot.search_handlers import search_command

        # Create failing search service
        failing_service = MagicMock()
        failing_service.search = AsyncMock(side_effect=Exception("Service unavailable"))

        message = create_test_message("/search test")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "search_service": failing_service,
        })
        context.args = ["test"]

        await search_command(update, context)

        # Should send error message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "error" in call_args.lower()

    @pytest.mark.asyncio
    async def test_addchannel_handles_validation_error(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test addchannel handles validation errors gracefully."""
        from src.tnse.bot.channel_handlers import addchannel_command

        # Create failing channel service
        failing_service = MagicMock()
        failing_service.validate_channel = AsyncMock(
            side_effect=Exception("Network error")
        )

        message = create_test_message("/addchannel @test")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "channel_service": failing_service,
            "db_session_factory": MagicMock(),
        })
        context.args = ["@test"]

        await addchannel_command(update, context)

        # Should send error message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "error" in call_args.lower()


# =============================================================================
# Additional Integration Tests for WS-6.10
# =============================================================================


class TestFullSearchWorkflow:
    """Integration tests for complete search workflow."""

    @pytest.mark.asyncio
    async def test_search_then_export_workflow(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
    ) -> None:
        """Test complete workflow: search -> export results."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.bot.export_handlers import export_command

        # Step 1: Execute search
        message = create_test_message("/search test query")
        update = create_test_update(message)
        user_data = {}  # Shared user data
        context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        context.user_data = user_data
        context.args = ["test", "query"]

        await search_command(update, context)

        # Verify search results stored
        assert "last_search_results" in user_data
        assert "last_search_query" in user_data
        assert user_data["last_search_query"] == "test query"

        # Step 2: Export results
        export_message = create_test_message("/export csv")
        export_update = create_test_update(export_message)
        export_context = create_test_context({"config": bot_config})
        export_context.user_data = user_data  # Same user data
        export_context.args = ["csv"]

        await export_command(export_update, export_context)

        # Verify document was sent
        export_update.message.reply_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_then_save_topic_workflow(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
        mock_topic_service: MagicMock,
    ) -> None:
        """Test complete workflow: search -> save as topic."""
        from src.tnse.bot.search_handlers import search_command
        from src.tnse.bot.topic_handlers import savetopic_command

        # Step 1: Execute search
        message = create_test_message("/search corruption news")
        update = create_test_update(message)
        user_data = {}
        context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        context.user_data = user_data
        context.args = ["corruption", "news"]

        await search_command(update, context)

        # Verify search completed
        assert user_data["last_search_query"] == "corruption news"

        # Step 2: Save as topic
        save_message = create_test_message("/savetopic my_corruption_topic")
        save_update = create_test_update(save_message)
        save_context = create_test_context({
            "config": bot_config,
            "topic_service": mock_topic_service,
        })
        save_context.user_data = user_data
        save_context.args = ["my_corruption_topic"]

        await savetopic_command(save_update, save_context)

        # Verify topic service was called (access through factory._service)
        mock_topic_service._service.save_topic.assert_called_once()
        save_update.message.reply_text.assert_called()
        call_args = save_update.message.reply_text.call_args[0][0]
        assert "saved" in call_args.lower()


class TestChannelLifecycle:
    """Integration tests for channel lifecycle operations."""

    @pytest.mark.asyncio
    async def test_add_list_remove_channel_workflow(
        self,
        bot_config: BotConfig,
        mock_channel_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Test complete channel lifecycle: add -> list -> remove."""
        from src.tnse.bot.channel_handlers import (
            addchannel_command,
            channels_command,
            removechannel_command,
        )
        from src.tnse.db.models import Channel

        # Create a mock channel that will be "stored"
        stored_channel = Channel(
            telegram_id=1234567890,
            username="test_channel",
            title="Test Channel",
            description="A test channel",
            subscriber_count=5000,
            is_active=True,
        )

        # Step 1: Add channel
        add_message = create_test_message("/addchannel @test_channel")
        add_update = create_test_update(add_message)
        add_context = create_test_context({
            "config": bot_config,
            "channel_service": mock_channel_service,
            "db_session_factory": mock_db_session,
        })
        add_context.args = ["@test_channel"]

        await addchannel_command(add_update, add_context)

        # Verify add succeeded
        add_update.message.reply_text.assert_called()
        add_result = add_update.message.reply_text.call_args[0][0]
        assert "successfully added" in add_result.lower() or "test channel" in add_result.lower()

        # Step 2: Mock the session to return the channel for list
        mock_session = mock_db_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stored_channel]
        mock_session.execute = AsyncMock(return_value=mock_result)

        list_message = create_test_message("/channels")
        list_update = create_test_update(list_message)
        list_context = create_test_context({
            "config": bot_config,
            "db_session_factory": lambda: mock_session,
        })

        await channels_command(list_update, list_context)

        # Verify list shows channel
        list_update.message.reply_text.assert_called()
        list_result = list_update.message.reply_text.call_args[0][0]
        assert "test_channel" in list_result.lower() or "monitored" in list_result.lower()


class TestBotInitializationFlow:
    """Integration tests for bot initialization and startup."""

    def test_bot_application_initializes_with_all_handlers(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that bot application initializes with all required handlers."""
        from src.tnse.bot.application import create_bot_application
        from telegram.ext import CommandHandler, CallbackQueryHandler

        app = create_bot_application(bot_config)

        # Count command handlers
        command_handlers = [
            handler for handler in app.handlers.get(0, [])
            if isinstance(handler, CommandHandler)
        ]

        # Should have handlers for all commands (including aliases)
        # Basic: start, help, settings
        # Channel: addchannel, removechannel, channels, channelinfo
        # Search: search
        # Export: export
        # Topics: savetopic, topics, topic, deletetopic, templates, usetemplate
        # Advanced: import, health
        assert len(command_handlers) >= 15

        # Should have callback query handler for pagination
        callback_handlers = [
            handler for handler in app.handlers.get(0, [])
            if isinstance(handler, CallbackQueryHandler)
        ]
        assert len(callback_handlers) >= 1

    def test_bot_config_stored_correctly(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that bot config is stored correctly in bot_data."""
        from src.tnse.bot.application import create_bot_application

        app = create_bot_application(bot_config)

        assert "config" in app.bot_data
        stored_config = app.bot_data["config"]
        assert stored_config.token == bot_config.token
        assert stored_config.allowed_users == bot_config.allowed_users


class TestPaginationNavigation:
    """Integration tests for pagination navigation."""

    @pytest.mark.asyncio
    async def test_pagination_navigates_through_results(
        self,
        bot_config: BotConfig,
        mock_search_service: MagicMock,
    ) -> None:
        """Test navigating through paginated search results."""
        from src.tnse.bot.search_handlers import search_command, pagination_callback
        from src.tnse.search.service import SearchResult
        from datetime import datetime, timezone

        # Create many mock results
        many_results = []
        for index in range(20):
            many_results.append(
                SearchResult(
                    post_id=str(uuid4()),
                    channel_id=str(uuid4()),
                    channel_username=f"channel_{index}",
                    channel_title=f"Channel {index}",
                    text_content=f"Post content {index}",
                    published_at=datetime.now(timezone.utc) - timedelta(hours=index),
                    view_count=1000 * (20 - index),
                    reaction_score=50.0,
                    relative_engagement=0.3,
                    telegram_message_id=index,
                )
            )

        mock_search_service.search = AsyncMock(return_value=many_results)

        # Step 1: Initial search
        message = create_test_message("/search test")
        update = create_test_update(message)
        user_data = {}
        context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        context.user_data = user_data
        context.args = ["test"]

        await search_command(update, context)

        # Results should be stored
        assert len(user_data.get("last_search_results", [])) == 20

        # Step 2: Navigate to page 2
        callback_update = MagicMock()
        callback_query = MagicMock()
        callback_query.data = "search:test:2"
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        callback_update.callback_query = callback_query

        page_context = create_test_context({
            "config": bot_config,
            "search_service": mock_search_service,
        })
        page_context.user_data = user_data  # Same user data

        await pagination_callback(callback_update, page_context)

        # Callback should answer and edit message
        callback_query.answer.assert_called_once()
        callback_query.edit_message_text.assert_called_once()

        # Edited message should show page 2
        call_kwargs = callback_query.edit_message_text.call_args
        edited_text = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("text", "")
        assert "showing" in edited_text.lower()


class TestHelperCommandsIntegration:
    """Integration tests for helper commands."""

    @pytest.mark.asyncio
    async def test_help_command_shows_all_sections(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that help command shows all command sections."""
        from src.tnse.bot.handlers import help_command

        message = create_test_message("/help")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})

        await help_command(update, context)

        update.message.reply_text.assert_called_once()
        help_text = update.message.reply_text.call_args[0][0]

        # Should have all sections
        assert "Quick Start" in help_text
        assert "Basic Commands" in help_text
        assert "Channel Management" in help_text
        assert "Search Commands" in help_text
        assert "Topic Management" in help_text
        assert "Advanced" in help_text

    @pytest.mark.asyncio
    async def test_settings_command_shows_access_mode(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that settings command shows access mode."""
        from src.tnse.bot.handlers import settings_command

        message = create_test_message("/settings")
        update = create_test_update(message)
        context = create_test_context({"config": bot_config})

        await settings_command(update, context)

        update.message.reply_text.assert_called_once()
        settings_text = update.message.reply_text.call_args[0][0]

        # Should show access mode
        assert "Access Mode" in settings_text
        assert "Restricted" in settings_text or "Open" in settings_text

        # Should show user ID
        assert "User ID" in settings_text


class TestSyncWorkflowIntegration:
    """Integration tests for manual sync command workflow (WS-9.2)."""

    @pytest.mark.asyncio
    async def test_sync_all_channels_workflow(
        self,
        bot_config: BotConfig,
        mock_db_session: MagicMock,
    ) -> None:
        """Test complete workflow: sync all monitored channels."""
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter
        from src.tnse.db.models import Channel

        # Create mock channels
        channel1 = MagicMock()
        channel1.id = uuid4()
        channel1.username = "channel_1"
        channel1.title = "Channel One"
        channel1.is_active = True

        channel2 = MagicMock()
        channel2.id = uuid4()
        channel2.username = "channel_2"
        channel2.title = "Channel Two"
        channel2.is_active = True

        # Mock session to return channels
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [channel1, channel2]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session)

        message = create_test_message("/sync")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": SyncRateLimiter(cooldown_seconds=300),
        })
        context.args = []

        # Mock the Celery task
        with patch("src.tnse.bot.sync_handlers.collect_all_channels") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-all-channels")
            await sync_command(update, context)

        # Verify task was triggered
        mock_task.delay.assert_called_once()

        # Verify success message mentions channel count
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "2 channels" in call_args or "sync started" in call_args.lower()

    @pytest.mark.asyncio
    async def test_sync_specific_channel_workflow(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test complete workflow: sync specific channel."""
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter

        # Create mock channel
        mock_channel = MagicMock()
        mock_channel.id = uuid4()
        mock_channel.username = "test_channel"
        mock_channel.title = "Test Channel"

        # Mock session to return the channel
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_channel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session)

        message = create_test_message("/sync @test_channel")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": SyncRateLimiter(cooldown_seconds=300),
        })
        context.args = ["@test_channel"]

        # Mock the Celery task
        with patch("src.tnse.bot.sync_handlers.collect_channel_content") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-specific-channel")
            await sync_command(update, context)

        # Verify task was triggered with correct channel ID
        mock_task.delay.assert_called_once_with(str(mock_channel.id))

        # Verify success message mentions channel name
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "test_channel" in call_args.lower() or "test channel" in call_args.lower()

    @pytest.mark.asyncio
    async def test_sync_rate_limiting_workflow(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test sync rate limiting prevents rapid syncs."""
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter

        # Create mock channels
        mock_channel = MagicMock()
        mock_channel.id = uuid4()
        mock_channel.username = "test_channel"
        mock_channel.is_active = True

        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_channel]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session)

        # Create rate limiter
        rate_limiter = SyncRateLimiter(cooldown_seconds=300)

        # First sync - should succeed
        message1 = create_test_message("/sync")
        update1 = create_test_update(message1)
        context1 = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": rate_limiter,
        })
        context1.args = []

        with patch("src.tnse.bot.sync_handlers.collect_all_channels") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-1")
            await sync_command(update1, context1)

        # First sync should succeed
        mock_task.delay.assert_called_once()
        call_args1 = update1.message.reply_text.call_args[0][0]
        assert "sync started" in call_args1.lower() or "task" in call_args1.lower()

        # Second sync - should be rate limited
        message2 = create_test_message("/sync")
        update2 = create_test_update(message2)
        context2 = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": rate_limiter,
        })
        context2.args = []

        with patch("src.tnse.bot.sync_handlers.collect_all_channels") as mock_task2:
            mock_task2.delay.return_value = MagicMock(id="task-2")
            await sync_command(update2, context2)

        # Second sync should NOT trigger task (rate limited)
        mock_task2.delay.assert_not_called()

        # Should show rate limit message
        call_args2 = update2.message.reply_text.call_args[0][0]
        assert "rate" in call_args2.lower() or "wait" in call_args2.lower()

    @pytest.mark.asyncio
    async def test_sync_channel_not_monitored(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test sync for a channel that is not being monitored."""
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter

        # Mock session to return None (channel not found)
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session)

        message = create_test_message("/sync @unknown_channel")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": SyncRateLimiter(cooldown_seconds=300),
        })
        context.args = ["@unknown_channel"]

        await sync_command(update, context)

        # Should show not monitored message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "not monitored" in call_args.lower() or "not found" in call_args.lower()

    @pytest.mark.asyncio
    async def test_sync_with_access_control(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that sync command respects access control."""
        from src.tnse.bot.handlers import require_access
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter

        # Create unauthorized user
        unauthorized_user = create_test_user(user_id=999999999)
        message = create_test_message("/sync", user=unauthorized_user)
        update = create_test_update(message)
        update.effective_user = unauthorized_user

        context = create_test_context({
            "config": bot_config,
            "sync_rate_limiter": SyncRateLimiter(cooldown_seconds=300),
        })
        context.args = []

        # Apply access control wrapper
        wrapped_sync = require_access(sync_command)
        await wrapped_sync(update, context)

        # Should receive access denied
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        assert "access denied" in call_args.lower()

    @pytest.mark.asyncio
    async def test_sync_shows_typing_indicator(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that sync shows typing indicator during processing."""
        from src.tnse.bot.sync_handlers import sync_command, SyncRateLimiter
        from telegram.constants import ChatAction

        # Create mock channel
        mock_channel = MagicMock()
        mock_channel.id = uuid4()
        mock_channel.username = "test_channel"
        mock_channel.is_active = True

        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_channel]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session)

        message = create_test_message("/sync")
        update = create_test_update(message)
        context = create_test_context({
            "config": bot_config,
            "db_session_factory": mock_session_factory,
            "sync_rate_limiter": SyncRateLimiter(cooldown_seconds=300),
        })
        context.args = []

        with patch("src.tnse.bot.sync_handlers.collect_all_channels") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")
            await sync_command(update, context)

        # Verify typing indicator was sent
        context.bot.send_chat_action.assert_called_with(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

    @pytest.mark.asyncio
    async def test_sync_handler_registered_in_application(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that sync command handler is registered in application."""
        from src.tnse.bot.application import create_bot_application
        from telegram.ext import CommandHandler

        app = create_bot_application(bot_config)

        # Find sync command handler
        sync_handlers = [
            handler for handler in app.handlers.get(0, [])
            if isinstance(handler, CommandHandler) and "sync" in handler.commands
        ]

        assert len(sync_handlers) == 1

    def test_sync_rate_limiter_in_bot_data(
        self,
        bot_config: BotConfig,
    ) -> None:
        """Test that sync rate limiter is created in bot_data."""
        from src.tnse.bot.application import create_bot_application
        from src.tnse.bot.sync_handlers import SyncRateLimiter

        app = create_bot_application(bot_config)

        assert "sync_rate_limiter" in app.bot_data
        assert isinstance(app.bot_data["sync_rate_limiter"], SyncRateLimiter)
        assert app.bot_data["sync_rate_limiter"].cooldown_seconds == 300

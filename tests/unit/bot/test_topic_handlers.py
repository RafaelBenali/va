"""
Unit tests for topic command handlers.

Tests cover:
- /savetopic command
- /topics command
- /topic command
- /deletetopic command
- /templates command

Work Stream: WS-3.1 - Saved Topics
"""

import json
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from telegram import Update, User, Message, Chat

from src.tnse.bot.topic_handlers import (
    savetopic_command,
    topics_command,
    topic_command,
    deletetopic_command,
    templates_command,
    TOPIC_CALLBACK_PREFIX,
)
from src.tnse.topics.service import (
    TopicService,
    SavedTopicData,
    TopicNotFoundError,
    TopicAlreadyExistsError,
)
from src.tnse.topics.templates import TopicTemplateData


@pytest.fixture
def mock_user() -> User:
    """Create a mock Telegram user."""
    user = MagicMock(spec=User)
    user.id = 12345
    user.first_name = "Test"
    user.username = "testuser"
    return user


@pytest.fixture
def mock_message(mock_user: User) -> Message:
    """Create a mock Telegram message."""
    message = MagicMock(spec=Message)
    message.from_user = mock_user
    message.reply_text = AsyncMock()
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    return message


@pytest.fixture
def mock_update(mock_user: User, mock_message: Message) -> Update:
    """Create a mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.message = mock_message
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock callback context."""
    context = MagicMock()
    context.args = []
    context.bot_data = {}
    context.user_data = {}
    return context


@pytest.fixture
def mock_topic_service() -> AsyncMock:
    """Create a mock TopicService."""
    service = AsyncMock(spec=TopicService)
    return service


@pytest.fixture
def mock_topic_service_factory(mock_topic_service: AsyncMock) -> MagicMock:
    """Create a mock TopicServiceFactory that returns the mock_topic_service in an async context.

    This mimics the factory pattern: topic_service() returns an async context manager
    that yields the actual TopicService instance.
    """
    # Create the context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=mock_topic_service)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    # Create the factory mock - callable that returns the context manager
    factory = MagicMock(return_value=context_manager)
    return factory


class TestSavetopicCommand:
    """Tests for the /savetopic command handler."""

    @pytest.mark.asyncio
    async def test_savetopic_no_args_shows_usage(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/savetopic without arguments shows usage."""
        mock_context.args = []

        await savetopic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Usage:" in call_args

    @pytest.mark.asyncio
    async def test_savetopic_no_last_search_shows_error(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/savetopic without prior search shows error."""
        mock_context.args = ["my_topic"]
        mock_context.user_data = {}

        await savetopic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "search first" in call_args.lower() or "no search" in call_args.lower()

    @pytest.mark.asyncio
    async def test_savetopic_saves_topic_successfully(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/savetopic saves topic from last search."""
        mock_context.args = ["corruption_news"]
        mock_context.user_data = {
            "last_search_query": "corruption bribery",
        }
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        saved_topic = SavedTopicData(
            name="corruption_news",
            keywords="corruption bribery",
            created_at=datetime.now(timezone.utc),
        )
        mock_topic_service.save_topic.return_value = saved_topic

        await savetopic_command(mock_update, mock_context)

        mock_topic_service.save_topic.assert_called_once_with(
            name="corruption_news",
            keywords="corruption bribery",
            sort_mode=None,
        )
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "saved" in call_args.lower()

    @pytest.mark.asyncio
    async def test_savetopic_handles_duplicate_topic(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/savetopic handles duplicate topic name."""
        mock_context.args = ["existing_topic"]
        mock_context.user_data = {"last_search_query": "test query"}
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        mock_topic_service.save_topic.side_effect = TopicAlreadyExistsError("existing_topic")

        await savetopic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "already exists" in call_args.lower()


class TestTopicsCommand:
    """Tests for the /topics command handler."""

    @pytest.mark.asyncio
    async def test_topics_lists_saved_topics(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/topics lists all saved topics."""
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        topics = [
            SavedTopicData(
                name="corruption",
                keywords="corruption, fraud",
                created_at=datetime.now(timezone.utc),
            ),
            SavedTopicData(
                name="politics",
                keywords="government, election",
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_topic_service.list_topics.return_value = topics

        await topics_command(mock_update, mock_context)

        mock_topic_service.list_topics.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "corruption" in call_args
        assert "politics" in call_args

    @pytest.mark.asyncio
    async def test_topics_empty_list_shows_message(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/topics shows message when no topics saved."""
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}
        mock_topic_service.list_topics.return_value = []

        await topics_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "no saved topics" in call_args.lower() or "no topics" in call_args.lower()


class TestTopicCommand:
    """Tests for the /topic command handler."""

    @pytest.mark.asyncio
    async def test_topic_no_args_shows_usage(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/topic without arguments shows usage."""
        mock_context.args = []

        await topic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Usage:" in call_args

    @pytest.mark.asyncio
    async def test_topic_runs_saved_search(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/topic runs search with saved topic keywords."""
        mock_context.args = ["corruption_news"]
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        saved_topic = SavedTopicData(
            name="corruption_news",
            keywords="corruption, bribery",
            created_at=datetime.now(timezone.utc),
        )
        mock_topic_service.get_topic.return_value = saved_topic

        # Mock the search_service as well
        mock_search_service = AsyncMock()
        mock_search_service.search.return_value = []
        mock_context.bot_data["search_service"] = mock_search_service

        await topic_command(mock_update, mock_context)

        mock_topic_service.get_topic.assert_called_once_with("corruption_news")
        mock_search_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_topic_not_found_shows_error(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/topic shows error for nonexistent topic."""
        mock_context.args = ["nonexistent"]

        # Also need search_service since topic_command checks for it
        mock_search_service = AsyncMock()
        mock_context.bot_data = {
            "topic_service": mock_topic_service_factory,
            "search_service": mock_search_service,
        }

        mock_topic_service.get_topic.side_effect = TopicNotFoundError("nonexistent")

        await topic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "not found" in call_args.lower()


class TestDeletetopicCommand:
    """Tests for the /deletetopic command handler."""

    @pytest.mark.asyncio
    async def test_deletetopic_no_args_shows_usage(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/deletetopic without arguments shows usage."""
        mock_context.args = []

        await deletetopic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Usage:" in call_args

    @pytest.mark.asyncio
    async def test_deletetopic_deletes_topic(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/deletetopic deletes an existing topic."""
        mock_context.args = ["old_topic"]
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        await deletetopic_command(mock_update, mock_context)

        mock_topic_service.delete_topic.assert_called_once_with("old_topic")
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "deleted" in call_args.lower()

    @pytest.mark.asyncio
    async def test_deletetopic_not_found_shows_error(
        self,
        mock_update: Update,
        mock_context: MagicMock,
        mock_topic_service: AsyncMock,
        mock_topic_service_factory: MagicMock,
    ) -> None:
        """/deletetopic shows error for nonexistent topic."""
        mock_context.args = ["nonexistent"]
        mock_context.bot_data = {"topic_service": mock_topic_service_factory}

        mock_topic_service.delete_topic.side_effect = TopicNotFoundError("nonexistent")

        await deletetopic_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "not found" in call_args.lower()


class TestTemplatesCommand:
    """Tests for the /templates command handler."""

    @pytest.mark.asyncio
    async def test_templates_lists_all_templates(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/templates lists all pre-built templates."""
        await templates_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]

        # Should contain all 5 required templates
        assert "corruption" in call_args.lower()
        assert "politics" in call_args.lower()
        assert "tech" in call_args.lower()
        assert "science" in call_args.lower()
        assert "business" in call_args.lower()

    @pytest.mark.asyncio
    async def test_templates_shows_keywords(
        self,
        mock_update: Update,
        mock_context: MagicMock,
    ) -> None:
        """/templates shows keywords for each template."""
        await templates_command(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        # Should show some keywords
        assert "keyword" in call_args.lower() or "bribery" in call_args.lower() or "government" in call_args.lower()


class TestTopicCallbackHandler:
    """Tests for topic-related callback handlers."""

    def test_topic_callback_prefix_defined(self) -> None:
        """TOPIC_CALLBACK_PREFIX is defined and non-empty."""
        assert TOPIC_CALLBACK_PREFIX
        assert isinstance(TOPIC_CALLBACK_PREFIX, str)

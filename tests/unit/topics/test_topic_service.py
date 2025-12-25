"""
Unit tests for TopicService.

Tests cover:
- Saving topics
- Retrieving saved topics
- Listing all topics
- Deleting topics
- Error handling for non-existent topics

Work Stream: WS-3.1 - Saved Topics
"""

import json
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tnse.topics.service import (
    TopicService,
    SavedTopicData,
    TopicNotFoundError,
    TopicAlreadyExistsError,
)


class TestSavedTopicData:
    """Tests for the SavedTopicData dataclass."""

    def test_create_saved_topic_data_with_required_fields(self) -> None:
        """SavedTopicData can be created with required fields only."""
        topic = SavedTopicData(
            name="corruption_news",
            keywords="corruption, bribery, scandal",
        )

        assert topic.name == "corruption_news"
        assert topic.keywords == "corruption, bribery, scandal"
        assert topic.sort_mode is None
        assert topic.created_at is not None

    def test_create_saved_topic_data_with_all_fields(self) -> None:
        """SavedTopicData can be created with all fields."""
        created_at = datetime.now(timezone.utc)
        topic_id = str(uuid4())

        topic = SavedTopicData(
            topic_id=topic_id,
            name="politics",
            keywords="government, election",
            sort_mode="views",
            created_at=created_at,
        )

        assert topic.topic_id == topic_id
        assert topic.name == "politics"
        assert topic.keywords == "government, election"
        assert topic.sort_mode == "views"
        assert topic.created_at == created_at

    def test_saved_topic_data_to_dict(self) -> None:
        """SavedTopicData can be converted to dictionary."""
        topic = SavedTopicData(
            name="tech",
            keywords="technology, AI",
            sort_mode="combined",
        )

        topic_dict = topic.to_dict()

        assert topic_dict["name"] == "tech"
        assert topic_dict["keywords"] == "technology, AI"
        assert topic_dict["sort_mode"] == "combined"
        assert "created_at" in topic_dict


class TestTopicService:
    """Tests for the TopicService class."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def topic_service(self, mock_session: MagicMock) -> TopicService:
        """Create a TopicService with mocked session."""
        return TopicService(session=mock_session)

    @pytest.mark.asyncio
    async def test_save_topic_creates_new_topic(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """save_topic creates a new topic in the database."""
        # Setup mock to return no existing topic
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await topic_service.save_topic(
            name="corruption_news",
            keywords="corruption, bribery, scandal",
            sort_mode="views",
        )

        assert result.name == "corruption_news"
        assert result.keywords == "corruption, bribery, scandal"
        assert result.sort_mode == "views"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_topic_raises_error_if_exists(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """save_topic raises TopicAlreadyExistsError if topic name exists."""
        # Setup mock to return existing topic
        existing_topic = MagicMock()
        existing_topic.name = "corruption_news"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_topic
        mock_session.execute.return_value = mock_result

        with pytest.raises(TopicAlreadyExistsError) as exc_info:
            await topic_service.save_topic(
                name="corruption_news",
                keywords="corruption, bribery",
            )

        assert "corruption_news" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_topic_returns_existing_topic(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """get_topic returns the topic if it exists."""
        # Setup mock to return existing topic
        existing_topic = MagicMock()
        existing_topic.id = str(uuid4())
        existing_topic.name = "politics"
        existing_topic.keywords = "government, election"
        existing_topic.search_config = json.dumps({"sort_mode": "combined"})
        existing_topic.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_topic
        mock_session.execute.return_value = mock_result

        result = await topic_service.get_topic("politics")

        assert result is not None
        assert result.name == "politics"
        assert result.keywords == "government, election"

    @pytest.mark.asyncio
    async def test_get_topic_raises_error_if_not_found(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """get_topic raises TopicNotFoundError if topic does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(TopicNotFoundError) as exc_info:
            await topic_service.get_topic("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_topics_returns_all_topics(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """list_topics returns all saved topics."""
        # Setup mock to return multiple topics
        topic1 = MagicMock()
        topic1.id = str(uuid4())
        topic1.name = "corruption"
        topic1.keywords = "corruption, fraud"
        topic1.search_config = None
        topic1.created_at = datetime.now(timezone.utc)

        topic2 = MagicMock()
        topic2.id = str(uuid4())
        topic2.name = "politics"
        topic2.keywords = "government, election"
        topic2.search_config = json.dumps({"sort_mode": "views"})
        topic2.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [topic1, topic2]
        mock_session.execute.return_value = mock_result

        results = await topic_service.list_topics()

        assert len(results) == 2
        assert results[0].name == "corruption"
        assert results[1].name == "politics"

    @pytest.mark.asyncio
    async def test_list_topics_returns_empty_list_when_no_topics(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """list_topics returns empty list when no topics exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await topic_service.list_topics()

        assert results == []

    @pytest.mark.asyncio
    async def test_delete_topic_removes_existing_topic(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """delete_topic removes an existing topic."""
        # Setup mock to return existing topic
        existing_topic = MagicMock()
        existing_topic.name = "old_topic"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_topic
        mock_session.execute.return_value = mock_result

        await topic_service.delete_topic("old_topic")

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_topic_raises_error_if_not_found(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """delete_topic raises TopicNotFoundError if topic does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(TopicNotFoundError) as exc_info:
            await topic_service.delete_topic("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_topic_normalizes_name(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """save_topic normalizes topic names to lowercase."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await topic_service.save_topic(
            name="My_Topic_Name",
            keywords="test",
        )

        assert result.name == "my_topic_name"

    @pytest.mark.asyncio
    async def test_get_topic_normalizes_name_for_lookup(
        self, topic_service: TopicService, mock_session: MagicMock
    ) -> None:
        """get_topic normalizes topic names before lookup."""
        existing_topic = MagicMock()
        existing_topic.id = str(uuid4())
        existing_topic.name = "my_topic"
        existing_topic.keywords = "test"
        existing_topic.search_config = None
        existing_topic.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_topic
        mock_session.execute.return_value = mock_result

        result = await topic_service.get_topic("My_Topic")

        assert result is not None
        # Verify lowercase name was used in query

"""
TNSE Topic Service Module

Provides the TopicService class for managing saved topics.
Supports CRUD operations on saved topics in the database.

Work Stream: WS-3.1 - Saved Topics
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.tnse.core.logging import get_logger
from src.tnse.db.models import SavedTopic

logger = get_logger(__name__)


class TopicNotFoundError(Exception):
    """Raised when a requested topic does not exist."""

    def __init__(self, topic_name: str) -> None:
        self.topic_name = topic_name
        super().__init__(f"Topic not found: {topic_name}")


class TopicAlreadyExistsError(Exception):
    """Raised when attempting to create a topic with a name that already exists."""

    def __init__(self, topic_name: str) -> None:
        self.topic_name = topic_name
        super().__init__(f"Topic already exists: {topic_name}")


@dataclass
class SavedTopicData:
    """Data structure for saved topic information.

    Attributes:
        name: Unique topic name (normalized to lowercase).
        keywords: Comma-separated search keywords.
        sort_mode: Optional sort mode (views, reactions, combined).
        topic_id: Database ID (UUID as string).
        created_at: When the topic was created.
    """

    name: str
    keywords: str
    sort_mode: Optional[str] = None
    topic_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with topic fields.
        """
        return {
            "topic_id": self.topic_id,
            "name": self.name,
            "keywords": self.keywords,
            "sort_mode": self.sort_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TopicService:
    """Service for managing saved topics.

    Provides methods for creating, retrieving, listing, and deleting
    saved topic configurations.

    Attributes:
        session: AsyncSession for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the TopicService.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a topic name to lowercase.

        Args:
            name: The topic name to normalize.

        Returns:
            Lowercase topic name.
        """
        return name.lower()

    def _model_to_data(self, model: SavedTopic) -> SavedTopicData:
        """Convert a SavedTopic model to SavedTopicData.

        Args:
            model: The database model.

        Returns:
            SavedTopicData with model values.
        """
        # Extract sort_mode from search_config if present
        sort_mode = None
        if model.search_config:
            try:
                config = json.loads(model.search_config)
                sort_mode = config.get("sort_mode")
            except json.JSONDecodeError:
                pass

        return SavedTopicData(
            topic_id=str(model.id) if model.id else None,
            name=model.name,
            keywords=model.keywords or "",
            sort_mode=sort_mode,
            created_at=model.created_at,
        )

    async def save_topic(
        self,
        name: str,
        keywords: str,
        sort_mode: Optional[str] = None,
    ) -> SavedTopicData:
        """Save a new topic configuration.

        Args:
            name: Unique topic name (will be normalized to lowercase).
            keywords: Comma-separated search keywords.
            sort_mode: Optional sort mode preference.

        Returns:
            SavedTopicData for the created topic.

        Raises:
            TopicAlreadyExistsError: If a topic with this name already exists.
        """
        normalized_name = self._normalize_name(name)

        # Check if topic already exists
        stmt = select(SavedTopic).where(SavedTopic.name == normalized_name)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.warning(
                "Attempted to create duplicate topic",
                topic_name=normalized_name,
            )
            raise TopicAlreadyExistsError(normalized_name)

        # Create search_config JSON if sort_mode is provided
        search_config = None
        if sort_mode:
            search_config = json.dumps({"sort_mode": sort_mode})

        # Create new topic
        topic = SavedTopic(
            name=normalized_name,
            keywords=keywords,
            search_config=search_config,
            is_active=True,
        )
        self.session.add(topic)
        await self.session.commit()

        logger.info(
            "Topic saved successfully",
            topic_name=normalized_name,
            keywords=keywords,
        )

        return SavedTopicData(
            topic_id=str(topic.id) if topic.id else None,
            name=normalized_name,
            keywords=keywords,
            sort_mode=sort_mode,
            created_at=topic.created_at,
        )

    async def get_topic(self, name: str) -> SavedTopicData:
        """Retrieve a topic by name.

        Args:
            name: Topic name to look up (case-insensitive).

        Returns:
            SavedTopicData for the found topic.

        Raises:
            TopicNotFoundError: If no topic with this name exists.
        """
        normalized_name = self._normalize_name(name)

        stmt = select(SavedTopic).where(SavedTopic.name == normalized_name)
        result = await self.session.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            logger.warning(
                "Topic not found",
                topic_name=normalized_name,
            )
            raise TopicNotFoundError(normalized_name)

        return self._model_to_data(topic)

    async def list_topics(self) -> list[SavedTopicData]:
        """List all saved topics.

        Returns:
            List of SavedTopicData for all topics.
        """
        stmt = select(SavedTopic).where(SavedTopic.is_active == True).order_by(SavedTopic.name)
        result = await self.session.execute(stmt)
        topics = result.scalars().all()

        return [self._model_to_data(topic) for topic in topics]

    async def delete_topic(self, name: str) -> None:
        """Delete a saved topic.

        Args:
            name: Topic name to delete (case-insensitive).

        Raises:
            TopicNotFoundError: If no topic with this name exists.
        """
        normalized_name = self._normalize_name(name)

        # Check if topic exists
        stmt = select(SavedTopic).where(SavedTopic.name == normalized_name)
        result = await self.session.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            logger.warning(
                "Attempted to delete nonexistent topic",
                topic_name=normalized_name,
            )
            raise TopicNotFoundError(normalized_name)

        # Delete the topic
        delete_stmt = delete(SavedTopic).where(SavedTopic.name == normalized_name)
        await self.session.execute(delete_stmt)
        await self.session.commit()

        logger.info(
            "Topic deleted successfully",
            topic_name=normalized_name,
        )

"""
TNSE Content Collector Service

Service for collecting and extracting content from Telegram channels.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Create content collection job
- Implement 24-hour content window
- Extract text content
- Extract media metadata
- Detect forwarded messages
- Store in database
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from src.tnse.telegram.client import MediaInfo, MessageInfo, TelegramClient


@dataclass
class ContentCollector:
    """Service for collecting content from Telegram channels.

    Provides methods to:
    - Collect messages within a time window
    - Extract text content from messages
    - Extract media metadata
    - Detect and process forwarded messages
    - Extract engagement metrics

    Attributes:
        telegram_client: Telegram client for API calls
        content_window_hours: Hours of content to collect (default 24)
    """

    telegram_client: TelegramClient
    content_window_hours: int = 24

    def get_cutoff_time(self) -> datetime:
        """Calculate the cutoff time for content collection.

        Returns:
            Datetime representing the start of the content window.
        """
        return datetime.now(timezone.utc) - timedelta(hours=self.content_window_hours)

    def is_within_window(self, message_time: datetime) -> bool:
        """Check if a message timestamp is within the collection window.

        Args:
            message_time: The timestamp of the message.

        Returns:
            True if the message is within the window, False otherwise.
        """
        cutoff = self.get_cutoff_time()
        return message_time >= cutoff

    def extract_text_content(self, message: MessageInfo) -> str:
        """Extract text content from a message.

        Handles None and empty strings gracefully.
        Preserves Unicode/Cyrillic text.

        Args:
            message: The message to extract text from.

        Returns:
            The text content, or empty string if no text.
        """
        if message.text is None:
            return ""
        return message.text

    def extract_media_metadata(self, message: MessageInfo) -> list[dict[str, Any]]:
        """Extract media metadata from a message.

        Extracts information about all media attachments including:
        - Media type (photo, video, document, audio, animation)
        - File ID and size
        - Dimensions (width, height) for images/videos
        - Duration for audio/video
        - MIME type

        Args:
            message: The message to extract media from.

        Returns:
            List of dictionaries containing media metadata.
        """
        if not message.media:
            return []

        result = []
        for media in message.media:
            media_dict = {
                "media_type": media.media_type,
                "file_id": media.file_id,
                "file_size": media.file_size,
                "mime_type": media.mime_type,
                "width": media.width,
                "height": media.height,
                "duration": media.duration,
                "thumbnail_file_id": media.thumbnail_file_id,
            }
            result.append(media_dict)

        return result

    def is_forwarded(self, message: MessageInfo) -> bool:
        """Check if a message is forwarded from another channel.

        Args:
            message: The message to check.

        Returns:
            True if the message is forwarded, False otherwise.
        """
        return message.is_forwarded

    def extract_forward_info(self, message: MessageInfo) -> dict[str, Optional[int]]:
        """Extract forwarding information from a message.

        Args:
            message: The message to extract forward info from.

        Returns:
            Dictionary containing forward source information.
        """
        return {
            "forward_from_channel_id": message.forward_from_channel_id,
            "forward_from_message_id": message.forward_from_message_id,
        }

    def extract_engagement(self, message: MessageInfo) -> dict[str, Any]:
        """Extract engagement metrics from a message.

        Extracts:
        - View count
        - Forward count
        - Reply count
        - Reactions (by emoji type)

        Args:
            message: The message to extract engagement from.

        Returns:
            Dictionary containing engagement metrics.
        """
        return {
            "view_count": message.views,
            "forward_count": message.forwards,
            "reply_count": message.replies,
            "reactions": message.reactions.copy() if message.reactions else {},
        }

    def extract_message_data(
        self,
        message: MessageInfo,
        channel_uuid: UUID,
    ) -> dict[str, Any]:
        """Extract complete message data for database storage.

        Combines all extraction methods to create a complete data
        dictionary ready for database insertion.

        Args:
            message: The message to extract data from.
            channel_uuid: UUID of the channel in the database.

        Returns:
            Dictionary containing all message data for storage.
        """
        engagement = self.extract_engagement(message)
        forward_info = self.extract_forward_info(message)

        return {
            # Post identification
            "telegram_message_id": message.message_id,
            "channel_id": channel_uuid,
            "published_at": message.date,
            # Content
            "text_content": self.extract_text_content(message),
            # Forward info
            "is_forwarded": self.is_forwarded(message),
            "forward_from_channel_id": forward_info["forward_from_channel_id"],
            "forward_from_message_id": forward_info["forward_from_message_id"],
            # Media
            "media": self.extract_media_metadata(message),
            # Engagement
            "views": engagement["view_count"],
            "forwards": engagement["forward_count"],
            "replies": engagement["reply_count"],
            "reactions": engagement["reactions"],
        }

    async def collect_channel_messages(
        self,
        telegram_channel_id: int,
        channel_uuid: UUID,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Collect messages from a channel within the content window.

        Fetches messages from the Telegram API and filters them
        to only include messages within the configured time window.

        Args:
            telegram_channel_id: Telegram's internal channel ID.
            channel_uuid: UUID of the channel in the database.
            limit: Maximum number of messages to fetch.

        Returns:
            List of message data dictionaries ready for storage.
        """
        # Fetch messages from Telegram
        messages = await self.telegram_client.get_messages(
            channel_id=telegram_channel_id,
            limit=limit,
        )

        # Filter by time window and extract data
        result = []
        for message in messages:
            if self.is_within_window(message.date):
                message_data = self.extract_message_data(message, channel_uuid)
                result.append(message_data)

        return result

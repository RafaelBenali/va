"""
TNSE Channel Service Module

Provides channel validation, metadata fetching, and message retrieval.

Work Stream: WS-1.4 - Telegram API Integration

Requirements addressed:
- Implement channel validation (public/accessible)
- Create channel metadata fetcher
- Implement message history retrieval (24 hours)
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.tnse.telegram.client import ChannelInfo, MessageInfo, TelegramClient


@dataclass
class ChannelValidationResult:
    """Result of channel validation.

    Attributes:
        is_valid: Whether the channel is valid and accessible
        channel_info: Channel information if valid
        error: Error message if invalid
        error_code: Error code for programmatic handling
    """

    is_valid: bool
    channel_info: Optional[ChannelInfo]
    error: Optional[str] = None
    error_code: Optional[str] = None


class ChannelService:
    """Service for channel validation, metadata, and message retrieval.

    Provides high-level operations for working with Telegram channels,
    including validation, metadata fetching, and message history.

    Attributes:
        client: Telegram client for API calls
    """

    # Regex pattern to extract username from t.me URLs
    TME_URL_PATTERN = re.compile(
        r"(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/)?([a-zA-Z0-9_]+)"
    )

    def __init__(self, client: TelegramClient) -> None:
        """Initialize the channel service.

        Args:
            client: Telegram client instance
        """
        self.client = client

    def _extract_identifier(self, identifier: str) -> str:
        """Extract channel username from various formats.

        Handles:
        - @username
        - username
        - https://t.me/username
        - https://telegram.me/username

        Args:
            identifier: Channel identifier in any format

        Returns:
            Clean username without @ or URL prefix
        """
        # Check if it's a URL
        url_match = self.TME_URL_PATTERN.match(identifier)
        if url_match:
            return url_match.group(1)

        # Strip @ prefix if present
        return identifier.lstrip("@")

    async def validate_channel(self, identifier: str) -> ChannelValidationResult:
        """Validate a channel and check if it's accessible.

        Args:
            identifier: Channel username, @username, or t.me URL

        Returns:
            ChannelValidationResult with validation status
        """
        clean_identifier = self._extract_identifier(identifier)

        try:
            channel_info = await self.client.get_channel(clean_identifier)

            if channel_info is None:
                return ChannelValidationResult(
                    is_valid=False,
                    channel_info=None,
                    error=f"Channel '{identifier}' not found",
                    error_code="NOT_FOUND",
                )

            if not channel_info.is_public:
                return ChannelValidationResult(
                    is_valid=False,
                    channel_info=channel_info,
                    error=f"Channel '{identifier}' is private and cannot be monitored",
                    error_code="PRIVATE_CHANNEL",
                )

            return ChannelValidationResult(
                is_valid=True,
                channel_info=channel_info,
            )

        except Exception as error:
            return ChannelValidationResult(
                is_valid=False,
                channel_info=None,
                error=str(error),
                error_code="API_ERROR",
            )

    async def get_channel_metadata(self, identifier: str) -> Optional[ChannelInfo]:
        """Get channel metadata.

        Args:
            identifier: Channel username, @username, or t.me URL

        Returns:
            ChannelInfo if found, None otherwise
        """
        clean_identifier = self._extract_identifier(identifier)

        try:
            return await self.client.get_channel(clean_identifier)
        except Exception:
            return None

    async def get_recent_messages(
        self,
        channel_id: int,
        hours: int = 24,
        limit: int = 100,
    ) -> list[MessageInfo]:
        """Get recent messages from a channel.

        Retrieves messages from the specified time window.

        Args:
            channel_id: Telegram channel ID
            hours: Number of hours to look back (default 24)
            limit: Maximum number of messages to retrieve

        Returns:
            List of MessageInfo objects
        """
        try:
            # Calculate the cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Get messages from the client
            messages = await self.client.get_messages(
                channel_id=channel_id,
                limit=limit,
            )

            # Filter messages within the time window
            filtered_messages = [
                message
                for message in messages
                if message.date >= cutoff_time
            ]

            return filtered_messages

        except Exception:
            return []

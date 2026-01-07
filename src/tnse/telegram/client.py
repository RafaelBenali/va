"""
TNSE Telegram Client Abstraction Layer

Provides an abstraction over Telethon for accessing Telegram channels.

Work Stream: WS-1.4 - Telegram API Integration

Requirements addressed:
- Create Telegram API abstraction layer
- Store credentials encrypted (via configuration)
- Set up Telethon/Pyrogram client

Python 3.10+ Modernization (WS-6.3):
- Uses X | None instead of Optional[X] for union types
- Uses Self type for context managers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Self

from src.tnse.core.logging import get_logger

if TYPE_CHECKING:
    from src.tnse.core.config import Settings

# Module-level logger
logger = get_logger(__name__)


@dataclass
class TelegramClientConfig:
    """Configuration for Telegram client connection.

    Attributes:
        api_id: Telegram API ID from my.telegram.org
        api_hash: Telegram API hash from my.telegram.org
        session_name: Name for the session file
        connection_timeout: Connection timeout in seconds
        phone: Optional phone number for authentication
    """

    api_id: str
    api_hash: str
    session_name: str = "tnse_session"
    connection_timeout: int = 30
    phone: str | None = None

    @classmethod
    def from_settings(cls, settings: "Settings") -> "TelegramClientConfig":
        """Create config from application settings.

        Args:
            settings: Application settings instance

        Returns:
            TelegramClientConfig with values from settings
        """
        return cls(
            api_id=settings.telegram.api_id or "",
            api_hash=settings.telegram.api_hash or "",
            phone=settings.telegram.phone,
        )


@dataclass
class MediaInfo:
    """Information about media attached to a message.

    Attributes:
        media_type: Type of media (photo, video, document, audio, animation)
        file_id: Telegram file ID for downloading
        file_size: Size in bytes
        mime_type: MIME type of the file
        width: Width in pixels (for images/videos)
        height: Height in pixels (for images/videos)
        duration: Duration in seconds (for audio/video)
        thumbnail_file_id: File ID for thumbnail
    """

    media_type: str
    file_id: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration: int | None = None
    thumbnail_file_id: str | None = None


@dataclass
class MessageInfo:
    """Information about a Telegram message.

    Attributes:
        message_id: Telegram message ID
        channel_id: ID of the channel this message belongs to
        text: Text content of the message
        date: When the message was posted
        views: Number of views
        forwards: Number of forwards
        replies: Number of replies
        reactions: Dictionary mapping emoji to count
        media: List of media attachments
        is_forwarded: Whether this is a forwarded message
        forward_from_channel_id: Original channel ID if forwarded
        forward_from_message_id: Original message ID if forwarded
    """

    message_id: int
    channel_id: int
    text: str | None
    date: datetime
    views: int = 0
    forwards: int = 0
    replies: int = 0
    reactions: dict[str, int] = field(default_factory=dict)
    media: list[MediaInfo] = field(default_factory=list)
    is_forwarded: bool = False
    forward_from_channel_id: int | None = None
    forward_from_message_id: int | None = None


@dataclass
class ChannelInfo:
    """Information about a Telegram channel.

    Attributes:
        telegram_id: Telegram's internal channel ID
        username: Channel username (without @)
        title: Channel display name
        subscriber_count: Number of subscribers
        is_public: Whether the channel is public
        description: Channel description/about text
        photo_url: URL to channel photo
        invite_link: Channel invite link
    """

    telegram_id: int
    username: str
    title: str
    subscriber_count: int
    is_public: bool
    description: str | None = None
    photo_url: str | None = None
    invite_link: str | None = None


class TelegramClient(ABC):
    """Abstract base class for Telegram client implementations.

    Defines the interface that all Telegram client implementations must follow.
    This abstraction allows for easy testing and potential alternative implementations.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to Telegram.

        Raises:
            ConnectionError: If connection fails
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from Telegram."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if client is connected.

        Returns:
            True if connected, False otherwise
        """

    @abstractmethod
    async def get_channel(self, identifier: str) -> ChannelInfo | None:
        """Get information about a channel.

        Args:
            identifier: Channel username (with or without @) or invite link

        Returns:
            ChannelInfo if channel exists and is accessible, None otherwise
        """

    @abstractmethod
    async def get_messages(
        self,
        channel_id: int,
        limit: int = 100,
        offset_date: datetime | None = None,
        min_id: int = 0,
    ) -> list[MessageInfo]:
        """Get messages from a channel.

        Args:
            channel_id: Telegram channel ID
            limit: Maximum number of messages to retrieve
            offset_date: Get messages before this date
            min_id: Only get messages with ID greater than this

        Returns:
            List of MessageInfo objects
        """


class TelethonClient(TelegramClient):
    """Telegram client implementation using Telethon.

    Provides channel access and message retrieval functionality
    using the Telethon MTProto library.
    """

    def __init__(self, config: TelegramClientConfig) -> None:
        """Initialize the Telethon client.

        Args:
            config: Client configuration
        """
        self.config = config
        self._connected = False
        self._authorized = False
        self._client: "TelethonClientWrapper | None" = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the underlying Telethon client."""
        try:
            from telethon import TelegramClient as TelethonTelegramClient

            self._client = TelethonTelegramClient(
                self.config.session_name,
                int(self.config.api_id),
                self.config.api_hash,
                connection_retries=3,
                timeout=self.config.connection_timeout,
            )
        except ImportError:
            # Telethon not installed - will fail on connect
            self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected.

        Returns:
            True if connected, False otherwise
        """
        if self._client is None:
            return False
        return self._connected

    @property
    def is_authorized(self) -> bool:
        """Check if client session is authorized.

        Returns:
            True if authorized with valid session, False otherwise
        """
        return self._authorized

    async def connect(self) -> None:
        """Establish connection to Telegram.

        Raises:
            ConnectionError: If connection fails
            ImportError: If Telethon is not installed
        """
        if self._client is None:
            raise ImportError("Telethon is not installed. Install with: pip install telethon")

        try:
            await self._client.connect()
            self._connected = self._client.is_connected()

            # Check authorization status after connection
            self._authorized = await self._client.is_user_authorized()
            if not self._authorized:
                logger.warning(
                    "Telegram session is not authorized",
                    session_name=self.config.session_name,
                    hint="Run authentication flow to authorize session"
                )
            else:
                logger.info(
                    "Telegram client connected and authorized",
                    session_name=self.config.session_name
                )
        except Exception as error:
            logger.error(
                "Failed to connect to Telegram",
                session_name=self.config.session_name,
                error=str(error)
            )
            raise ConnectionError(f"Failed to connect to Telegram: {error}") from error

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._client is not None:
            await self._client.disconnect()
            self._connected = False

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def _ensure_connected(self) -> bool:
        """Ensure the client is connected, auto-connecting if necessary.

        This method enables lazy connection - the client will automatically
        connect on first API call if not already connected.

        Returns:
            True if connected (or successfully auto-connected), False otherwise
        """
        if self._client is None:
            logger.error(
                "Telegram client not initialized",
                hint="Telethon may not be installed"
            )
            return False

        if not self.is_connected:
            try:
                await self.connect()
            except Exception as error:
                logger.error(
                    "Failed to auto-connect to Telegram",
                    error=str(error),
                    session_name=self.config.session_name
                )
                return False

        # Warn if connected but not authorized
        if self.is_connected and not self.is_authorized:
            logger.warning(
                "Client connected but session is not authorized - API calls will fail",
                session_name=self.config.session_name
            )

        return self.is_connected

    async def get_channel(self, identifier: str) -> ChannelInfo | None:
        """Get information about a channel.

        Args:
            identifier: Channel username (with or without @) or invite link

        Returns:
            ChannelInfo if channel exists and is accessible, None otherwise
        """
        if not await self._ensure_connected():
            logger.warning(
                "Cannot get channel - not connected",
                identifier=identifier
            )
            return None

        try:
            from telethon.tl.functions.channels import GetFullChannelRequest

            # Clean up identifier
            clean_identifier = identifier.lstrip("@")

            entity = await self._client.get_entity(clean_identifier)

            # Get full channel info for subscriber count
            full_channel = await self._client(GetFullChannelRequest(entity))

            return ChannelInfo(
                telegram_id=entity.id,
                username=getattr(entity, "username", None) or clean_identifier,
                title=getattr(entity, "title", ""),
                subscriber_count=full_channel.full_chat.participants_count,
                is_public=not getattr(entity, "restricted", False),
                description=full_channel.full_chat.about,
                photo_url=None,  # Would need to download photo
                invite_link=None,
            )
        except Exception as error:
            logger.error(
                "Failed to get channel info",
                identifier=identifier,
                error=str(error),
                error_type=type(error).__name__
            )
            return None

    async def get_messages(
        self,
        channel_id: int,
        limit: int = 100,
        offset_date: datetime | None = None,
        min_id: int = 0,
        channel_username: str | None = None,
    ) -> list[MessageInfo]:
        """Get messages from a channel.

        Args:
            channel_id: Telegram channel ID
            limit: Maximum number of messages to retrieve
            offset_date: Get messages before this date
            min_id: Only get messages with ID greater than this
            channel_username: Channel username for entity resolution (recommended)

        Returns:
            List of MessageInfo objects
        """
        if not await self._ensure_connected():
            logger.warning(
                "Cannot get messages - not connected",
                channel_id=channel_id
            )
            return []

        # Resolve entity - prefer username for fresh sessions
        entity = channel_id
        if channel_username:
            try:
                entity = await self._client.get_entity(channel_username)
                logger.debug(
                    "Resolved channel entity by username",
                    channel_username=channel_username,
                    channel_id=channel_id
                )
            except Exception as resolve_error:
                logger.warning(
                    "Failed to resolve channel by username, falling back to ID",
                    channel_username=channel_username,
                    channel_id=channel_id,
                    error=str(resolve_error)
                )
                entity = channel_id

        try:
            messages = await self._client.get_messages(
                entity,
                limit=limit,
                offset_date=offset_date,
                min_id=min_id,
            )

            result = []
            for message in messages:
                # Skip only if the message object itself is None
                # Do NOT skip media-only posts (where message.message text is None)
                if message is None:
                    continue

                message_info = self._parse_message(message, channel_id)
                if message_info:
                    result.append(message_info)

            logger.debug(
                "Retrieved messages from channel",
                channel_id=channel_id,
                messages_count=len(result),
                limit=limit,
                min_id=min_id
            )
            return result
        except Exception as error:
            logger.error(
                "Failed to get messages from channel",
                channel_id=channel_id,
                limit=limit,
                min_id=min_id,
                error=str(error),
                error_type=type(error).__name__
            )
            return []

    def _parse_message(self, message: object, channel_id: int) -> MessageInfo | None:
        """Parse a Telethon message into MessageInfo.

        Args:
            message: Telethon Message object
            channel_id: ID of the channel

        Returns:
            MessageInfo or None if parsing fails
        """
        try:
            # Extract reactions
            reactions: dict[str, int] = {}
            if hasattr(message, "reactions") and message.reactions:
                for reaction in message.reactions.results:
                    emoji = getattr(reaction.reaction, "emoticon", str(reaction.reaction))
                    reactions[emoji] = reaction.count

            # Extract media
            media_list: list[MediaInfo] = []
            if hasattr(message, "media") and message.media:
                media_info = self._parse_media(message.media)
                if media_info:
                    media_list.append(media_info)

            # Extract forward info
            is_forwarded = hasattr(message, "fwd_from") and message.fwd_from is not None
            forward_from_channel_id = None
            forward_from_message_id = None
            if is_forwarded and message.fwd_from:
                if hasattr(message.fwd_from, "channel_id"):
                    forward_from_channel_id = message.fwd_from.channel_id
                if hasattr(message.fwd_from, "channel_post"):
                    forward_from_message_id = message.fwd_from.channel_post

            return MessageInfo(
                message_id=message.id,
                channel_id=channel_id,
                text=message.message or "",
                date=message.date,
                views=getattr(message, "views", 0) or 0,
                forwards=getattr(message, "forwards", 0) or 0,
                replies=getattr(message, "replies", None)
                and message.replies.replies
                or 0,
                reactions=reactions,
                media=media_list,
                is_forwarded=is_forwarded,
                forward_from_channel_id=forward_from_channel_id,
                forward_from_message_id=forward_from_message_id,
            )
        except Exception:
            return None

    def _parse_media(self, media: object) -> MediaInfo | None:
        """Parse Telethon media into MediaInfo.

        Args:
            media: Telethon MessageMedia object

        Returns:
            MediaInfo or None if parsing fails
        """
        try:
            media_type = "document"
            file_id = None
            file_size = None
            mime_type = None
            width = None
            height = None
            duration = None

            if hasattr(media, "photo") and media.photo:
                media_type = "photo"
                file_id = str(media.photo.id)
                if media.photo.sizes:
                    largest = max(media.photo.sizes, key=lambda size: getattr(size, "w", 0) * getattr(size, "h", 0))
                    width = getattr(largest, "w", None)
                    height = getattr(largest, "h", None)
            elif hasattr(media, "document") and media.document:
                document = media.document
                file_id = str(document.id)
                file_size = document.size
                mime_type = document.mime_type

                # Check for video
                if mime_type and mime_type.startswith("video/"):
                    media_type = "video"
                    for attr in document.attributes:
                        if hasattr(attr, "w"):
                            width = attr.w
                            height = attr.h
                        if hasattr(attr, "duration"):
                            duration = attr.duration
                # Check for audio
                elif mime_type and mime_type.startswith("audio/"):
                    media_type = "audio"
                    for attr in document.attributes:
                        if hasattr(attr, "duration"):
                            duration = attr.duration
                # Check for animation/GIF
                elif mime_type == "image/gif" or any(
                    hasattr(attr, "round_message") for attr in document.attributes
                ):
                    media_type = "animation"

            return MediaInfo(
                media_type=media_type,
                file_id=file_id,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                duration=duration,
            )
        except Exception:
            return None

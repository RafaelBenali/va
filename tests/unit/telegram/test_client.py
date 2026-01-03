"""
Tests for TNSE Telegram Client Abstraction Layer.

Following TDD methodology: these tests are written BEFORE the implementation.

Work Stream: WS-1.4 - Telegram API Integration

Requirements addressed:
- Create Telegram API abstraction layer
- Store credentials encrypted
- Handle rate limiting with backoff
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTelegramClientConfig:
    """Tests for TelegramClientConfig dataclass."""

    def test_config_requires_api_id_and_hash(self):
        """Test that config requires both api_id and api_hash."""
        from src.tnse.telegram.client import TelegramClientConfig

        config = TelegramClientConfig(
            api_id="12345",
            api_hash="abcdef123456",
            session_name="test_session",
        )
        assert config.api_id == "12345"
        assert config.api_hash == "abcdef123456"
        assert config.session_name == "test_session"

    def test_config_has_default_session_name(self):
        """Test that config has a default session name."""
        from src.tnse.telegram.client import TelegramClientConfig

        config = TelegramClientConfig(
            api_id="12345",
            api_hash="abcdef123456",
        )
        assert config.session_name == "tnse_session"

    def test_config_has_default_timeout(self):
        """Test that config has a default connection timeout."""
        from src.tnse.telegram.client import TelegramClientConfig

        config = TelegramClientConfig(
            api_id="12345",
            api_hash="abcdef123456",
        )
        assert config.connection_timeout == 30

    def test_config_from_settings(self):
        """Test creating config from application settings."""
        from src.tnse.telegram.client import TelegramClientConfig

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_API_ID": "99999",
                "TELEGRAM_API_HASH": "test_hash_value",
            },
        ):
            from src.tnse.core.config import get_settings

            get_settings.cache_clear()
            settings = get_settings()

            config = TelegramClientConfig.from_settings(settings)
            assert config.api_id == "99999"
            assert config.api_hash == "test_hash_value"


class TestTelegramClient:
    """Tests for the TelegramClient abstraction."""

    def test_client_is_abstract(self):
        """Test that TelegramClient is an abstract base class."""
        from src.tnse.telegram.client import TelegramClient

        with pytest.raises(TypeError):
            TelegramClient()

    def test_client_defines_connect_method(self):
        """Test that client defines an abstract connect method."""
        from src.tnse.telegram.client import TelegramClient

        assert hasattr(TelegramClient, "connect")
        assert asyncio.iscoroutinefunction(getattr(TelegramClient, "connect", None))

    def test_client_defines_disconnect_method(self):
        """Test that client defines an abstract disconnect method."""
        from src.tnse.telegram.client import TelegramClient

        assert hasattr(TelegramClient, "disconnect")
        assert asyncio.iscoroutinefunction(getattr(TelegramClient, "disconnect", None))

    def test_client_defines_is_connected_property(self):
        """Test that client defines an is_connected property."""
        from src.tnse.telegram.client import TelegramClient

        assert hasattr(TelegramClient, "is_connected")

    def test_client_defines_get_channel_method(self):
        """Test that client defines a get_channel method."""
        from src.tnse.telegram.client import TelegramClient

        assert hasattr(TelegramClient, "get_channel")
        assert asyncio.iscoroutinefunction(getattr(TelegramClient, "get_channel", None))

    def test_client_defines_get_messages_method(self):
        """Test that client defines a get_messages method."""
        from src.tnse.telegram.client import TelegramClient

        assert hasattr(TelegramClient, "get_messages")
        assert asyncio.iscoroutinefunction(getattr(TelegramClient, "get_messages", None))


class TestTelethonClient:
    """Tests for the TelethonClient implementation."""

    @pytest.fixture
    def client_config(self) -> Any:
        """Provide a test client configuration."""
        from src.tnse.telegram.client import TelegramClientConfig

        return TelegramClientConfig(
            api_id="12345",
            api_hash="test_hash",
            session_name="test_session",
        )

    def test_telethon_client_implements_telegram_client(self, client_config: Any):
        """Test that TelethonClient implements TelegramClient interface."""
        from src.tnse.telegram.client import TelegramClient, TelethonClient

        client = TelethonClient(client_config)
        assert isinstance(client, TelegramClient)

    def test_telethon_client_stores_config(self, client_config: Any):
        """Test that TelethonClient stores the configuration."""
        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)
        assert client.config == client_config

    def test_telethon_client_not_connected_initially(self, client_config: Any):
        """Test that TelethonClient is not connected initially."""
        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_telethon_client_connect(self, client_config: Any):
        """Test that TelethonClient can connect."""
        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)

        with patch.object(client, "_client") as mock_client:
            mock_client.connect = AsyncMock()
            mock_client.is_connected = MagicMock(return_value=True)

            await client.connect()

            mock_client.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_telethon_client_disconnect(self, client_config: Any):
        """Test that TelethonClient can disconnect."""
        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)

        with patch.object(client, "_client") as mock_client:
            mock_client.disconnect = AsyncMock()

            await client.disconnect()

            mock_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_telethon_client_context_manager(self, client_config: Any):
        """Test that TelethonClient can be used as async context manager."""
        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)

        with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(
                client, "disconnect", new_callable=AsyncMock
            ) as mock_disconnect:
                async with client:
                    mock_connect.assert_awaited_once()

                mock_disconnect.assert_awaited_once()


class TestChannelInfo:
    """Tests for the ChannelInfo dataclass."""

    def test_channel_info_has_required_fields(self):
        """Test that ChannelInfo has all required fields."""
        from src.tnse.telegram.client import ChannelInfo

        info = ChannelInfo(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            is_public=True,
        )
        assert info.telegram_id == 123456789
        assert info.username == "test_channel"
        assert info.title == "Test Channel"
        assert info.subscriber_count == 1000
        assert info.is_public is True

    def test_channel_info_optional_fields(self):
        """Test that ChannelInfo has optional fields with defaults."""
        from src.tnse.telegram.client import ChannelInfo

        info = ChannelInfo(
            telegram_id=123456789,
            username="test_channel",
            title="Test Channel",
            subscriber_count=1000,
            is_public=True,
        )
        assert info.description is None
        assert info.photo_url is None
        assert info.invite_link is None


class TestMessageInfo:
    """Tests for the MessageInfo dataclass."""

    def test_message_info_has_required_fields(self):
        """Test that MessageInfo has all required fields."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        info = MessageInfo(
            message_id=12345,
            channel_id=123456789,
            text="Test message content",
            date=now,
        )
        assert info.message_id == 12345
        assert info.channel_id == 123456789
        assert info.text == "Test message content"
        assert info.date == now

    def test_message_info_has_engagement_fields(self):
        """Test that MessageInfo has engagement-related fields."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        info = MessageInfo(
            message_id=12345,
            channel_id=123456789,
            text="Test message",
            date=now,
            views=5000,
            forwards=100,
            replies=50,
            reactions={"thumbs_up": 150, "heart": 89, "fire": 34},
        )
        assert info.views == 5000
        assert info.forwards == 100
        assert info.replies == 50
        assert info.reactions == {"thumbs_up": 150, "heart": 89, "fire": 34}

    def test_message_info_has_media_fields(self):
        """Test that MessageInfo has media-related fields."""
        from src.tnse.telegram.client import MediaInfo, MessageInfo

        now = datetime.now(timezone.utc)
        media = MediaInfo(
            media_type="photo",
            file_id="ABC123",
            file_size=1024,
        )
        info = MessageInfo(
            message_id=12345,
            channel_id=123456789,
            text="Test message with photo",
            date=now,
            media=[media],
        )
        assert len(info.media) == 1
        assert info.media[0].media_type == "photo"

    def test_message_info_forward_fields(self):
        """Test that MessageInfo has forward-related fields."""
        from src.tnse.telegram.client import MessageInfo

        now = datetime.now(timezone.utc)
        info = MessageInfo(
            message_id=12345,
            channel_id=123456789,
            text="Forwarded message",
            date=now,
            is_forwarded=True,
            forward_from_channel_id=987654321,
            forward_from_message_id=54321,
        )
        assert info.is_forwarded is True
        assert info.forward_from_channel_id == 987654321
        assert info.forward_from_message_id == 54321


class TestMediaInfo:
    """Tests for the MediaInfo dataclass."""

    def test_media_info_basic_fields(self):
        """Test that MediaInfo has basic fields."""
        from src.tnse.telegram.client import MediaInfo

        info = MediaInfo(
            media_type="photo",
            file_id="ABC123",
        )
        assert info.media_type == "photo"
        assert info.file_id == "ABC123"

    def test_media_info_size_and_dimensions(self):
        """Test that MediaInfo supports size and dimensions."""
        from src.tnse.telegram.client import MediaInfo

        info = MediaInfo(
            media_type="video",
            file_id="DEF456",
            file_size=10485760,
            width=1920,
            height=1080,
            duration=120,
        )
        assert info.file_size == 10485760
        assert info.width == 1920
        assert info.height == 1080
        assert info.duration == 120

    def test_media_info_mime_type(self):
        """Test that MediaInfo supports mime type."""
        from src.tnse.telegram.client import MediaInfo

        info = MediaInfo(
            media_type="document",
            file_id="GHI789",
            mime_type="application/pdf",
        )
        assert info.mime_type == "application/pdf"


class TestTelethonClientAutoConnect:
    """Tests for TelethonClient auto-connect behavior.

    WS-7.2: Fix channel validation connection bug.

    The TelethonClient should auto-connect when API methods are called
    if not already connected. This prevents the bug where get_channel()
    returns None simply because connect() was never called.
    """

    @pytest.fixture
    def client_config(self) -> Any:
        """Provide a test client configuration."""
        from src.tnse.telegram.client import TelegramClientConfig

        return TelegramClientConfig(
            api_id="12345",
            api_hash="test_hash",
            session_name="test_session",
        )

    @pytest.mark.asyncio
    async def test_get_channel_auto_connects_when_not_connected(
        self, client_config: Any
    ):
        """Test that get_channel auto-connects if client is not connected.

        This test reproduces the bug where get_channel returns None because
        the client was never explicitly connected.
        """
        from src.tnse.telegram.client import ChannelInfo, TelethonClient

        client = TelethonClient(client_config)

        # Initially not connected
        assert client.is_connected is False

        # Create a mock entity that get_entity would return
        mock_entity = MagicMock()
        mock_entity.id = 123456789
        mock_entity.username = "test_channel"
        mock_entity.title = "Test Channel"
        mock_entity.restricted = False

        # Create a mock full channel response
        mock_full_channel = MagicMock()
        mock_full_channel.full_chat.participants_count = 10000
        mock_full_channel.full_chat.about = "Test description"

        # Track if connect was called
        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True
            # Simulate what connect() does - set _connected based on is_connected()
            client._connected = True

        # Create mock _client that properly handles async calls
        # Must be AsyncMock so that client(request) is awaitable
        mock_telethon = AsyncMock()
        mock_telethon.get_entity = AsyncMock(return_value=mock_entity)
        mock_telethon.return_value = mock_full_channel

        # Patch the connect method to track calls and simulate connection
        with patch.object(client, "connect", side_effect=mock_connect):
            # Also need to patch _client for the API calls after connection
            with patch.object(client, "_client", mock_telethon):
                result = await client.get_channel("test_channel")

        # The client should have auto-connected
        assert connect_called is True

        # After connect(), _connected should be True
        assert client._connected is True

        # And should have returned channel info, not None
        assert result is not None
        assert isinstance(result, ChannelInfo)
        assert result.username == "test_channel"

    @pytest.mark.asyncio
    async def test_get_channel_does_not_reconnect_if_already_connected(
        self, client_config: Any
    ):
        """Test that get_channel does not reconnect if already connected."""
        from src.tnse.telegram.client import ChannelInfo, TelethonClient

        client = TelethonClient(client_config)

        # Create mock entity and full channel
        mock_entity = MagicMock()
        mock_entity.id = 123456789
        mock_entity.username = "test_channel"
        mock_entity.title = "Test Channel"
        mock_entity.restricted = False

        mock_full_channel = MagicMock()
        mock_full_channel.full_chat.participants_count = 10000
        mock_full_channel.full_chat.about = "Test description"

        # Pre-connect the client
        client._connected = True

        # Track if connect was called
        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True

        # Create mock _client that properly handles async calls
        mock_telethon = AsyncMock()
        mock_telethon.get_entity = AsyncMock(return_value=mock_entity)
        mock_telethon.return_value = mock_full_channel

        with patch.object(client, "connect", side_effect=mock_connect):
            with patch.object(client, "_client", mock_telethon):
                result = await client.get_channel("test_channel")

        # Should NOT have called connect again
        assert connect_called is False

        # But should still return channel info
        assert result is not None
        assert isinstance(result, ChannelInfo)

    @pytest.mark.asyncio
    async def test_get_messages_auto_connects_when_not_connected(
        self, client_config: Any
    ):
        """Test that get_messages auto-connects if client is not connected."""
        from datetime import datetime, timezone

        from src.tnse.telegram.client import TelethonClient

        client = TelethonClient(client_config)

        # Initially not connected
        assert client.is_connected is False

        # Create mock messages
        mock_message = MagicMock()
        mock_message.id = 12345
        mock_message.message = "Test message"
        mock_message.date = datetime.now(timezone.utc)
        mock_message.views = 1000
        mock_message.forwards = 10
        mock_message.replies = None
        mock_message.reactions = None
        mock_message.media = None
        mock_message.fwd_from = None

        # Track if connect was called
        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True
            client._connected = True

        with patch.object(client, "connect", side_effect=mock_connect):
            with patch.object(client, "_client") as mock_telethon:
                mock_telethon.get_messages = AsyncMock(return_value=[mock_message])

                result = await client.get_messages(channel_id=123456789, limit=10)

        # The client should have auto-connected
        assert connect_called is True

        # And should have returned messages, not empty list
        assert len(result) == 1
        assert result[0].message_id == 12345

"""
TNSE Telegram Bot Configuration

Provides configuration management for the Telegram bot.
Integrates with the main application settings system.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.tnse.core.config import get_settings


class BotTokenMissingError(Exception):
    """Raised when the Telegram bot token is not configured."""

    def __init__(self, message: str = "TELEGRAM_BOT_TOKEN environment variable is required"):
        self.message = message
        super().__init__(self.message)


@dataclass
class BotConfig:
    """
    Configuration for the Telegram bot.

    Attributes:
        token: The Telegram bot API token from BotFather.
        allowed_users: List of Telegram user IDs allowed to use the bot.
                      Empty list means open access (no restrictions).
        polling_mode: If True, use polling. If False, use webhooks.
        webhook_url: URL for webhook mode (required if polling_mode is False).
    """

    token: str
    allowed_users: list[int] = field(default_factory=list)
    polling_mode: bool = True
    webhook_url: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.token:
            raise ValueError("Bot token cannot be empty")

    def __repr__(self) -> str:
        """Return string representation with redacted token."""
        token_preview = self._redact_token()
        return (
            f"BotConfig(token='{token_preview}', "
            f"allowed_users={self.allowed_users}, "
            f"polling_mode={self.polling_mode}, "
            f"webhook_url={self.webhook_url})"
        )

    def __str__(self) -> str:
        """Return string representation with redacted token."""
        return self.__repr__()

    def _redact_token(self) -> str:
        """Redact the token for safe logging/display."""
        if not self.token:
            return "***"
        # Show first part (bot ID) and redact the hash
        parts = self.token.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:***REDACTED***"
        return "***REDACTED***"

    def is_user_allowed(self, user_id: int) -> bool:
        """
        Check if a user is allowed to use the bot.

        Args:
            user_id: The Telegram user ID to check.

        Returns:
            True if user is allowed, False otherwise.
            If allowed_users is empty, all users are allowed.
        """
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users


def create_bot_config() -> BotConfig:
    """
    Create a BotConfig instance from application settings.

    This function reads configuration from environment variables
    through the application's Settings class.

    Returns:
        BotConfig instance configured from environment.

    Raises:
        BotTokenMissingError: If TELEGRAM_BOT_TOKEN is not set.

    Example:
        >>> config = create_bot_config()
        >>> print(config.polling_mode)
        True
    """
    settings = get_settings()

    token = settings.telegram.bot_token
    if not token:
        raise BotTokenMissingError()

    allowed_users = settings.allowed_user_ids

    return BotConfig(
        token=token,
        allowed_users=allowed_users,
        polling_mode=True,  # Default to polling for simplicity
        webhook_url=None,
    )

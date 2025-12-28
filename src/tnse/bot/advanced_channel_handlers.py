"""
TNSE Telegram Bot Advanced Channel Management Command Handlers

Provides command handlers for bulk import and health monitoring operations.
Work Stream: WS-3.2 - Advanced Channel Management

Commands:
- /import - Bulk import channels from CSV, JSON, or TXT file
- /health - Show health status of all monitored channels
"""

import csv
import json
import re
from io import StringIO
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger
from src.tnse.bot.channel_handlers import extract_channel_username, format_subscriber_count

logger = get_logger(__name__)


# Type alias for handler functions
HandlerFunc = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]


# Supported file extensions and MIME types
SUPPORTED_EXTENSIONS = {".csv", ".json", ".txt"}
SUPPORTED_MIME_TYPES = {
    "text/csv",
    "application/json",
    "text/plain",
    "application/octet-stream",  # Sometimes sent for txt files
}


def parse_csv_channels(content: str) -> list[str]:
    """
    Parse channel list from CSV content.

    Expects a column named 'channel_url', 'channel', 'username', or similar.
    Falls back to first column if no matching header found.

    Args:
        content: CSV file content as string

    Returns:
        List of channel identifiers
    """
    channels = []
    reader = csv.reader(StringIO(content))

    # Try to detect header row
    try:
        header = next(reader)
        header_lower = [column.lower().strip() for column in header]

        # Find the channel column
        channel_column_index = 0
        for index, column_name in enumerate(header_lower):
            if any(keyword in column_name for keyword in ["channel", "url", "username", "link"]):
                channel_column_index = index
                break

        # Check if first row looks like data (starts with @ or t.me)
        first_value = header[channel_column_index].strip() if header else ""
        if first_value.startswith("@") or "t.me" in first_value:
            # First row is data, not header
            channels.append(first_value)

        # Parse remaining rows
        for row in reader:
            if row and len(row) > channel_column_index:
                value = row[channel_column_index].strip()
                if value and not value.startswith("#"):  # Skip comments
                    channels.append(value)

    except StopIteration:
        pass  # Empty file

    return channels


def parse_json_channels(content: str) -> list[str]:
    """
    Parse channel list from JSON content.

    Supports formats:
    - Array: ["@channel1", "@channel2"]
    - Object with channels key: {"channels": ["@channel1", "@channel2"]}

    Args:
        content: JSON file content as string

    Returns:
        List of channel identifiers
    """
    try:
        data = json.loads(content)

        # If it's a list, return it directly
        if isinstance(data, list):
            return [str(item).strip() for item in data if item]

        # If it's a dict, look for common keys
        if isinstance(data, dict):
            for key in ["channels", "channel_list", "usernames", "urls"]:
                if key in data and isinstance(data[key], list):
                    return [str(item).strip() for item in data[key] if item]

            # Try first list value found
            for value in data.values():
                if isinstance(value, list):
                    return [str(item).strip() for item in value if item]

    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON content")

    return []


def parse_txt_channels(content: str) -> list[str]:
    """
    Parse channel list from plain text content.

    One channel per line. Lines starting with # are treated as comments.
    Empty lines are skipped.

    Args:
        content: Plain text file content

    Returns:
        List of channel identifiers
    """
    channels = []

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Extract channel identifier (handle inline comments)
        if "#" in line:
            line = line.split("#")[0].strip()

        if line:
            channels.append(line)

    return channels


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.

    Args:
        filename: The filename to parse

    Returns:
        Lowercase file extension including the dot
    """
    if "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


async def import_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /import command.

    Imports multiple channels from an uploaded file (CSV, JSON, or TXT).
    Validates each channel and reports results.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    logger.info("Import command called", user_id=user_id)

    # Check for file attachment
    if not update.message.document:
        await update.message.reply_text(
            "Usage: /import (with file attachment)\n\n"
            "Please attach a file containing channel list.\n\n"
            "Supported formats:\n"
            "- CSV: One column with channel usernames or URLs\n"
            "- JSON: Array of channels or {\"channels\": [...]}\n"
            "- TXT: One channel per line\n\n"
            "Example CSV:\n"
            "channel_url\n"
            "@channel_one\n"
            "@channel_two\n"
            "https://t.me/channel_three"
        )
        return

    document = update.message.document
    filename = document.file_name or ""
    extension = get_file_extension(filename)
    mime_type = document.mime_type or ""

    logger.info(
        "Processing import file",
        user_id=user_id,
        filename=filename,
        extension=extension,
        mime_type=mime_type
    )

    # Validate file type
    if extension not in SUPPORTED_EXTENSIONS and mime_type not in SUPPORTED_MIME_TYPES:
        await update.message.reply_text(
            f"Unsupported file format: {extension or mime_type}\n\n"
            "Please upload a CSV, JSON, or TXT file."
        )
        return

    # Get channel service and database session from bot_data
    channel_service = context.bot_data.get("channel_service")
    db_session_factory = context.bot_data.get("db_session_factory")

    if not channel_service or not db_session_factory:
        await update.message.reply_text(
            "Import service is not available. Please try again later."
        )
        logger.error("Channel service or database not configured in bot_data")
        return

    # Download and parse the file
    try:
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode("utf-8")
    except Exception as error:
        await update.message.reply_text(
            "Error reading file. Please ensure it's a valid text file."
        )
        logger.error("Error reading import file", error=str(error))
        return

    # Parse channels based on file type
    channels = []
    if extension == ".csv" or mime_type == "text/csv":
        channels = parse_csv_channels(content)
    elif extension == ".json" or mime_type == "application/json":
        channels = parse_json_channels(content)
    else:  # .txt or plain text
        channels = parse_txt_channels(content)

    if not channels:
        await update.message.reply_text(
            "No channels found in the file.\n\n"
            "Please ensure the file contains valid channel usernames or URLs."
        )
        return

    # Send initial status message
    await update.message.reply_text(
        f"Processing {len(channels)} channels...\n"
        "This may take a moment."
    )

    # Process each channel
    added_count = 0
    skipped_count = 0
    failed_count = 0
    failed_channels = []

    from sqlalchemy import select
    from src.tnse.db.models import Channel

    session = db_session_factory()

    for channel_identifier in channels:
        username = extract_channel_username(channel_identifier)

        if not username:
            failed_count += 1
            failed_channels.append((channel_identifier, "Invalid format"))
            continue

        try:
            # Validate the channel
            validation_result = await channel_service.validate_channel(username)

            if not validation_result.is_valid:
                failed_count += 1
                failed_channels.append((username, validation_result.error or "Validation failed"))
                continue

            channel_info = validation_result.channel_info

            # Check if channel already exists
            query = select(Channel).where(
                (Channel.username == channel_info.username) |
                (Channel.telegram_id == channel_info.telegram_id)
            )
            result = await session.execute(query)
            existing_channel = result.scalar_one_or_none()

            if existing_channel:
                skipped_count += 1
                continue

            # Create new channel record
            new_channel = Channel(
                telegram_id=channel_info.telegram_id,
                username=channel_info.username,
                title=channel_info.title,
                description=channel_info.description,
                subscriber_count=channel_info.subscriber_count,
                photo_url=channel_info.photo_url,
                invite_link=channel_info.invite_link,
                is_active=True,
            )

            session.add(new_channel)
            await session.commit()
            added_count += 1

        except Exception as error:
            failed_count += 1
            failed_channels.append((username, str(error)))
            logger.error(
                "Error processing channel during import",
                username=username,
                error=str(error)
            )

    # Build result message
    message_lines = [
        "Import completed!\n",
        f"Added: {added_count} channels",
        f"Skipped (already exist): {skipped_count} channels",
        f"Failed: {failed_count} channels",
    ]

    if failed_channels and len(failed_channels) <= 10:
        message_lines.append("\nFailed channels:")
        for channel_name, error in failed_channels[:10]:
            message_lines.append(f"  - @{channel_name}: {error}")
    elif failed_channels:
        message_lines.append(f"\n(Showing first 10 of {len(failed_channels)} failures)")
        for channel_name, error in failed_channels[:10]:
            message_lines.append(f"  - @{channel_name}: {error}")

    await update.message.reply_text("\n".join(message_lines))

    logger.info(
        "Import completed",
        user_id=user_id,
        added=added_count,
        skipped=skipped_count,
        failed=failed_count
    )


async def health_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /health command.

    Shows health status of all monitored channels including:
    - Current status (healthy, rate_limited, inaccessible, removed)
    - Last check time
    - Any error messages

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    logger.info("Health command called", user_id=user_id)

    # Get database session from bot_data
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        await update.message.reply_text(
            "Database is not available. Please try again later."
        )
        logger.error("Database session factory not configured in bot_data")
        return

    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.tnse.db.models import Channel

        session = db_session_factory()

        # Get all channels with health logs
        query = (
            select(Channel)
            .options(selectinload(Channel.health_logs))
            .order_by(Channel.title)
        )
        result = await session.execute(query)
        channels = result.scalars().all()

        if not channels:
            await update.message.reply_text(
                "No channels are currently being monitored.\n\n"
                "Use /addchannel @username to add a channel."
            )
            logger.info("No channels found for health check")
            return

        # Count channels by status
        healthy_count = 0
        warning_count = 0
        error_count = 0
        unknown_count = 0

        channel_statuses = []

        for channel in channels:
            # Get latest health log
            if channel.health_logs:
                sorted_logs = sorted(
                    channel.health_logs,
                    key=lambda log: log.checked_at,
                    reverse=True
                )
                latest_log = sorted_logs[0]
                status = latest_log.status
                last_check = latest_log.checked_at.strftime("%Y-%m-%d %H:%M UTC")
                error_message = latest_log.error_message
            else:
                status = "unknown"
                last_check = "Never"
                error_message = None

            # Categorize status
            if status == "healthy":
                healthy_count += 1
                status_indicator = "[OK]"
            elif status in ("rate_limited",):
                warning_count += 1
                status_indicator = "[WARNING]"
            elif status in ("inaccessible", "removed"):
                error_count += 1
                status_indicator = "[ERROR]"
            else:
                unknown_count += 1
                status_indicator = "[PENDING]"

            channel_statuses.append({
                "username": channel.username,
                "title": channel.title,
                "status": status,
                "status_indicator": status_indicator,
                "last_check": last_check,
                "error_message": error_message,
            })

        # Build message
        total_count = len(channels)
        message_lines = [
            "Channel Health Status\n",
            f"Total: {total_count} channels",
            f"Healthy: {healthy_count} | Warnings: {warning_count} | Errors: {error_count} | Pending: {unknown_count}",
            "",
        ]

        # Show channels with issues first
        issue_channels = [
            status for status in channel_statuses
            if status["status"] not in ("healthy", "unknown")
        ]

        if issue_channels:
            message_lines.append("Issues:")
            for status in issue_channels:
                message_lines.append(
                    f"  {status['status_indicator']} @{status['username']}"
                )
                message_lines.append(
                    f"     Status: {status['status'].replace('_', ' ').title()}"
                )
                if status["error_message"]:
                    error_preview = status["error_message"][:50]
                    if len(status["error_message"]) > 50:
                        error_preview += "..."
                    message_lines.append(f"     Error: {error_preview}")
                message_lines.append(f"     Last check: {status['last_check']}")
            message_lines.append("")

        # Show healthy channels summary
        healthy_channels = [
            status for status in channel_statuses
            if status["status"] == "healthy"
        ]

        if healthy_channels:
            message_lines.append(f"Healthy ({len(healthy_channels)}):")
            for status in healthy_channels[:10]:  # Limit to 10
                message_lines.append(
                    f"  [OK] @{status['username']} - Last: {status['last_check']}"
                )
            if len(healthy_channels) > 10:
                message_lines.append(f"  ... and {len(healthy_channels) - 10} more")

        # Show unchecked channels
        unchecked_channels = [
            status for status in channel_statuses
            if status["status"] == "unknown"
        ]

        if unchecked_channels:
            message_lines.append(f"\nNever checked ({len(unchecked_channels)}):")
            for status in unchecked_channels[:5]:  # Limit to 5
                message_lines.append(f"  [PENDING] @{status['username']}")
            if len(unchecked_channels) > 5:
                message_lines.append(f"  ... and {len(unchecked_channels) - 5} more")

        await update.message.reply_text("\n".join(message_lines))

        logger.info(
            "Health check completed",
            total=total_count,
            healthy=healthy_count,
            warnings=warning_count,
            errors=error_count,
            unknown=unknown_count
        )

    except Exception as error:
        await update.message.reply_text(
            "Error retrieving health status.\n\n"
            "Please try again later."
        )
        logger.error(
            "Database error during health check",
            error=str(error)
        )

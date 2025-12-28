"""
TNSE Telegram Bot Export Command Handlers

Provides command handlers for exporting search results to files.

Work Stream: WS-2.5 - Export Functionality

Requirements addressed:
- REQ-RP-005: System MUST support export to CSV, JSON, and formatted text
- REQ-TB-003: Telegram bot MUST format results with clickable links
"""

import io
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger
from src.tnse.export.service import ExportService
from src.tnse.search.service import SearchResult

logger = get_logger(__name__)

# Valid export formats
VALID_FORMATS = {"csv", "json"}


async def export_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle the /export command.

    Exports the last search results to a file (CSV or JSON) and sends it
    to the user via Telegram.

    Usage:
        /export         - Export as CSV (default)
        /export csv     - Export as CSV
        /export json    - Export as JSON
        /export help    - Show usage information

    Args:
        update: The Telegram update object.
        context: The callback context containing user data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Get arguments
    args = context.args or []

    # Check for help argument
    if args and args[0].lower() == "help":
        await _send_usage_help(update)
        logger.info(
            "User requested export help",
            user_id=user_id,
        )
        return

    # Determine export format
    format_arg = args[0].lower() if args else "csv"

    # Validate format
    if format_arg not in VALID_FORMATS:
        await update.message.reply_text(
            f"Invalid export format: '{format_arg}'\n\n"
            f"Valid formats are: csv, json\n\n"
            f"Usage: /export [format]\n"
            f"Example: /export csv"
        )
        logger.warning(
            "User requested invalid export format",
            user_id=user_id,
            format=format_arg,
        )
        return

    # Get last search results from user data
    user_data = context.user_data or {}
    last_results = user_data.get("last_search_results")
    last_query = user_data.get("last_search_query", "search")

    # Check if there are results to export
    if last_results is None:
        await update.message.reply_text(
            "No results to export.\n\n"
            "Please perform a search first using /search <query>, "
            "then use /export to download the results."
        )
        logger.info(
            "User tried to export with no previous search",
            user_id=user_id,
        )
        return

    if not last_results:
        await update.message.reply_text(
            "No results to export.\n\n"
            "Your last search returned no results. "
            "Try a different search query."
        )
        logger.info(
            "User tried to export empty results",
            user_id=user_id,
        )
        return

    # Convert mock results to SearchResult if needed (for testing compatibility)
    results = _ensure_search_results(last_results)

    # Export using ExportService
    export_service = ExportService()

    try:
        if format_arg == "csv":
            file_bytes = export_service.export_to_csv_bytes(results)
        else:  # json
            json_string = export_service.export_to_json(results, query=last_query)
            file_bytes = json_string.encode("utf-8")

        filename = export_service.generate_filename(format_arg, query=last_query)

        # Create file-like object for Telegram
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = filename

        # Send file to user
        result_count = len(results)
        caption = f"Exported {result_count} result{'s' if result_count != 1 else ''}"
        if last_query:
            caption += f" for '{last_query}'"

        await update.message.reply_document(
            document=file_obj,
            filename=filename,
            caption=caption,
        )

        logger.info(
            "User exported search results",
            user_id=user_id,
            format=format_arg,
            result_count=result_count,
            query=last_query,
        )

    except Exception as error:
        logger.error(
            "Error exporting search results",
            user_id=user_id,
            error=str(error),
            exc_info=error,
        )
        await update.message.reply_text(
            "An error occurred while exporting your results. "
            "Please try again later."
        )


async def _send_usage_help(update: Update) -> None:
    """Send usage help message for export command."""
    help_message = """Export Command - Usage

The /export command exports your last search results to a file.

Usage:
  /export        - Export as CSV (default)
  /export csv    - Export as CSV file
  /export json   - Export as JSON file
  /export help   - Show this help message

The exported file will include:
- Channel information (username, title)
- Post content preview
- View count and engagement metrics
- Direct links to original Telegram posts

Note: You must perform a search with /search <query> before exporting."""

    await update.message.reply_text(help_message)


def _ensure_search_results(results: list[Any]) -> list[SearchResult]:
    """
    Ensure results are SearchResult objects.

    This handles both actual SearchResult objects and mock objects
    that have the same attributes (for testing compatibility).

    Args:
        results: List of results (may be SearchResult or mock objects).

    Returns:
        List of SearchResult objects.
    """
    if not results:
        return []

    # If already SearchResult objects, return as-is
    if isinstance(results[0], SearchResult):
        return results

    # Otherwise, try to convert mock objects to SearchResult
    converted = []
    for result in results:
        try:
            search_result = SearchResult(
                post_id=getattr(result, "post_id", ""),
                channel_id=getattr(result, "channel_id", ""),
                channel_username=getattr(result, "channel_username", ""),
                channel_title=getattr(result, "channel_title", ""),
                text_content=getattr(result, "text_content", ""),
                published_at=getattr(result, "published_at", None),
                view_count=getattr(result, "view_count", 0),
                reaction_score=getattr(result, "reaction_score", 0.0),
                relative_engagement=getattr(result, "relative_engagement", 0.0),
                telegram_message_id=getattr(result, "telegram_message_id", 0),
            )
            converted.append(search_result)
        except Exception:
            # If conversion fails, try to use the object as-is
            converted.append(result)

    return converted

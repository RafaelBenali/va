"""
TNSE Telegram Bot Search Command Handlers

Provides command handlers for search operations.
Work Stream: WS-2.4 - Search Bot Commands

Commands:
- /search <query> - Search for news by keyword

Requirements addressed:
- /search returns ranked results
- Pagination works via buttons
- Metrics displayed clearly
- Links work
- Telegram message length limits (4096 chars)

Python 3.10+ Modernization (WS-6.8):
- Uses X | None instead of Optional[X] for union types
"""

import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger
from src.tnse.search.service import SearchResult

logger = get_logger(__name__)

# Type alias for handler functions
HandlerFunc = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]

# Telegram message character limit
TELEGRAM_MESSAGE_LIMIT = 4096

# Default page size for search results
DEFAULT_PAGE_SIZE = 5

# Emoji mapping for reactions display
EMOJI_DISPLAY_MAP = {
    "thumbs_up": "\U0001F44D",  # Thumbs up
    "thumbs_down": "\U0001F44E",  # Thumbs down
    "heart": "\u2764\ufe0f",  # Red heart
    "fire": "\U0001F525",  # Fire
    "clap": "\U0001F44F",  # Clapping hands
    "thinking": "\U0001F914",  # Thinking face
    "party": "\U0001F389",  # Party popper
    "cry": "\U0001F62D",  # Crying face
    "eyes": "\U0001F440",  # Eyes
    "poop": "\U0001F4A9",  # Poop
}

# Callback data prefix for search pagination
SEARCH_CALLBACK_PREFIX = "search:"


@dataclass
class SearchFormatter:
    """Formats search results for Telegram display.

    Provides methods to format individual components of search results
    (views, time, reactions, previews) and complete result pages.

    Attributes:
        max_preview_length: Maximum length for text previews (default: 100).
        max_results_per_message: Max results before truncating (default: 5).
    """

    max_preview_length: int = 100
    max_results_per_message: int = DEFAULT_PAGE_SIZE

    def format_view_count(self, view_count: int) -> str:
        """Format view count for display (e.g., 12.5K, 1.5M).

        Args:
            view_count: Number of views.

        Returns:
            Formatted string with K or M suffix for large numbers.
        """
        if view_count >= 1_000_000:
            return f"{view_count / 1_000_000:.1f}M"
        elif view_count >= 1_000:
            return f"{view_count / 1_000:.1f}K"
        return str(view_count)

    def format_time_ago(
        self,
        published_at: datetime,
        reference_time: datetime | None = None,
    ) -> str:
        """Format time as relative (e.g., 2h ago, 30m ago).

        Args:
            published_at: When the post was published.
            reference_time: Reference time for calculation (default: now).

        Returns:
            Formatted relative time string.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Handle naive datetime by treating as UTC
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        time_diff = reference_time - published_at
        total_seconds = time_diff.total_seconds()

        if total_seconds < 0:
            return "just now"

        minutes = int(total_seconds / 60)
        hours = int(total_seconds / 3600)
        days = int(total_seconds / 86400)

        if days > 0:
            return f"{days}d ago"
        elif hours > 0:
            return f"{hours}h ago"
        elif minutes > 0:
            return f"{minutes}m ago"
        else:
            return "just now"

    def format_reactions(self, reactions: dict[str, int] | None) -> str:
        """Format reaction counts with emoji labels.

        Args:
            reactions: Dictionary mapping emoji names to counts.

        Returns:
            Formatted reaction string or empty string if no reactions.
        """
        if not reactions:
            return ""

        parts = []
        for emoji_name, count in reactions.items():
            if count > 0:
                emoji_display = EMOJI_DISPLAY_MAP.get(emoji_name, emoji_name)
                parts.append(f"{emoji_display} {count}")

        return " | ".join(parts)

    def format_score(self, score: float) -> str:
        """Format combined ranking score.

        Args:
            score: The ranking score to format.

        Returns:
            Score formatted to 2 decimal places.
        """
        return f"{score:.2f}"

    def format_preview(self, text_content: str) -> str:
        """Format text preview with truncation.

        Args:
            text_content: Full text content.

        Returns:
            Truncated preview if needed, with ellipsis.
        """
        if not text_content:
            return ""

        # Remove multiple newlines and extra whitespace
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        if len(text_content) <= self.max_preview_length:
            return text_content

        return text_content[: self.max_preview_length - 3] + "..."

    def format_result(
        self,
        result: SearchResult,
        index: int,
        reference_time: datetime | None = None,
        reactions: dict[str, int] | None = None,
    ) -> str:
        """Format a single search result for display.

        Args:
            result: The SearchResult to format.
            index: Display index (1-based).
            reference_time: Reference time for relative time display.
            reactions: Optional reaction counts for this result.

        Returns:
            Formatted result string.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        lines = []

        # Header line: index, channel name, views
        view_display = self.format_view_count(result.view_count)
        lines.append(f"{index}. [{result.channel_title}] - {view_display} views")

        # Preview line
        preview = self.format_preview(result.text_content)
        if preview:
            lines.append(f"   Preview: {preview}")

        # Reactions line (if available)
        if reactions:
            reaction_display = self.format_reactions(reactions)
            if reaction_display:
                lines.append(f"   Reactions: {reaction_display}")

        # Score and time line
        score_display = self.format_score(result.relative_engagement)
        time_display = self.format_time_ago(result.published_at, reference_time)
        lines.append(f"   Score: {score_display} | {time_display}")

        # Link line
        lines.append(f"   [View Post]({result.telegram_link})")

        return "\n".join(lines)

    def format_results_page(
        self,
        query: str,
        results: list[SearchResult],
        total_count: int,
        page: int,
        page_size: int,
        reference_time: datetime | None = None,
        reactions_map: dict[str, dict[str, int]] | None = None,
    ) -> str:
        """Format a page of search results.

        Args:
            query: The search query.
            results: List of SearchResult objects for this page.
            total_count: Total number of results across all pages.
            page: Current page number (1-based).
            page_size: Number of results per page.
            reference_time: Reference time for relative time display.
            reactions_map: Optional map of post_id to reaction counts.

        Returns:
            Formatted results page string, truncated to fit Telegram limits.
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        if reactions_map is None:
            reactions_map = {}

        # Calculate range for display
        start_index = (page - 1) * page_size + 1
        end_index = min(start_index + len(results) - 1, total_count)

        # Build header
        lines = [
            f'Search: "{query}"',
            f"Found {total_count} results (showing {start_index}-{end_index})",
            "",
        ]

        # Add each result
        current_length = sum(len(line) + 1 for line in lines)

        for display_index, result in enumerate(results, start=start_index):
            reactions = reactions_map.get(result.post_id)
            formatted_result = self.format_result(
                result=result,
                index=display_index,
                reference_time=reference_time,
                reactions=reactions,
            )

            # Check if adding this result would exceed limit
            result_length = len(formatted_result) + 2  # +2 for newlines
            if current_length + result_length > TELEGRAM_MESSAGE_LIMIT - 100:
                # Leave room for pagination info
                lines.append("")
                lines.append("... (results truncated to fit message limit)")
                break

            lines.append(formatted_result)
            lines.append("")  # Blank line between results
            current_length += result_length + 1

        return "\n".join(lines).strip()


def create_pagination_keyboard(
    query: str,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Create an inline keyboard for pagination.

    Args:
        query: The search query (for callback data).
        current_page: Current page number (1-based).
        total_pages: Total number of pages.

    Returns:
        InlineKeyboardMarkup with navigation buttons.
    """
    buttons = []

    # Previous button
    if current_page > 1:
        prev_callback = f"{SEARCH_CALLBACK_PREFIX}{query}:{current_page - 1}"
        buttons.append(
            InlineKeyboardButton("<< Prev", callback_data=prev_callback)
        )

    # Page indicator
    page_text = f"{current_page}/{total_pages}"
    buttons.append(
        InlineKeyboardButton(page_text, callback_data="noop")
    )

    # Next button
    if current_page < total_pages:
        next_callback = f"{SEARCH_CALLBACK_PREFIX}{query}:{current_page + 1}"
        buttons.append(
            InlineKeyboardButton("Next >>", callback_data=next_callback)
        )

    return InlineKeyboardMarkup([buttons])


async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /search command.

    Searches for posts matching the query and displays results
    with pagination.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    # Check for query argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /search <query>\n\n"
            "Example: /search corruption news"
        )
        logger.info("search called without arguments", user_id=user_id)
        return

    # Combine all arguments into search query
    query = " ".join(context.args)

    logger.info(
        "Searching",
        user_id=user_id,
        query=query,
    )

    # Send typing indicator to show progress
    if chat_id:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Get search service from bot_data
    search_service = context.bot_data.get("search_service")

    if not search_service:
        await update.message.reply_text(
            "Search service is not available. Please try again later."
        )
        logger.error("Search service not configured in bot_data")
        return

    try:
        # Execute search
        results = await search_service.search(
            query=query,
            hours=24,
            limit=100,  # Get more results for pagination
            offset=0,
        )

        if not results:
            await update.message.reply_text(
                f'Search: "{query}"\n\n'
                f"No results found. Try different keywords or check back later."
            )
            logger.info("No search results", query=query)
            return

        # Format first page of results
        page_size = DEFAULT_PAGE_SIZE
        total_count = len(results)
        total_pages = (total_count + page_size - 1) // page_size
        page_results = results[:page_size]

        formatter = SearchFormatter()
        formatted_message = formatter.format_results_page(
            query=query,
            results=page_results,
            total_count=total_count,
            page=1,
            page_size=page_size,
        )

        # Create pagination keyboard if multiple pages
        reply_markup = None
        if total_pages > 1:
            reply_markup = create_pagination_keyboard(
                query=query,
                current_page=1,
                total_pages=total_pages,
            )

        await update.message.reply_text(
            formatted_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # Store results in user_data for pagination
        context.user_data["last_search_query"] = query
        context.user_data["last_search_results"] = results

        logger.info(
            "Search completed",
            query=query,
            result_count=total_count,
            pages=total_pages,
        )

    except Exception as error:
        await update.message.reply_text(
            f"Error performing search.\n\n"
            f"Please try again later."
        )
        logger.error(
            "Search error",
            query=query,
            error=str(error),
            exc_info=error,
        )


async def pagination_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle pagination callback queries.

    Updates the search results message to show a different page.

    Args:
        update: The Telegram update object.
        context: The callback context.
    """
    callback_query = update.callback_query

    # Always answer the callback to remove loading state
    await callback_query.answer()

    callback_data = callback_query.data

    # Check if this is a search pagination callback
    if not callback_data.startswith(SEARCH_CALLBACK_PREFIX):
        return

    # Handle noop callback (page indicator button)
    if callback_data == "noop":
        return

    # Parse callback data: search:query:page
    try:
        parts = callback_data[len(SEARCH_CALLBACK_PREFIX) :].rsplit(":", 1)
        if len(parts) != 2:
            logger.warning("Invalid pagination callback data", data=callback_data)
            return

        query = parts[0]
        page = int(parts[1])
    except (ValueError, IndexError) as error:
        logger.warning(
            "Failed to parse pagination callback",
            data=callback_data,
            error=str(error),
        )
        return

    # Get search service from bot_data
    search_service = context.bot_data.get("search_service")

    if not search_service:
        await callback_query.edit_message_text(
            "Search service is not available. Please try again."
        )
        return

    try:
        # Re-execute search (or use cached results)
        cached_query = context.user_data.get("last_search_query")
        cached_results = context.user_data.get("last_search_results")

        if cached_query == query and cached_results:
            results = cached_results
        else:
            # Need to re-execute search
            results = await search_service.search(
                query=query,
                hours=24,
                limit=100,
                offset=0,
            )
            context.user_data["last_search_query"] = query
            context.user_data["last_search_results"] = results

        if not results:
            await callback_query.edit_message_text(
                f'Search: "{query}"\n\n'
                f"No results found."
            )
            return

        # Calculate page results
        page_size = DEFAULT_PAGE_SIZE
        total_count = len(results)
        total_pages = (total_count + page_size - 1) // page_size

        # Ensure page is valid
        page = max(1, min(page, total_pages))

        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, total_count)
        page_results = results[start_index:end_index]

        # Format results
        formatter = SearchFormatter()
        formatted_message = formatter.format_results_page(
            query=query,
            results=page_results,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

        # Create pagination keyboard
        reply_markup = create_pagination_keyboard(
            query=query,
            current_page=page,
            total_pages=total_pages,
        )

        await callback_query.edit_message_text(
            formatted_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        logger.info(
            "Pagination updated",
            query=query,
            page=page,
            total_pages=total_pages,
        )

    except Exception as error:
        logger.error(
            "Pagination error",
            query=query,
            page=page,
            error=str(error),
            exc_info=error,
        )
        await callback_query.edit_message_text(
            "Error loading results. Please try the search again."
        )

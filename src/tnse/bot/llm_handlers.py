"""
TNSE Telegram Bot LLM Command Handlers (WS-5.6)

Provides command handlers for LLM features:
- /mode - Show/switch between LLM and metrics-only modes
- /enrich - Manually trigger post enrichment for a channel
- /stats llm - Show LLM usage statistics

Commands:
- /mode - Show current mode (llm/metrics)
- /mode llm - Switch to LLM-enhanced search
- /mode metrics - Switch to metrics-only search
- /enrich @channel - Manually trigger enrichment for a channel
- /stats llm - Show LLM usage statistics

Requirements addressed (WS-5.6):
- Users can switch between LLM and metrics mode
- Search results display enrichment metadata when available
- Filter syntax works for category/sentiment
- Help text documents new commands
- Commands registered in bot menu

Python 3.10+ Modernization (WS-6.3):
- Uses X | None instead of Optional[X] for union types
"""

from collections.abc import Callable, Coroutine
from typing import Any, TypeAlias

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger

logger = get_logger(__name__)

# Type alias for handler functions
HandlerFunc: TypeAlias = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]

# Valid search modes
VALID_MODES = ("llm", "metrics")

# Default search mode (metrics-only, no LLM needed)
DEFAULT_MODE = "metrics"


def get_current_mode(bot_data: dict[str, Any]) -> str:
    """Get the current search mode from bot_data.

    Args:
        bot_data: The bot's data dictionary.

    Returns:
        The current mode ('llm' or 'metrics').
    """
    return bot_data.get("llm_mode", DEFAULT_MODE)


def set_current_mode(bot_data: dict[str, Any], mode: str) -> None:
    """Set the current search mode in bot_data.

    Args:
        bot_data: The bot's data dictionary.
        mode: The mode to set ('llm' or 'metrics').
    """
    bot_data["llm_mode"] = mode


async def mode_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /mode command.

    Shows the current search mode or switches between LLM and metrics modes.

    Usage:
        /mode - Show current mode
        /mode llm - Switch to LLM-enhanced search
        /mode metrics - Switch to metrics-only search
        /m - Alias for /mode

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Get current mode
    current_mode = get_current_mode(context.bot_data)

    # Check if user wants to switch mode
    if context.args and len(context.args) > 0:
        requested_mode = context.args[0].lower()

        if requested_mode not in VALID_MODES:
            await update.message.reply_text(
                f"Invalid mode: {requested_mode}\n\n"
                f"Valid modes:\n"
                f"  - llm: LLM-enhanced search with category/sentiment\n"
                f"  - metrics: Metrics-only search (faster, no API costs)\n\n"
                f"Usage: /mode <llm|metrics>"
            )
            logger.info(
                "Invalid mode requested",
                user_id=user_id,
                requested_mode=requested_mode,
            )
            return

        # Switch mode
        set_current_mode(context.bot_data, requested_mode)
        current_mode = requested_mode

        logger.info(
            "Mode switched",
            user_id=user_id,
            new_mode=current_mode,
        )

        await update.message.reply_text(
            f"Mode switched to: {current_mode}\n\n"
            f"{'LLM-enhanced search enabled. Results will include category and sentiment.' if current_mode == 'llm' else 'Metrics-only mode. Fast search without LLM API calls.'}"
        )
        return

    # Show current mode status
    enrichment_service = context.bot_data.get("enrichment_service")
    llm_status = "available" if enrichment_service else "not configured"

    message = (
        f"Current Search Mode: {current_mode}\n\n"
        f"LLM Service: {llm_status}\n\n"
        f"Available modes:\n"
        f"  - llm: LLM-enhanced search with category, sentiment, implicit keywords\n"
        f"  - metrics: Metrics-only search (faster, no API costs)\n\n"
        f"Usage: /mode <llm|metrics>"
    )

    await update.message.reply_text(message)
    logger.info(
        "Mode status displayed",
        user_id=user_id,
        current_mode=current_mode,
        llm_status=llm_status,
    )


async def enrich_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /enrich command.

    Manually triggers LLM enrichment for posts from a specific channel.

    Usage:
        /enrich @channel - Enrich posts from the specified channel

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None

    # Check for channel argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /enrich @channel\n\n"
            "This command manually triggers LLM enrichment for posts "
            "from the specified channel.\n\n"
            "Example: /enrich @telegram"
        )
        logger.info("enrich called without arguments", user_id=user_id)
        return

    channel_arg = context.args[0]

    # Show typing indicator
    if chat_id:
        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass  # Ignore typing indicator failures

    # Check if enrichment service is available
    enrichment_service = context.bot_data.get("enrichment_service")
    db_session_factory = context.bot_data.get("db_session_factory")

    if not enrichment_service or not db_session_factory:
        await update.message.reply_text(
            "Enrichment service is not available.\n\n"
            "The LLM enrichment service is not configured. "
            "Please contact the administrator to check:\n"
            "  - GROQ_API_KEY is set\n"
            "  - GROQ_ENABLED is true\n"
            "  - Database is properly configured"
        )
        logger.warning(
            "Enrichment service not configured",
            user_id=user_id,
            channel=channel_arg,
        )
        return

    try:
        # Trigger enrichment task via Celery
        from src.tnse.llm import tasks

        # Parse channel username (remove @ prefix if present)
        channel_username = channel_arg.lstrip("@")

        # Queue the enrichment task
        tasks.enrich_channel_posts.delay(channel_username=channel_username)

        await update.message.reply_text(
            f"Enrichment queued for @{channel_username}\n\n"
            f"Posts from this channel will be enriched in the background. "
            f"This may take a few minutes depending on the number of posts.\n\n"
            f"Use /stats llm to check enrichment progress."
        )

        logger.info(
            "Enrichment task queued",
            user_id=user_id,
            channel=channel_username,
        )

    except ImportError:
        await update.message.reply_text(
            "Enrichment tasks are not available.\n\n"
            "The Celery task queue is not configured properly. "
            "Please contact the administrator."
        )
        logger.error(
            "Failed to import enrichment tasks",
            user_id=user_id,
        )

    except Exception as error:
        await update.message.reply_text(
            f"Error queueing enrichment task.\n\n"
            f"Please try again later or contact the administrator."
        )
        logger.error(
            "Enrichment command error",
            user_id=user_id,
            channel=channel_arg,
            error=str(error),
            exc_info=error,
        )


async def stats_llm_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /stats llm command.

    Shows LLM usage statistics including token counts and costs.

    Usage:
        /stats llm - Show LLM usage statistics

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    logger.info("LLM stats requested", user_id=user_id)

    # Get current mode
    current_mode = get_current_mode(context.bot_data)

    # Check if database is available for stats
    db_session_factory = context.bot_data.get("db_session_factory")

    if not db_session_factory:
        # Show basic stats without database
        await update.message.reply_text(
            "LLM Usage Statistics\n"
            "--------------------\n\n"
            f"Current mode: {current_mode}\n\n"
            "Database not configured - detailed statistics unavailable.\n\n"
            "To view detailed statistics, ensure the database is properly configured."
        )
        return

    try:
        # Query database for usage stats
        from sqlalchemy import text, func
        from datetime import datetime, timezone, timedelta

        async with db_session_factory() as session:
            # Get total token usage from llm_usage_logs table
            today = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Try to query usage logs
            try:
                result = await session.execute(
                    text("""
                        SELECT
                            COUNT(*) as total_calls,
                            COALESCE(SUM(total_tokens), 0) as total_tokens,
                            COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                            COALESCE(SUM(posts_processed), 0) as total_posts
                        FROM llm_usage_logs
                        WHERE created_at >= :month_ago
                    """),
                    {"month_ago": month_ago}
                )
                row = result.fetchone()

                total_calls = row.total_calls if row else 0
                total_tokens = row.total_tokens if row else 0
                total_cost = row.total_cost if row else 0.0
                total_posts = row.total_posts if row else 0

                # Get today's stats
                today_result = await session.execute(
                    text("""
                        SELECT
                            COUNT(*) as calls,
                            COALESCE(SUM(total_tokens), 0) as tokens,
                            COALESCE(SUM(estimated_cost_usd), 0) as cost
                        FROM llm_usage_logs
                        WHERE created_at >= :today
                    """),
                    {"today": today}
                )
                today_row = today_result.fetchone()
                today_calls = today_row.calls if today_row else 0
                today_tokens = today_row.tokens if today_row else 0
                today_cost = today_row.cost if today_row else 0.0

                # Get enriched posts count
                enriched_result = await session.execute(
                    text("SELECT COUNT(*) FROM post_enrichments")
                )
                enriched_count = enriched_result.scalar() or 0

                message = (
                    "LLM Usage Statistics\n"
                    "--------------------\n\n"
                    f"Current mode: {current_mode}\n\n"
                    f"Today:\n"
                    f"  - API calls: {today_calls}\n"
                    f"  - Tokens used: {today_tokens:,}\n"
                    f"  - Estimated cost: ${today_cost:.4f}\n\n"
                    f"Last 30 days:\n"
                    f"  - API calls: {total_calls}\n"
                    f"  - Tokens used: {total_tokens:,}\n"
                    f"  - Estimated cost: ${total_cost:.4f}\n"
                    f"  - Posts processed: {total_posts}\n\n"
                    f"Total enriched posts: {enriched_count}"
                )

            except Exception as db_error:
                # Table may not exist yet
                logger.warning(
                    "Could not query LLM usage logs",
                    error=str(db_error),
                )
                message = (
                    "LLM Usage Statistics\n"
                    "--------------------\n\n"
                    f"Current mode: {current_mode}\n\n"
                    "No usage data available yet.\n\n"
                    "Statistics will appear once LLM enrichment tasks have run."
                )

        await update.message.reply_text(message)

    except Exception as error:
        await update.message.reply_text(
            "LLM Usage Statistics\n"
            "--------------------\n\n"
            f"Current mode: {current_mode}\n\n"
            "Error retrieving statistics. Please try again later."
        )
        logger.error(
            "Stats llm command error",
            user_id=user_id,
            error=str(error),
            exc_info=error,
        )

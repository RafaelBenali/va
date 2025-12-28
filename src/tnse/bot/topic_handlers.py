"""
TNSE Telegram Bot Topic Command Handlers

Provides command handlers for topic management operations.
Work Stream: WS-3.1 - Saved Topics

Commands:
- /savetopic <name> - Save current search configuration
- /topics - List all saved topics
- /topic <name> - Run a saved topic search
- /deletetopic <name> - Delete a saved topic
- /templates - Show pre-built topic templates

Requirements addressed:
- Topics saved and retrieved
- Templates work
- Quick access via commands
"""

from datetime import datetime, timezone
from collections.abc import Callable, Coroutine
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.tnse.core.logging import get_logger
from src.tnse.topics.service import (
    TopicService,
    SavedTopicData,
    TopicNotFoundError,
    TopicAlreadyExistsError,
)
from src.tnse.topics.templates import get_all_templates, get_template_by_name
from src.tnse.bot.search_handlers import (
    SearchFormatter,
    DEFAULT_PAGE_SIZE,
    create_pagination_keyboard,
)

logger = get_logger(__name__)

# Type alias for handler functions
HandlerFunc = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Coroutine[Any, Any, None]
]

# Callback data prefix for topic-related operations
TOPIC_CALLBACK_PREFIX = "topic:"


async def savetopic_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /savetopic command.

    Saves the current search configuration as a named topic.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data and user_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for topic name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /savetopic <name>\n\n"
            "Example: /savetopic corruption_news\n\n"
            "First run a search with /search, then save it as a topic."
        )
        logger.info("savetopic called without arguments", user_id=user_id)
        return

    topic_name = context.args[0]

    # Check if there's a last search to save
    last_query = context.user_data.get("last_search_query")
    if not last_query:
        await update.message.reply_text(
            "No search to save.\n\n"
            "Please run a search first with /search <query>, "
            "then use /savetopic to save it."
        )
        logger.info("savetopic called without prior search", user_id=user_id)
        return

    # Get topic service from bot_data
    topic_service = context.bot_data.get("topic_service")
    if not topic_service:
        await update.message.reply_text(
            "Topic service is not available. Please try again later."
        )
        logger.error("Topic service not configured in bot_data")
        return

    try:
        # Save the topic
        saved_topic = await topic_service.save_topic(
            name=topic_name,
            keywords=last_query,
            sort_mode=context.user_data.get("last_sort_mode"),
        )

        await update.message.reply_text(
            f"Topic saved successfully!\n\n"
            f"Name: {saved_topic.name}\n"
            f"Keywords: {saved_topic.keywords}\n\n"
            f"Use /topic {saved_topic.name} to run this search again."
        )

        logger.info(
            "Topic saved",
            user_id=user_id,
            topic_name=saved_topic.name,
            keywords=saved_topic.keywords,
        )

    except TopicAlreadyExistsError:
        await update.message.reply_text(
            f"A topic named '{topic_name}' already exists.\n\n"
            f"Use a different name or delete the existing topic with "
            f"/deletetopic {topic_name}"
        )
        logger.warning(
            "Duplicate topic name",
            user_id=user_id,
            topic_name=topic_name,
        )

    except Exception as error:
        await update.message.reply_text(
            "Error saving topic. Please try again later."
        )
        logger.error(
            "Error saving topic",
            user_id=user_id,
            topic_name=topic_name,
            error=str(error),
            exc_info=error,
        )


async def topics_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /topics command.

    Lists all saved topics for the user.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Get topic service from bot_data
    topic_service = context.bot_data.get("topic_service")
    if not topic_service:
        await update.message.reply_text(
            "Topic service is not available. Please try again later."
        )
        logger.error("Topic service not configured in bot_data")
        return

    try:
        topics = await topic_service.list_topics()

        if not topics:
            await update.message.reply_text(
                "No saved topics found.\n\n"
                "Use /search to find news, then /savetopic <name> to save it.\n"
                "Or use /templates to see pre-built topic templates."
            )
            logger.info("No topics found", user_id=user_id)
            return

        # Format the topic list
        lines = ["Your Saved Topics:\n"]
        for topic in topics:
            lines.append(f"- {topic.name}")
            lines.append(f"  Keywords: {topic.keywords}")
            lines.append("")

        lines.append("Use /topic <name> to run a saved search.")
        lines.append("Use /deletetopic <name> to delete a topic.")

        await update.message.reply_text("\n".join(lines))

        logger.info(
            "Topics listed",
            user_id=user_id,
            topic_count=len(topics),
        )

    except Exception as error:
        await update.message.reply_text(
            "Error retrieving topics. Please try again later."
        )
        logger.error(
            "Error listing topics",
            user_id=user_id,
            error=str(error),
            exc_info=error,
        )


async def topic_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /topic command.

    Runs a search using a saved topic's keywords.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for topic name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /topic <name>\n\n"
            "Example: /topic corruption_news\n\n"
            "Use /topics to see your saved topics."
        )
        logger.info("topic called without arguments", user_id=user_id)
        return

    topic_name = context.args[0]

    # Get topic service from bot_data
    topic_service = context.bot_data.get("topic_service")
    if not topic_service:
        await update.message.reply_text(
            "Topic service is not available. Please try again later."
        )
        logger.error("Topic service not configured in bot_data")
        return

    # Get search service from bot_data
    search_service = context.bot_data.get("search_service")
    if not search_service:
        await update.message.reply_text(
            "Search service is not available. Please try again later."
        )
        logger.error("Search service not configured in bot_data")
        return

    try:
        # Get the saved topic
        saved_topic = await topic_service.get_topic(topic_name)

        logger.info(
            "Running saved topic search",
            user_id=user_id,
            topic_name=saved_topic.name,
            keywords=saved_topic.keywords,
        )

        # Execute search with topic keywords
        results = await search_service.search(
            query=saved_topic.keywords,
            hours=24,
            limit=100,
            offset=0,
        )

        if not results:
            await update.message.reply_text(
                f'Topic: "{saved_topic.name}"\n'
                f'Keywords: {saved_topic.keywords}\n\n'
                f"No results found. Try again later or update your topic."
            )
            logger.info(
                "No results for topic",
                topic_name=saved_topic.name,
            )
            return

        # Format results
        page_size = DEFAULT_PAGE_SIZE
        total_count = len(results)
        total_pages = (total_count + page_size - 1) // page_size
        page_results = results[:page_size]

        formatter = SearchFormatter()
        formatted_message = formatter.format_results_page(
            query=f"[Topic: {saved_topic.name}] {saved_topic.keywords}",
            results=page_results,
            total_count=total_count,
            page=1,
            page_size=page_size,
        )

        # Create pagination keyboard if multiple pages
        reply_markup = None
        if total_pages > 1:
            # Use keywords for pagination to maintain compatibility
            reply_markup = create_pagination_keyboard(
                query=saved_topic.keywords,
                current_page=1,
                total_pages=total_pages,
            )

        await update.message.reply_text(
            formatted_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # Store results for pagination
        context.user_data["last_search_query"] = saved_topic.keywords
        context.user_data["last_search_results"] = results

        logger.info(
            "Topic search completed",
            topic_name=saved_topic.name,
            result_count=total_count,
        )

    except TopicNotFoundError:
        await update.message.reply_text(
            f"Topic '{topic_name}' not found.\n\n"
            f"Use /topics to see your saved topics, or "
            f"/templates to see pre-built templates."
        )
        logger.warning(
            "Topic not found",
            user_id=user_id,
            topic_name=topic_name,
        )

    except Exception as error:
        await update.message.reply_text(
            "Error running topic search. Please try again later."
        )
        logger.error(
            "Error running topic search",
            user_id=user_id,
            topic_name=topic_name,
            error=str(error),
            exc_info=error,
        )


async def deletetopic_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /deletetopic command.

    Deletes a saved topic.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for topic name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /deletetopic <name>\n\n"
            "Example: /deletetopic old_topic\n\n"
            "Use /topics to see your saved topics."
        )
        logger.info("deletetopic called without arguments", user_id=user_id)
        return

    topic_name = context.args[0]

    # Get topic service from bot_data
    topic_service = context.bot_data.get("topic_service")
    if not topic_service:
        await update.message.reply_text(
            "Topic service is not available. Please try again later."
        )
        logger.error("Topic service not configured in bot_data")
        return

    try:
        await topic_service.delete_topic(topic_name)

        await update.message.reply_text(
            f"Topic '{topic_name}' has been deleted."
        )

        logger.info(
            "Topic deleted",
            user_id=user_id,
            topic_name=topic_name,
        )

    except TopicNotFoundError:
        await update.message.reply_text(
            f"Topic '{topic_name}' not found.\n\n"
            f"Use /topics to see your saved topics."
        )
        logger.warning(
            "Topic not found for deletion",
            user_id=user_id,
            topic_name=topic_name,
        )

    except Exception as error:
        await update.message.reply_text(
            "Error deleting topic. Please try again later."
        )
        logger.error(
            "Error deleting topic",
            user_id=user_id,
            topic_name=topic_name,
            error=str(error),
            exc_info=error,
        )


async def templates_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /templates command.

    Shows all pre-built topic templates.

    Args:
        update: The Telegram update object.
        context: The callback context.
    """
    user_id = update.effective_user.id if update.effective_user else None

    templates = get_all_templates()

    lines = [
        "Pre-built Topic Templates:\n",
        "Use these templates for quick searches:\n",
    ]

    for template in templates:
        lines.append(f"- {template.name}")
        lines.append(f"  Keywords: {template.keywords}")
        if template.description:
            lines.append(f"  Description: {template.description}")
        lines.append("")

    lines.append("To use a template, run a search with those keywords:")
    lines.append("Example: /search corruption bribery scandal")
    lines.append("\nOr save your own topics with /savetopic after searching.")

    await update.message.reply_text("\n".join(lines))

    logger.info(
        "Templates shown",
        user_id=user_id,
        template_count=len(templates),
    )


async def use_template_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle the /usetemplate command.

    Runs a search using a pre-built template's keywords.

    Args:
        update: The Telegram update object.
        context: The callback context containing bot_data.
    """
    user_id = update.effective_user.id if update.effective_user else None

    # Check for template name argument
    if not context.args:
        await update.message.reply_text(
            "Usage: /usetemplate <name>\n\n"
            "Example: /usetemplate corruption\n\n"
            "Use /templates to see available templates."
        )
        logger.info("usetemplate called without arguments", user_id=user_id)
        return

    template_name = context.args[0]

    # Get template
    template = get_template_by_name(template_name)
    if not template:
        await update.message.reply_text(
            f"Template '{template_name}' not found.\n\n"
            f"Use /templates to see available templates."
        )
        logger.warning(
            "Template not found",
            user_id=user_id,
            template_name=template_name,
        )
        return

    # Get search service from bot_data
    search_service = context.bot_data.get("search_service")
    if not search_service:
        await update.message.reply_text(
            "Search service is not available. Please try again later."
        )
        logger.error("Search service not configured in bot_data")
        return

    try:
        logger.info(
            "Running template search",
            user_id=user_id,
            template_name=template.name,
            keywords=template.keywords,
        )

        # Execute search with template keywords
        results = await search_service.search(
            query=template.keywords,
            hours=24,
            limit=100,
            offset=0,
        )

        if not results:
            await update.message.reply_text(
                f'Template: "{template.name}"\n'
                f'Keywords: {template.keywords}\n\n'
                f"No results found. Try again later."
            )
            logger.info(
                "No results for template",
                template_name=template.name,
            )
            return

        # Format results
        page_size = DEFAULT_PAGE_SIZE
        total_count = len(results)
        total_pages = (total_count + page_size - 1) // page_size
        page_results = results[:page_size]

        formatter = SearchFormatter()
        formatted_message = formatter.format_results_page(
            query=f"[Template: {template.name}] {template.keywords}",
            results=page_results,
            total_count=total_count,
            page=1,
            page_size=page_size,
        )

        # Create pagination keyboard if multiple pages
        reply_markup = None
        if total_pages > 1:
            reply_markup = create_pagination_keyboard(
                query=template.keywords,
                current_page=1,
                total_pages=total_pages,
            )

        await update.message.reply_text(
            formatted_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # Store results for pagination and potential saving
        context.user_data["last_search_query"] = template.keywords
        context.user_data["last_search_results"] = results

        logger.info(
            "Template search completed",
            template_name=template.name,
            result_count=total_count,
        )

    except Exception as error:
        await update.message.reply_text(
            "Error running template search. Please try again later."
        )
        logger.error(
            "Error running template search",
            user_id=user_id,
            template_name=template_name,
            error=str(error),
            exc_info=error,
        )

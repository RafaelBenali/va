"""
TNSE Structured Logging Module

Provides structured JSON logging using structlog library.
Supports log levels, extra context, exception handling, and environment-based configuration.

Requirements addressed:
- NFR-E-002: System SHALL implement structured logging (JSON format)
- NFR-E-003: Log levels MUST include DEBUG, INFO, WARN, ERROR, FATAL
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional, TextIO

import structlog
from structlog.types import Processor


def _add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO 8601 timestamp to log entry."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def _add_app_name(app_name: str) -> Processor:
    """Create a processor that adds the application name to log entries."""

    def processor(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        event_dict["app"] = app_name
        return event_dict

    return processor


def _rename_event_to_message(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Rename 'event' key to 'message' for consistency."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def configure_logging(
    stream: Optional[TextIO] = None,
    level: Optional[str] = None,
    app_name: str = "tnse",
) -> structlog.BoundLogger:
    """
    Configure structured logging for the application.

    Args:
        stream: Output stream for logs (default: sys.stdout)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses LOG_LEVEL environment variable or defaults to INFO.
        app_name: Application name to include in log entries.

    Returns:
        A configured structlog BoundLogger instance.

    Example:
        >>> logger = configure_logging()
        >>> logger.info("User logged in", user_id=123)
    """
    # Determine log level
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Use provided stream or default to stdout
    output_stream = stream if stream is not None else sys.stdout

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_timestamp,
        _add_app_name(app_name),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output_stream),
        cache_logger_on_first_use=False,  # Disable caching for testing
    )

    return structlog.get_logger()


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a logger instance bound with a specific name/module.

    Args:
        name: The name to bind to the logger (typically __name__).

    Returns:
        A structlog BoundLogger instance bound with the provided name.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
    """
    return structlog.get_logger().bind(logger=name)


def bind_context(**context: Any) -> None:
    """
    Bind context variables that will be included in all subsequent log entries.

    This is useful for request-scoped logging where you want to include
    request_id, user_id, etc. in all logs within a request context.

    Args:
        **context: Key-value pairs to bind to the logging context.

    Example:
        >>> bind_context(request_id="abc-123", user_id=456)
        >>> logger.info("Processing request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**context)


def clear_context() -> None:
    """
    Clear all bound context variables.

    Call this at the end of a request to clean up context.
    """
    structlog.contextvars.clear_contextvars()

"""
Tests for TNSE structured logging module.

Following TDD methodology: these tests are written BEFORE the implementation.
"""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest


class TestStructuredLogging:
    """Tests for the structured logging configuration and functionality."""

    def test_configure_logging_returns_logger(self):
        """Test that configure_logging returns a properly configured logger."""
        from src.tnse.core.logging import configure_logging

        logger = configure_logging()
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def test_logger_outputs_json_format(self):
        """Test that log output is in JSON format for structured logging."""
        from src.tnse.core.logging import configure_logging

        # Capture log output
        stream = StringIO()
        logger = configure_logging(stream=stream)

        logger.info("test message")

        output = stream.getvalue()
        assert output, "Logger should produce output"

        # Verify JSON format
        log_entry = json.loads(output.strip().split("\n")[-1])
        assert "event" in log_entry or "message" in log_entry

    def test_logger_includes_timestamp(self):
        """Test that log entries include a timestamp."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream)

        logger.info("test message with timestamp")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert "timestamp" in log_entry or "time" in log_entry

    def test_logger_includes_log_level(self):
        """Test that log entries include the log level."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream)

        logger.warning("test warning message")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert "level" in log_entry
        assert log_entry["level"].upper() in ["WARNING", "WARN"]

    def test_logger_accepts_extra_context(self):
        """Test that logger can include extra context in log entries."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream)

        logger.info("user action", user_id=123, action="login")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert log_entry.get("user_id") == 123
        assert log_entry.get("action") == "login"

    def test_logger_respects_log_level_setting(self):
        """Test that logger respects the configured log level."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream, level="WARNING")

        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")

        output = stream.getvalue()
        # Debug and info should not appear
        assert "debug message" not in output
        assert "info message" not in output
        # Warning should appear
        assert "warning message" in output

    def test_get_logger_returns_named_logger(self):
        """Test that get_logger returns a logger with the specified name."""
        from src.tnse.core.logging import configure_logging, get_logger

        configure_logging()
        logger = get_logger("test.module")

        assert logger is not None
        # The logger should be bound with the module name

    def test_logger_handles_exceptions(self):
        """Test that logger properly handles and formats exceptions."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream)

        try:
            raise ValueError("test exception")
        except ValueError:
            logger.exception("caught an error")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert "exception" in log_entry or "exc_info" in log_entry or "traceback" in output.lower()

    def test_configure_logging_from_env(self):
        """Test that logging configuration respects environment variables."""
        from src.tnse.core.logging import configure_logging

        with patch.dict("os.environ", {"LOG_LEVEL": "ERROR"}):
            stream = StringIO()
            # When no level specified, should use env var
            logger = configure_logging(stream=stream, level=None)

            logger.info("should not appear")
            logger.error("should appear")

            output = stream.getvalue()
            assert "should not appear" not in output
            assert "should appear" in output


class TestLoggerIntegration:
    """Integration tests for logger with application components."""

    def test_logger_includes_app_name(self):
        """Test that log entries include the application name."""
        from src.tnse.core.logging import configure_logging

        stream = StringIO()
        logger = configure_logging(stream=stream, app_name="tnse")

        logger.info("test message")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert log_entry.get("app") == "tnse" or log_entry.get("application") == "tnse"

    def test_logger_can_bind_request_context(self):
        """Test that logger can bind request-specific context."""
        from src.tnse.core.logging import configure_logging, get_logger

        configure_logging()
        logger = get_logger("request")

        # Bind request context
        request_logger = logger.bind(request_id="abc-123", user_id=456)

        stream = StringIO()
        # Create a new logger with the stream to capture output
        test_logger = configure_logging(stream=stream)
        test_logger = test_logger.bind(request_id="abc-123", user_id=456)
        test_logger.info("handling request")

        output = stream.getvalue()
        log_entry = json.loads(output.strip().split("\n")[-1])

        assert log_entry.get("request_id") == "abc-123"
        assert log_entry.get("user_id") == 456

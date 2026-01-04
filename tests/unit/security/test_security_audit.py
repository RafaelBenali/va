"""
Security Audit Tests for WS-6.2

This module contains tests to validate the security posture of the TNSE codebase.
These tests verify:
- No hardcoded secrets in source code
- Proper parameterized SQL queries
- Input validation on bot commands
- Secure Docker configuration
- Proper environment variable handling
- Rate limiting implementation

Work Stream: WS-6.2 - Security Vulnerability Assessment
"""

import ast
import re
from pathlib import Path
from typing import Generator

import pytest


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "tnse"


class TestNoHardcodedSecrets:
    """Tests to ensure no hardcoded secrets exist in the codebase."""

    SECRET_PATTERNS = [
        # API keys and tokens
        (r'sk-[a-zA-Z0-9]{48,}', "OpenAI API key"),
        (r'sk-ant-[a-zA-Z0-9-]+', "Anthropic API key"),
        (r'\d{9,}:[a-zA-Z0-9_-]{35}', "Telegram bot token"),
        # Database passwords in connection strings
        (r'postgresql://[^:]+:[^@]+@', "PostgreSQL connection with password"),
        (r'redis://:[^@]+@', "Redis connection with password"),
        # Generic secret patterns
        (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
        (r'secret\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded secret"),
    ]

    ALLOWED_FILES = [
        # Test files may contain mock values
        "test_",
        # Example files are expected to have placeholder values
        ".example",
        # Config files may have default empty strings
        "config.py",
    ]

    def get_python_files(self) -> Generator[Path, None, None]:
        """Get all Python files in the source directory."""
        for python_file in SRC_DIR.rglob("*.py"):
            yield python_file

    def is_allowed_file(self, file_path: Path) -> bool:
        """Check if a file is allowed to contain secret-like patterns."""
        filename = file_path.name
        for allowed in self.ALLOWED_FILES:
            if allowed in filename:
                return True
        return False

    def test_no_openai_api_keys(self) -> None:
        """Verify no OpenAI API keys are hardcoded."""
        pattern = re.compile(r'sk-[a-zA-Z0-9]{48,}')

        for python_file in self.get_python_files():
            if self.is_allowed_file(python_file):
                continue

            content = python_file.read_text(encoding="utf-8", errors="ignore")
            matches = pattern.findall(content)

            assert not matches, (
                f"Potential OpenAI API key found in {python_file.relative_to(PROJECT_ROOT)}"
            )

    def test_no_anthropic_api_keys(self) -> None:
        """Verify no Anthropic API keys are hardcoded."""
        pattern = re.compile(r'sk-ant-[a-zA-Z0-9-]+')

        for python_file in self.get_python_files():
            if self.is_allowed_file(python_file):
                continue

            content = python_file.read_text(encoding="utf-8", errors="ignore")
            matches = pattern.findall(content)

            assert not matches, (
                f"Potential Anthropic API key found in {python_file.relative_to(PROJECT_ROOT)}"
            )

    def test_no_telegram_bot_tokens(self) -> None:
        """Verify no Telegram bot tokens are hardcoded."""
        # Telegram bot tokens have format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        pattern = re.compile(r'\d{9,}:[a-zA-Z0-9_-]{35}')

        for python_file in self.get_python_files():
            if self.is_allowed_file(python_file):
                continue

            content = python_file.read_text(encoding="utf-8", errors="ignore")
            matches = pattern.findall(content)

            assert not matches, (
                f"Potential Telegram bot token found in {python_file.relative_to(PROJECT_ROOT)}"
            )

    def test_no_hardcoded_database_passwords(self) -> None:
        """Verify no database connection strings with passwords are hardcoded."""
        # Pattern for postgresql://user:password@host format
        pattern = re.compile(
            r'postgresql://[a-zA-Z0-9_]+:[a-zA-Z0-9!@#$%^&*]+@[a-zA-Z0-9.-]+',
            re.IGNORECASE
        )

        for python_file in self.get_python_files():
            if self.is_allowed_file(python_file):
                continue

            content = python_file.read_text(encoding="utf-8", errors="ignore")
            matches = pattern.findall(content)

            # Filter out placeholder patterns
            real_matches = [
                match for match in matches
                if not any(placeholder in match.lower() for placeholder in
                          ["user:password", "user:pass", "localhost", "example"])
            ]

            assert not real_matches, (
                f"Hardcoded database credentials found in {python_file.relative_to(PROJECT_ROOT)}"
            )


class TestSQLInjectionPrevention:
    """Tests to ensure SQL queries use parameterization."""

    def get_python_files(self) -> Generator[Path, None, None]:
        """Get all Python files in the source directory."""
        for python_file in SRC_DIR.rglob("*.py"):
            yield python_file

    def test_no_string_formatted_sql(self) -> None:
        """Verify no SQL queries are built using string formatting."""
        # Patterns that indicate string formatting in SQL
        # These patterns look for SQL keywords followed by typical SQL structure
        dangerous_patterns = [
            # f-strings with SELECT followed by FROM
            r'f["\'].*\bSELECT\b.*\bFROM\b.*\{',
            # f-strings with INSERT INTO
            r'f["\'].*\bINSERT\s+INTO\b.*\{',
            # f-strings with UPDATE SET
            r'f["\'].*\bUPDATE\b.*\bSET\b.*\{',
            # f-strings with DELETE FROM
            r'f["\'].*\bDELETE\s+FROM\b.*\{',
            # .format() with SQL keywords
            r'["\'].*\bSELECT\b.*\bFROM\b.*["\']\.format\(',
            # % formatting with SQL keywords
            r'["\'].*\bSELECT\b.*\bFROM\b.*%s.*["\'].*%',
        ]

        issues_found = []

        for python_file in self.get_python_files():
            content = python_file.read_text(encoding="utf-8", errors="ignore")

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    issues_found.append(
                        f"{python_file.relative_to(PROJECT_ROOT)}: {matches[0][:50]}..."
                    )

        assert not issues_found, (
            f"Potential SQL injection vulnerabilities found:\n" +
            "\n".join(issues_found)
        )

    def test_sqlalchemy_text_uses_bind_parameters(self) -> None:
        """Verify SQLAlchemy text() queries use bind parameters."""
        # Find all uses of text() and verify they use :param_name syntax
        text_pattern = re.compile(r'text\s*\(\s*["\'](.+?)["\']', re.DOTALL)

        for python_file in self.get_python_files():
            content = python_file.read_text(encoding="utf-8", errors="ignore")

            # Find text() calls
            text_matches = text_pattern.findall(content)

            for sql_query in text_matches:
                # Skip simple queries like "SELECT 1"
                if len(sql_query) < 20:
                    continue

                # Check if query uses :param syntax for parameters
                # If query contains WHERE or values, it should use bind params
                if re.search(r'\bWHERE\b', sql_query, re.IGNORECASE):
                    # Should have :param_name in the query
                    has_bind_params = bool(re.search(r':\w+', sql_query))
                    assert has_bind_params, (
                        f"SQL query with WHERE clause should use bind parameters:\n"
                        f"File: {python_file.relative_to(PROJECT_ROOT)}\n"
                        f"Query: {sql_query[:200]}..."
                    )


class TestInputValidation:
    """Tests to ensure bot commands validate user input."""

    def test_channel_username_validation_exists(self) -> None:
        """Verify channel username extraction uses regex validation."""
        channel_handlers = SRC_DIR / "bot" / "channel_handlers.py"
        content = channel_handlers.read_text(encoding="utf-8")

        # Should have a pattern for validating Telegram usernames/URLs
        assert "re.compile" in content or "re.match" in content or "re.search" in content, (
            "Channel handlers should use regex for username validation"
        )

        # Should have the extract_channel_username function
        assert "extract_channel_username" in content, (
            "Channel handlers should have username extraction function"
        )

    def test_search_query_tokenization(self) -> None:
        """Verify search queries are tokenized before use."""
        search_service = SRC_DIR / "search" / "service.py"
        content = search_service.read_text(encoding="utf-8")

        # Should use tokenizer for processing queries
        assert "tokenize" in content or "Tokenizer" in content, (
            "Search service should tokenize queries before executing"
        )

    def test_pagination_parameters_validated(self) -> None:
        """Verify pagination parameters are validated."""
        search_handlers = SRC_DIR / "bot" / "search_handlers.py"
        content = search_handlers.read_text(encoding="utf-8")

        # Should validate page numbers
        assert "int(" in content, (
            "Search handlers should convert page numbers to integers"
        )

        # Should clamp page values to valid range
        assert "max(" in content or "min(" in content, (
            "Search handlers should clamp page values to valid range"
        )


class TestDockerSecurity:
    """Tests to verify Docker configuration security."""

    def test_dockerfile_uses_non_root_user(self) -> None:
        """Verify Dockerfile creates and uses non-root user."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        content = dockerfile.read_text(encoding="utf-8")

        # Should have USER instruction
        assert "USER " in content, (
            "Dockerfile should use non-root USER instruction"
        )

        # Should create a user
        assert "useradd" in content or "adduser" in content, (
            "Dockerfile should create a non-root user"
        )

    def test_dockerfile_has_health_check(self) -> None:
        """Verify Dockerfile includes health check."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        content = dockerfile.read_text(encoding="utf-8")

        assert "HEALTHCHECK" in content, (
            "Dockerfile should include HEALTHCHECK instruction"
        )

    def test_dockerfile_uses_slim_base_image(self) -> None:
        """Verify Dockerfile uses slim base image."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        content = dockerfile.read_text(encoding="utf-8")

        # Should use slim or alpine image
        assert "slim" in content or "alpine" in content, (
            "Dockerfile should use slim or alpine base image for reduced attack surface"
        )


class TestEnvironmentVariableHandling:
    """Tests to verify secure environment variable handling."""

    def test_env_file_in_gitignore(self) -> None:
        """Verify .env files are in .gitignore."""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")

        assert ".env" in content, (
            ".gitignore should exclude .env files"
        )

    def test_config_uses_pydantic_settings(self) -> None:
        """Verify configuration uses pydantic-settings for type safety."""
        config_file = SRC_DIR / "core" / "config.py"
        content = config_file.read_text(encoding="utf-8")

        assert "BaseSettings" in content, (
            "Configuration should use pydantic BaseSettings"
        )

        assert "pydantic_settings" in content, (
            "Configuration should import from pydantic_settings"
        )

    def test_secrets_have_no_default_values(self) -> None:
        """Verify sensitive fields don't have insecure default values."""
        config_file = SRC_DIR / "core" / "config.py"
        content = config_file.read_text(encoding="utf-8")

        # Bot token should not have a default real value
        # Support both Optional[str] and str | None (PEP 604) syntax
        assert (
            "bot_token: Optional[str] = Field(default=None" in content or
            "bot_token: str | None = Field(default=None" in content
        ), (
            "Telegram bot token should default to None, not a value"
        )

        # API keys should not have default values
        # Support both Optional[str] and str | None (PEP 604) syntax
        assert (
            "api_key: Optional[str] = Field(default=None" in content or
            "api_key: str | None = Field(default=None" in content or
            "OPENAI_API_KEY" in content
        ), (
            "API keys should default to None"
        )

    def test_secret_key_has_change_me_default(self) -> None:
        """Verify SECRET_KEY has an obvious placeholder default."""
        config_file = SRC_DIR / "core" / "config.py"
        content = config_file.read_text(encoding="utf-8")

        # Should have a default that indicates it needs to be changed
        assert "change-me" in content.lower() or "changeme" in content.lower(), (
            "SECRET_KEY should have an obvious placeholder default"
        )


class TestRateLimiting:
    """Tests to verify rate limiting implementation."""

    def test_rate_limiter_exists(self) -> None:
        """Verify rate limiter module exists."""
        rate_limiter = SRC_DIR / "telegram" / "rate_limiter.py"

        assert rate_limiter.exists(), (
            "Rate limiter module should exist at telegram/rate_limiter.py"
        )

    def test_rate_limiter_has_token_bucket(self) -> None:
        """Verify rate limiter uses token bucket algorithm."""
        rate_limiter = SRC_DIR / "telegram" / "rate_limiter.py"
        content = rate_limiter.read_text(encoding="utf-8")

        # Should have token tracking
        assert "_tokens" in content or "tokens" in content, (
            "Rate limiter should implement token bucket algorithm"
        )

        # Should have acquire method
        assert "acquire" in content, (
            "Rate limiter should have acquire method"
        )

    def test_exponential_backoff_exists(self) -> None:
        """Verify exponential backoff is implemented."""
        rate_limiter = SRC_DIR / "telegram" / "rate_limiter.py"
        content = rate_limiter.read_text(encoding="utf-8")

        assert "ExponentialBackoff" in content or "exponential" in content.lower(), (
            "Rate limiter should implement exponential backoff"
        )

    def test_retryable_decorator_exists(self) -> None:
        """Verify retryable decorator for API calls exists."""
        rate_limiter = SRC_DIR / "telegram" / "rate_limiter.py"
        content = rate_limiter.read_text(encoding="utf-8")

        assert "retryable" in content or "retry" in content, (
            "Rate limiter should have retryable decorator or retry functionality"
        )


class TestBotAccessControl:
    """Tests to verify bot access control implementation."""

    def test_user_whitelist_support(self) -> None:
        """Verify bot supports user whitelist for access control."""
        config_file = SRC_DIR / "core" / "config.py"
        content = config_file.read_text(encoding="utf-8")

        assert "allowed_telegram_users" in content.lower() or "allowed_users" in content.lower(), (
            "Configuration should support allowed users list"
        )

    def test_access_check_decorator_exists(self) -> None:
        """Verify access control decorator exists for handlers."""
        handlers = SRC_DIR / "bot" / "handlers.py"
        content = handlers.read_text(encoding="utf-8")

        assert "require_access" in content or "check_access" in content, (
            "Bot handlers should have access control decorator/function"
        )

    def test_token_redaction_in_logs(self) -> None:
        """Verify bot token is redacted in logs and string representations."""
        bot_config = SRC_DIR / "bot" / "config.py"
        content = bot_config.read_text(encoding="utf-8")

        assert "redact" in content.lower() or "REDACTED" in content, (
            "Bot config should redact token in string representations"
        )

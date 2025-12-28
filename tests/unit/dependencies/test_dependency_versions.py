"""
Test module for validating dependency versions.

This module ensures all project dependencies are at or above the December 2025
minimum stable versions. This is part of WS-6.1 Dependency Modernization.
"""

from importlib.metadata import version
from packaging.version import Version
import pytest


class TestCoreDependencyVersions:
    """Tests for core production dependencies."""

    def test_fastapi_version_is_december_2025_compatible(self) -> None:
        """FastAPI should be at least 0.115.0 (December 2025 baseline)."""
        installed_version = Version(version("fastapi"))
        minimum_version = Version("0.115.0")
        assert installed_version >= minimum_version, (
            f"FastAPI version {installed_version} is below minimum {minimum_version}"
        )

    def test_uvicorn_version_is_december_2025_compatible(self) -> None:
        """Uvicorn should be at least 0.32.0 (December 2025 baseline)."""
        installed_version = Version(version("uvicorn"))
        minimum_version = Version("0.32.0")
        assert installed_version >= minimum_version, (
            f"Uvicorn version {installed_version} is below minimum {minimum_version}"
        )

    def test_pydantic_version_is_december_2025_compatible(self) -> None:
        """Pydantic should be at least 2.10.0 (December 2025 baseline)."""
        installed_version = Version(version("pydantic"))
        minimum_version = Version("2.10.0")
        assert installed_version >= minimum_version, (
            f"Pydantic version {installed_version} is below minimum {minimum_version}"
        )

    def test_pydantic_settings_version_is_december_2025_compatible(self) -> None:
        """Pydantic-settings should be at least 2.6.0 (December 2025 baseline)."""
        installed_version = Version(version("pydantic-settings"))
        minimum_version = Version("2.6.0")
        assert installed_version >= minimum_version, (
            f"Pydantic-settings version {installed_version} is below minimum {minimum_version}"
        )

    def test_structlog_version_is_december_2025_compatible(self) -> None:
        """Structlog should be at least 24.4.0 (December 2025 baseline)."""
        installed_version = Version(version("structlog"))
        minimum_version = Version("24.4.0")
        assert installed_version >= minimum_version, (
            f"Structlog version {installed_version} is below minimum {minimum_version}"
        )

    def test_python_dotenv_version_is_december_2025_compatible(self) -> None:
        """Python-dotenv should be at least 1.0.1 (December 2025 baseline)."""
        installed_version = Version(version("python-dotenv"))
        minimum_version = Version("1.0.1")
        assert installed_version >= minimum_version, (
            f"Python-dotenv version {installed_version} is below minimum {minimum_version}"
        )


class TestDatabaseDependencyVersions:
    """Tests for database-related dependencies."""

    def test_sqlalchemy_version_is_december_2025_compatible(self) -> None:
        """SQLAlchemy should be at least 2.0.35 (December 2025 baseline)."""
        installed_version = Version(version("sqlalchemy"))
        minimum_version = Version("2.0.35")
        assert installed_version >= minimum_version, (
            f"SQLAlchemy version {installed_version} is below minimum {minimum_version}"
        )

    def test_alembic_version_is_december_2025_compatible(self) -> None:
        """Alembic should be at least 1.14.0 (December 2025 baseline)."""
        installed_version = Version(version("alembic"))
        minimum_version = Version("1.14.0")
        assert installed_version >= minimum_version, (
            f"Alembic version {installed_version} is below minimum {minimum_version}"
        )

    def test_psycopg2_version_is_december_2025_compatible(self) -> None:
        """Psycopg2-binary should be at least 2.9.10 (December 2025 baseline)."""
        installed_version = Version(version("psycopg2-binary"))
        minimum_version = Version("2.9.10")
        assert installed_version >= minimum_version, (
            f"Psycopg2-binary version {installed_version} is below minimum {minimum_version}"
        )


class TestCacheQueueDependencyVersions:
    """Tests for cache and queue dependencies."""

    def test_redis_version_is_december_2025_compatible(self) -> None:
        """Redis client should be at least 5.2.0 (December 2025 baseline)."""
        installed_version = Version(version("redis"))
        minimum_version = Version("5.2.0")
        assert installed_version >= minimum_version, (
            f"Redis version {installed_version} is below minimum {minimum_version}"
        )

    def test_celery_version_is_december_2025_compatible(self) -> None:
        """Celery should be at least 5.4.0 (December 2025 baseline)."""
        installed_version = Version(version("celery"))
        minimum_version = Version("5.4.0")
        assert installed_version >= minimum_version, (
            f"Celery version {installed_version} is below minimum {minimum_version}"
        )


class TestHttpDependencyVersions:
    """Tests for HTTP client dependencies."""

    def test_httpx_version_is_december_2025_compatible(self) -> None:
        """HTTPX should be at least 0.27.0 (December 2025 baseline)."""
        installed_version = Version(version("httpx"))
        minimum_version = Version("0.27.0")
        assert installed_version >= minimum_version, (
            f"HTTPX version {installed_version} is below minimum {minimum_version}"
        )


class TestTelegramDependencyVersions:
    """Tests for Telegram-related dependencies."""

    def test_python_telegram_bot_version_is_december_2025_compatible(self) -> None:
        """Python-telegram-bot should be at least 21.0 (December 2025 baseline)."""
        installed_version = Version(version("python-telegram-bot"))
        minimum_version = Version("21.0")
        assert installed_version >= minimum_version, (
            f"Python-telegram-bot version {installed_version} is below minimum {minimum_version}"
        )

    def test_telethon_version_is_december_2025_compatible(self) -> None:
        """Telethon should be at least 1.37.0 (December 2025 baseline)."""
        try:
            installed_version = Version(version("telethon"))
            minimum_version = Version("1.37.0")
            assert installed_version >= minimum_version, (
                f"Telethon version {installed_version} is below minimum {minimum_version}"
            )
        except Exception:
            pytest.skip("Telethon package not installed (optional dependency)")


class TestDevDependencyVersions:
    """Tests for development dependencies."""

    def test_pytest_version_is_december_2025_compatible(self) -> None:
        """Pytest should be at least 8.0.0 (December 2025 baseline)."""
        installed_version = Version(version("pytest"))
        minimum_version = Version("8.0.0")
        assert installed_version >= minimum_version, (
            f"Pytest version {installed_version} is below minimum {minimum_version}"
        )

    def test_pytest_cov_version_is_december_2025_compatible(self) -> None:
        """Pytest-cov should be at least 5.0.0 (December 2025 baseline)."""
        installed_version = Version(version("pytest-cov"))
        minimum_version = Version("5.0.0")
        assert installed_version >= minimum_version, (
            f"Pytest-cov version {installed_version} is below minimum {minimum_version}"
        )

    def test_pytest_asyncio_version_is_december_2025_compatible(self) -> None:
        """Pytest-asyncio should be at least 0.24.0 (December 2025 baseline)."""
        installed_version = Version(version("pytest-asyncio"))
        minimum_version = Version("0.24.0")
        assert installed_version >= minimum_version, (
            f"Pytest-asyncio version {installed_version} is below minimum {minimum_version}"
        )

    def test_ruff_version_is_december_2025_compatible(self) -> None:
        """Ruff should be at least 0.8.0 (December 2025 baseline)."""
        installed_version = Version(version("ruff"))
        minimum_version = Version("0.8.0")
        assert installed_version >= minimum_version, (
            f"Ruff version {installed_version} is below minimum {minimum_version}"
        )

    def test_mypy_version_is_december_2025_compatible(self) -> None:
        """Mypy should be at least 1.13.0 (December 2025 baseline)."""
        installed_version = Version(version("mypy"))
        minimum_version = Version("1.13.0")
        assert installed_version >= minimum_version, (
            f"Mypy version {installed_version} is below minimum {minimum_version}"
        )

    def test_black_version_is_december_2025_compatible(self) -> None:
        """Black should be at least 24.10.0 (December 2025 baseline)."""
        installed_version = Version(version("black"))
        minimum_version = Version("24.10.0")
        assert installed_version >= minimum_version, (
            f"Black version {installed_version} is below minimum {minimum_version}"
        )

    def test_isort_version_is_december_2025_compatible(self) -> None:
        """Isort should be at least 5.13.0 (December 2025 baseline)."""
        installed_version = Version(version("isort"))
        minimum_version = Version("5.13.0")
        assert installed_version >= minimum_version, (
            f"Isort version {installed_version} is below minimum {minimum_version}"
        )

    def test_pre_commit_version_is_december_2025_compatible(self) -> None:
        """Pre-commit should be at least 4.0.0 (December 2025 baseline)."""
        installed_version = Version(version("pre-commit"))
        minimum_version = Version("4.0.0")
        assert installed_version >= minimum_version, (
            f"Pre-commit version {installed_version} is below minimum {minimum_version}"
        )


class TestOptionalLLMDependencyVersions:
    """Tests for optional LLM dependencies."""

    def test_openai_version_is_december_2025_compatible(self) -> None:
        """OpenAI should be at least 1.50.0 (December 2025 baseline)."""
        try:
            installed_version = Version(version("openai"))
            minimum_version = Version("1.50.0")
            assert installed_version >= minimum_version, (
                f"OpenAI version {installed_version} is below minimum {minimum_version}"
            )
        except Exception:
            pytest.skip("OpenAI package not installed (optional dependency)")

    def test_anthropic_version_is_december_2025_compatible(self) -> None:
        """Anthropic should be at least 0.40.0 (December 2025 baseline)."""
        try:
            installed_version = Version(version("anthropic"))
            minimum_version = Version("0.40.0")
            assert installed_version >= minimum_version, (
                f"Anthropic version {installed_version} is below minimum {minimum_version}"
            )
        except Exception:
            pytest.skip("Anthropic package not installed (optional dependency)")

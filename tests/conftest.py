"""
TNSE Test Configuration

Pytest fixtures and configuration for the test suite.
"""

import os
from typing import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Generator[None, None, None]:
    """Reset the settings cache before each test."""
    from src.tnse.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env() -> Generator[dict[str, str], None, None]:
    """Provide a clean test environment with default values."""
    test_env_vars = {
        "APP_NAME": "tnse-test",
        "APP_ENV": "test",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "tnse_test",
        "POSTGRES_USER": "tnse_test",
        "POSTGRES_PASSWORD": "test_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
    }
    with patch.dict(os.environ, test_env_vars, clear=False):
        yield test_env_vars


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Provide a clean environment without TNSE-related variables."""
    env_vars_to_remove = [
        key for key in os.environ
        if key.startswith(("POSTGRES_", "REDIS_", "CELERY_", "TELEGRAM_", "APP_", "LOG_"))
    ]
    original_values = {key: os.environ.get(key) for key in env_vars_to_remove}

    for key in env_vars_to_remove:
        os.environ.pop(key, None)

    yield

    # Restore original values
    for key, value in original_values.items():
        if value is not None:
            os.environ[key] = value

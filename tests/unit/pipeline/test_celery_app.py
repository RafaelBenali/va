"""
Tests for TNSE Celery Application Configuration

Following TDD methodology: these tests validate the Celery app setup for background tasks.

Work Stream: WS-1.6 - Content Collection Pipeline
"""

import os
from unittest.mock import patch

import pytest


class TestCeleryAppConfiguration:
    """Tests for Celery application setup."""

    def test_celery_app_exists(self):
        """Test that Celery app can be imported."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app is not None

    def test_celery_app_is_celery_instance(self):
        """Test that celery_app is a Celery instance."""
        from celery import Celery

        from src.tnse.core.celery_app import celery_app

        assert isinstance(celery_app, Celery)

    def test_celery_app_name(self):
        """Test that Celery app has correct name."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.main == "tnse"

    def test_celery_broker_url_from_settings(self):
        """Test that broker URL is loaded from settings."""
        with patch.dict(
            os.environ,
            {"CELERY_BROKER_URL": "redis://test-redis:6379/1"},
        ):
            # Need to reimport to pick up new settings
            from src.tnse.core.config import get_settings

            get_settings.cache_clear()
            from src.tnse.core.celery_app import create_celery_app

            app = create_celery_app()
            assert "redis://test-redis:6379/1" in str(app.conf.broker_url)

    def test_celery_result_backend_from_settings(self):
        """Test that result backend URL is loaded from settings."""
        with patch.dict(
            os.environ,
            {"CELERY_RESULT_BACKEND": "redis://test-redis:6379/2"},
        ):
            from src.tnse.core.config import get_settings

            get_settings.cache_clear()
            from src.tnse.core.celery_app import create_celery_app

            app = create_celery_app()
            assert "redis://test-redis:6379/2" in str(app.conf.result_backend)

    def test_celery_task_discovery(self):
        """Test that Celery discovers tasks from pipeline module."""
        from src.tnse.core.celery_app import celery_app

        # Ensure task autodiscovery includes pipeline
        assert "src.tnse.pipeline" in celery_app.conf.include or any(
            "pipeline" in pkg for pkg in celery_app.conf.imports or []
        )


class TestCeleryConfiguration:
    """Tests for Celery configuration settings."""

    def test_celery_timezone_is_utc(self):
        """Test that Celery uses UTC timezone."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.timezone == "UTC"

    def test_celery_task_serializer_is_json(self):
        """Test that task serializer is JSON for safety."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"

    def test_celery_result_serializer_is_json(self):
        """Test that result serializer is JSON for safety."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.result_serializer == "json"

    def test_celery_accept_content_includes_json(self):
        """Test that Celery accepts JSON content."""
        from src.tnse.core.celery_app import celery_app

        assert "json" in celery_app.conf.accept_content

    def test_celery_task_acks_late_is_true(self):
        """Test that task acknowledgment is late for reliability."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.task_acks_late is True

    def test_celery_task_reject_on_worker_lost_is_true(self):
        """Test that tasks are requeued on worker loss."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.task_reject_on_worker_lost is True

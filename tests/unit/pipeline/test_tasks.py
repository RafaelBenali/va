"""
Tests for TNSE Content Collection Celery Tasks

Following TDD methodology: tests for the Celery tasks that orchestrate
content collection from all monitored channels.

Work Stream: WS-1.6 - Content Collection Pipeline

Requirements addressed:
- Create content collection job
- Schedule periodic runs (every 15-30 min)
- Handles failures gracefully
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCollectAllChannelsTask:
    """Tests for the collect_all_channels Celery task."""

    def test_task_is_registered(self):
        """Test that collect_all_channels task is registered."""
        from src.tnse.pipeline.tasks import collect_all_channels

        assert collect_all_channels is not None
        assert hasattr(collect_all_channels, "delay")
        assert hasattr(collect_all_channels, "apply_async")

    def test_task_has_correct_name(self):
        """Test that task has the correct registered name."""
        from src.tnse.pipeline.tasks import collect_all_channels

        assert collect_all_channels.name == "src.tnse.pipeline.tasks.collect_all_channels"

    def test_task_returns_dict(self):
        """Test that task returns a dictionary with status."""
        from src.tnse.pipeline.tasks import collect_all_channels

        result = collect_all_channels()

        assert isinstance(result, dict)
        assert "status" in result

    def test_task_returns_channel_count(self):
        """Test that task returns number of channels processed."""
        from src.tnse.pipeline.tasks import collect_all_channels

        result = collect_all_channels()

        assert "channels_processed" in result

    def test_task_returns_post_count(self):
        """Test that task returns number of posts collected."""
        from src.tnse.pipeline.tasks import collect_all_channels

        result = collect_all_channels()

        assert "posts_collected" in result


class TestCollectChannelContentTask:
    """Tests for the collect_channel_content Celery task."""

    def test_task_is_registered(self):
        """Test that collect_channel_content task is registered."""
        from src.tnse.pipeline.tasks import collect_channel_content

        assert collect_channel_content is not None
        assert hasattr(collect_channel_content, "delay")
        assert hasattr(collect_channel_content, "apply_async")

    def test_task_has_correct_name(self):
        """Test that task has the correct registered name."""
        from src.tnse.pipeline.tasks import collect_channel_content

        assert collect_channel_content.name == "src.tnse.pipeline.tasks.collect_channel_content"

    def test_task_accepts_channel_id(self):
        """Test that task accepts channel_id parameter."""
        from src.tnse.pipeline.tasks import collect_channel_content

        channel_id = str(uuid4())
        result = collect_channel_content(channel_id=channel_id)

        assert isinstance(result, dict)
        assert result["channel_id"] == channel_id

    def test_task_returns_dict(self):
        """Test that task returns a dictionary with status."""
        from src.tnse.pipeline.tasks import collect_channel_content

        result = collect_channel_content(channel_id=str(uuid4()))

        assert isinstance(result, dict)
        assert "status" in result

    def test_task_returns_post_count(self):
        """Test that task returns posts collected count."""
        from src.tnse.pipeline.tasks import collect_channel_content

        result = collect_channel_content(channel_id=str(uuid4()))

        assert "posts_collected" in result


class TestTaskRetryConfiguration:
    """Tests for task retry configuration."""

    def test_collect_all_has_max_retries(self):
        """Test that collect_all_channels has max_retries configured."""
        from src.tnse.pipeline.tasks import collect_all_channels

        assert collect_all_channels.max_retries == 3

    def test_collect_all_has_retry_delay(self):
        """Test that collect_all_channels has retry delay configured."""
        from src.tnse.pipeline.tasks import collect_all_channels

        assert collect_all_channels.default_retry_delay == 60

    def test_collect_channel_has_max_retries(self):
        """Test that collect_channel_content has max_retries configured."""
        from src.tnse.pipeline.tasks import collect_channel_content

        assert collect_channel_content.max_retries == 3

    def test_collect_channel_has_retry_delay(self):
        """Test that collect_channel_content has retry delay configured."""
        from src.tnse.pipeline.tasks import collect_channel_content

        assert collect_channel_content.default_retry_delay == 60


class TestBeatScheduleConfiguration:
    """Tests for Celery Beat periodic schedule configuration."""

    def test_beat_schedule_exists(self):
        """Test that beat_schedule is configured."""
        from src.tnse.core.celery_app import celery_app

        assert celery_app.conf.beat_schedule is not None

    def test_content_collection_scheduled(self):
        """Test that content collection task is scheduled."""
        from src.tnse.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "collect-content-every-15-minutes" in schedule

    def test_schedule_interval_is_15_minutes(self):
        """Test that schedule runs every 15 minutes."""
        from src.tnse.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        task_config = schedule["collect-content-every-15-minutes"]

        assert task_config["schedule"] == 900.0  # 15 minutes in seconds

    def test_schedule_has_expiry(self):
        """Test that scheduled task has expiry time."""
        from src.tnse.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        task_config = schedule["collect-content-every-15-minutes"]

        assert "expires" in task_config.get("options", {})

    def test_schedule_calls_correct_task(self):
        """Test that schedule calls the correct task."""
        from src.tnse.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        task_config = schedule["collect-content-every-15-minutes"]

        assert task_config["task"] == "src.tnse.pipeline.tasks.collect_all_channels"

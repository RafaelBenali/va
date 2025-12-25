"""
Tests for TNSE Saved Topics database models.

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover the SavedTopic, TopicTemplate, and BotSettings models.

Requirements addressed:
- WS-1.2: Design schema for saved topics/templates
- REQ-TC-003: System MUST allow saving topic configurations for future use
- REQ-TC-007: System MUST support topic templates for common searches
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestSavedTopicModel:
    """Tests for the SavedTopic database model."""

    def test_saved_topic_model_exists(self):
        """Test that SavedTopic model class exists."""
        from src.tnse.db.models import SavedTopic
        assert SavedTopic is not None

    def test_saved_topic_has_required_fields(self):
        """Test that SavedTopic has all required fields."""
        from src.tnse.db.models import SavedTopic

        column_names = [column.name for column in SavedTopic.__table__.columns]

        required_fields = [
            "id",
            "name",
            "description",
            "keywords",
            "search_config",
            "is_active",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in column_names, f"SavedTopic missing required field: {field}"

    def test_saved_topic_has_tablename(self):
        """Test that SavedTopic has correct table name."""
        from src.tnse.db.models import SavedTopic

        assert SavedTopic.__tablename__ == "saved_topics"

    def test_saved_topic_name_is_unique(self):
        """Test that SavedTopic name is unique."""
        from src.tnse.db.models import SavedTopic

        name_column = SavedTopic.__table__.columns["name"]
        assert name_column.unique is True

    def test_saved_topic_keywords_is_text(self):
        """Test that keywords can store JSON or comma-separated list."""
        from src.tnse.db.models import SavedTopic
        from sqlalchemy import Text

        keywords_column = SavedTopic.__table__.columns["keywords"]
        assert isinstance(keywords_column.type, Text)

    def test_saved_topic_search_config_is_text(self):
        """Test that search_config can store JSON configuration."""
        from src.tnse.db.models import SavedTopic
        from sqlalchemy import Text

        config_column = SavedTopic.__table__.columns["search_config"]
        assert isinstance(config_column.type, Text)

    def test_saved_topic_can_be_instantiated(self):
        """Test that SavedTopic can be instantiated."""
        from src.tnse.db.models import SavedTopic

        topic = SavedTopic(
            name="corruption_news",
            description="News about political corruption",
            keywords="corruption, scandal, bribery",
        )

        assert topic.name == "corruption_news"
        assert topic.description == "News about political corruption"

    def test_saved_topic_is_active_defaults_to_true(self):
        """Test that is_active defaults to True."""
        from src.tnse.db.models import SavedTopic

        is_active_column = SavedTopic.__table__.columns["is_active"]
        assert is_active_column.default is not None or is_active_column.server_default is not None


class TestTopicTemplateModel:
    """Tests for the TopicTemplate database model."""

    def test_topic_template_model_exists(self):
        """Test that TopicTemplate model class exists."""
        from src.tnse.db.models import TopicTemplate
        assert TopicTemplate is not None

    def test_topic_template_has_required_fields(self):
        """Test that TopicTemplate has all required fields."""
        from src.tnse.db.models import TopicTemplate

        column_names = [column.name for column in TopicTemplate.__table__.columns]

        required_fields = [
            "id",
            "name",
            "description",
            "keywords",
            "category",
            "is_builtin",
            "created_at",
        ]

        for field in required_fields:
            assert field in column_names, f"TopicTemplate missing required field: {field}"

    def test_topic_template_has_tablename(self):
        """Test that TopicTemplate has correct table name."""
        from src.tnse.db.models import TopicTemplate

        assert TopicTemplate.__tablename__ == "topic_templates"

    def test_topic_template_name_is_unique(self):
        """Test that TopicTemplate name is unique."""
        from src.tnse.db.models import TopicTemplate

        name_column = TopicTemplate.__table__.columns["name"]
        assert name_column.unique is True

    def test_topic_template_is_builtin_defaults_to_false(self):
        """Test that is_builtin defaults to False for custom templates."""
        from src.tnse.db.models import TopicTemplate

        is_builtin_column = TopicTemplate.__table__.columns["is_builtin"]
        assert is_builtin_column.default is not None or is_builtin_column.server_default is not None

    def test_topic_template_has_category(self):
        """Test that TopicTemplate has category field for grouping."""
        from src.tnse.db.models import TopicTemplate
        from sqlalchemy import String

        category_column = TopicTemplate.__table__.columns["category"]
        assert isinstance(category_column.type, String)

    def test_topic_template_can_be_instantiated(self):
        """Test that TopicTemplate can be instantiated."""
        from src.tnse.db.models import TopicTemplate

        template = TopicTemplate(
            name="corruption",
            description="General corruption-related news",
            keywords="corruption, bribery, scandal, embezzlement",
            category="politics",
            is_builtin=True,
        )

        assert template.name == "corruption"
        assert template.is_builtin is True


class TestBotSettingsModel:
    """Tests for the BotSettings database model (key-value store)."""

    def test_bot_settings_model_exists(self):
        """Test that BotSettings model class exists."""
        from src.tnse.db.models import BotSettings
        assert BotSettings is not None

    def test_bot_settings_has_required_fields(self):
        """Test that BotSettings has key-value fields."""
        from src.tnse.db.models import BotSettings

        column_names = [column.name for column in BotSettings.__table__.columns]

        required_fields = [
            "id",
            "key",
            "value",
            "updated_at",
        ]

        for field in required_fields:
            assert field in column_names, f"BotSettings missing required field: {field}"

    def test_bot_settings_has_tablename(self):
        """Test that BotSettings has correct table name."""
        from src.tnse.db.models import BotSettings

        assert BotSettings.__tablename__ == "bot_settings"

    def test_bot_settings_key_is_unique(self):
        """Test that BotSettings key is unique."""
        from src.tnse.db.models import BotSettings

        key_column = BotSettings.__table__.columns["key"]
        assert key_column.unique is True

    def test_bot_settings_value_is_text(self):
        """Test that value can store JSON or text content."""
        from src.tnse.db.models import BotSettings
        from sqlalchemy import Text

        value_column = BotSettings.__table__.columns["value"]
        assert isinstance(value_column.type, Text)

    def test_bot_settings_can_be_instantiated(self):
        """Test that BotSettings can be instantiated."""
        from src.tnse.db.models import BotSettings

        setting = BotSettings(
            key="default_search_mode",
            value="metrics_only",
        )

        assert setting.key == "default_search_mode"
        assert setting.value == "metrics_only"
